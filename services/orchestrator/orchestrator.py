#!/usr/bin/env python3
import os
import sys
import subprocess
import time
import sqlite3
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz


DB_PATH = "/data/execution_log.db"


def init_db():
    """Initialize execution log database."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS executions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            stage TEXT NOT NULL,
            status TEXT NOT NULL,
            duration_seconds INTEGER,
            error_message TEXT,
            created_at INTEGER NOT NULL
        )
    ''')

    cursor.execute('CREATE INDEX IF NOT EXISTS idx_date ON executions(date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_status ON executions(status)')

    conn.commit()
    conn.close()
    print("Execution log database initialized")


def log_execution(date, stage, status, duration=None, error=None):
    """Log pipeline execution to database."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    cursor = conn.cursor()

    timestamp = int(time.time())

    cursor.execute('''
        INSERT INTO executions (date, stage, status, duration_seconds, error_message, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (date, stage, status, duration, error, timestamp))

    conn.commit()
    conn.close()


def run_service(service_name, max_retries=3):
    """Execute a service via docker exec with retry logic."""
    print(f"\n{'=' * 60}")
    print(f"Running {service_name.upper()} service...")
    print('=' * 60)

    container_name = f"night-feed-{service_name}"
    command = ["docker", "exec", container_name, "python", "/app/" + service_name + ".py"]

    for attempt in range(1, max_retries + 1):
        try:
            start_time = time.time()

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=600  # 10 minutes max per service
            )

            duration = int(time.time() - start_time)

            # Print output
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(result.stderr, file=sys.stderr)

            if result.returncode == 0:
                print(f"✓ {service_name} completed successfully in {duration}s")
                return True, duration, None
            else:
                error_msg = f"{service_name} failed with exit code {result.returncode}"
                print(f"✗ {error_msg}")

                if attempt < max_retries:
                    wait_time = 2 ** attempt  # Exponential backoff
                    print(f"  Retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                else:
                    return False, duration, error_msg

        except subprocess.TimeoutExpired:
            error_msg = f"{service_name} timed out after 10 minutes"
            print(f"✗ {error_msg}")

            if attempt < max_retries:
                print(f"  Retrying... (attempt {attempt + 1}/{max_retries})")
            else:
                return False, 600, error_msg

        except Exception as e:
            error_msg = f"{service_name} failed: {str(e)}"
            print(f"✗ {error_msg}")

            if attempt < max_retries:
                print(f"  Retrying... (attempt {attempt + 1}/{max_retries})")
            else:
                return False, 0, error_msg

    return False, 0, "Max retries exceeded"


def validate_file_exists(filepath):
    """Check if a file exists and is non-empty."""
    if not os.path.exists(filepath):
        print(f"✗ File not found: {filepath}")
        return False

    file_size = os.path.getsize(filepath)
    if file_size == 0:
        print(f"✗ File is empty: {filepath}")
        return False

    print(f"✓ File validated: {filepath} ({file_size / 1024:.1f} KB)")
    return True


def run_pipeline():
    """Execute the complete Night-Feed pipeline."""
    date = datetime.now().strftime("%Y-%m-%d")

    print("\n" + "=" * 60)
    print(f"NIGHT-FEED PIPELINE - {date}")
    print("=" * 60)

    # Check if episode already exists
    episode_path = f"/output/episodes/{date}.mp3"
    if os.path.exists(episode_path):
        print(f"✓ Episode already exists for {date}, skipping pipeline")
        return

    pipeline_start = time.time()

    # Stage 1: Collector
    print("\n[STAGE 1/3] COLLECTOR")
    success, duration, error = run_service("collector")
    log_execution(date, "collector", "success" if success else "failure", duration, error)

    if not success:
        print("\n✗ PIPELINE FAILED at Collector stage")
        notify_failure(date, "collector", error)
        return

    # Validate collector output
    if not validate_file_exists("/data/signals.json"):
        error = "Collector did not produce valid signals.json"
        log_execution(date, "collector", "failure", duration, error)
        notify_failure(date, "collector", error)
        return

    # Stage 2: Writer
    print("\n[STAGE 2/3] WRITER")
    success, duration, error = run_service("writer")
    log_execution(date, "writer", "success" if success else "failure", duration, error)

    if not success:
        print("\n✗ PIPELINE FAILED at Writer stage")
        notify_failure(date, "writer", error)
        return

    # Validate writer output
    script_path = f"/output/scripts/{date}.txt"
    if not validate_file_exists(script_path):
        error = "Writer did not produce valid script"
        log_execution(date, "writer", "failure", duration, error)
        notify_failure(date, "writer", error)
        return

    # Stage 3: Publisher
    print("\n[STAGE 3/3] PUBLISHER")
    success, duration, error = run_service("publisher")
    log_execution(date, "publisher", "success" if success else "failure", duration, error)

    if not success:
        print("\n✗ PIPELINE FAILED at Publisher stage")
        notify_failure(date, "publisher", error)
        return

    # Validate publisher outputs
    if not validate_file_exists(episode_path):
        error = "Publisher did not produce episode MP3"
        log_execution(date, "publisher", "failure", duration, error)
        notify_failure(date, "publisher", error)
        return

    if not validate_file_exists("/output/feed.xml"):
        error = "Publisher did not update RSS feed"
        log_execution(date, "publisher", "failure", duration, error)
        notify_failure(date, "publisher", error)
        return

    # Pipeline complete
    total_duration = int(time.time() - pipeline_start)

    print("\n" + "=" * 60)
    print("✓ PIPELINE COMPLETED SUCCESSFULLY")
    print(f"  Total time: {total_duration}s ({total_duration // 60}m {total_duration % 60}s)")
    print("=" * 60)

    log_execution(date, "pipeline", "success", total_duration, None)
    notify_success(date, total_duration)


def notify_success(date, duration):
    """Send success notification (optional Discord webhook)."""
    webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
    enable_notifications = os.getenv('ENABLE_NOTIFICATIONS', 'false').lower() == 'true'

    if not webhook_url or not enable_notifications:
        return

    try:
        import requests
        message = {
            'content': f"✅ Night-Feed episode generated for {date}\n⏱️ Duration: {duration // 60}m {duration % 60}s"
        }
        requests.post(webhook_url, json=message, timeout=10)
        print("✓ Success notification sent")
    except:
        pass


def notify_failure(date, stage, error):
    """Send failure notification (optional Discord webhook)."""
    webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
    enable_notifications = os.getenv('ENABLE_NOTIFICATIONS', 'false').lower() == 'true'

    if not webhook_url or not enable_notifications:
        return

    try:
        import requests
        message = {
            'content': f"❌ Night-Feed pipeline failed for {date}\n🔴 Stage: {stage}\n💬 Error: {error}"
        }
        requests.post(webhook_url, json=message, timeout=10)
        print("✓ Failure notification sent")
    except:
        pass


def main():
    """Main orchestrator entry point with scheduler."""
    print("=" * 60)
    print("NIGHT-FEED ORCHESTRATOR")
    print("=" * 60)

    # Initialize database
    init_db()

    # Get schedule from environment
    daily_run_time = os.getenv('DAILY_RUN_TIME', '21:30')
    hour, minute = daily_run_time.split(':')

    timezone = pytz.timezone(os.getenv('TZ', 'Europe/Warsaw'))

    print(f"\nSchedule: Daily at {daily_run_time} ({os.getenv('TZ', 'Europe/Warsaw')})")
    print("Press Ctrl+C to stop")
    print("=" * 60)

    # Create scheduler
    scheduler = BlockingScheduler(timezone=timezone)

    # Add daily job
    scheduler.add_job(
        run_pipeline,
        CronTrigger(hour=int(hour), minute=int(minute)),
        id='daily_briefing',
        name='Night-Feed Daily Briefing',
        replace_existing=True
    )

    # Start scheduler
    try:
        print("\n✓ Orchestrator started, waiting for scheduled time...")
        print(f"  Next run: {scheduler.get_jobs()[0].next_run_time}")

        scheduler.start()

    except (KeyboardInterrupt, SystemExit):
        print("\n\nOrchestrator stopped by user")
        scheduler.shutdown()


if __name__ == '__main__':
    main()
