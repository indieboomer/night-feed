import sqlite3
import json
from datetime import datetime

DB_PATH = "/data/signals_history.db"


def init_db():
    """Initialize database schema for signal history tracking."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    cursor = conn.cursor()

    # Steam rankings history
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS steam_rankings (
            date TEXT NOT NULL,
            appid INTEGER NOT NULL,
            name TEXT,
            rank INTEGER,
            timestamp INTEGER,
            PRIMARY KEY (date, appid)
        )
    ''')

    # RSS items seen (for deduplication)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rss_seen (
            url TEXT PRIMARY KEY,
            title TEXT,
            source TEXT,
            first_seen INTEGER
        )
    ''')

    cursor.execute('CREATE INDEX IF NOT EXISTS idx_steam_date ON steam_rankings(date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_rss_source ON rss_seen(source)')

    conn.commit()
    conn.close()
    print("Database initialized successfully")


def store_steam_rankings(date, rankings):
    """Store today's Steam rankings for trend analysis."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    cursor = conn.cursor()
    timestamp = int(datetime.now().timestamp())

    for game in rankings:
        cursor.execute('''
            INSERT OR REPLACE INTO steam_rankings (date, appid, name, rank, timestamp)
            VALUES (?, ?, ?, ?, ?)
        ''', (date, game['appid'], game['name'], game['rank'], timestamp))

    conn.commit()
    conn.close()


def get_previous_rankings(days_back=7):
    """Get Steam rankings from previous days for trend comparison."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT DISTINCT date FROM steam_rankings
        ORDER BY date DESC
        LIMIT ?
    ''', (days_back,))

    dates = [row[0] for row in cursor.fetchall()]

    rankings_by_date = {}
    for date in dates:
        cursor.execute('''
            SELECT appid, name, rank FROM steam_rankings
            WHERE date = ?
        ''', (date,))
        rankings_by_date[date] = {
            row[0]: {'name': row[1], 'rank': row[2]}
            for row in cursor.fetchall()
        }

    conn.close()
    return rankings_by_date


def is_rss_item_new(url):
    """Check if RSS item was already seen."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    cursor = conn.cursor()

    cursor.execute('SELECT 1 FROM rss_seen WHERE url = ?', (url,))
    exists = cursor.fetchone() is not None

    conn.close()
    return not exists


def mark_rss_item_seen(url, title, source):
    """Mark RSS item as seen."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    cursor = conn.cursor()
    timestamp = int(datetime.now().timestamp())

    cursor.execute('''
        INSERT OR IGNORE INTO rss_seen (url, title, source, first_seen)
        VALUES (?, ?, ?, ?)
    ''', (url, title, source, timestamp))

    conn.commit()
    conn.close()


def cleanup_old_data(days_to_keep=30):
    """Remove data older than specified days."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    cursor = conn.cursor()

    cutoff_timestamp = int((datetime.now().timestamp()) - (days_to_keep * 86400))

    cursor.execute('DELETE FROM steam_rankings WHERE timestamp < ?', (cutoff_timestamp,))
    cursor.execute('DELETE FROM rss_seen WHERE first_seen < ?', (cutoff_timestamp,))

    conn.commit()
    conn.close()
    print(f"Cleaned up data older than {days_to_keep} days")
