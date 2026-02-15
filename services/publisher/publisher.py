#!/usr/bin/env python3
import os
import sys
import json
from datetime import datetime, timedelta

from tts_client import TTSClient
from rss_generator import RSSGenerator


def load_script(date_str):
    """Load generated script from Writer service."""
    script_path = f'/output/scripts/{date_str}.txt'

    if not os.path.exists(script_path):
        print(f"ERROR: Script file not found: {script_path}")
        print("Make sure Writer service ran successfully first.")
        sys.exit(1)

    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"ERROR: Failed to load script: {e}")
        sys.exit(1)


def cleanup_old_episodes(episodes_dir, days_to_keep=30):
    """Remove episodes older than specified days."""
    if not os.path.exists(episodes_dir):
        return

    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    removed_count = 0

    for filename in os.listdir(episodes_dir):
        if not filename.endswith('.mp3'):
            continue

        try:
            # Extract date from filename
            episode_date_str = filename.replace('.mp3', '')
            episode_date = datetime.strptime(episode_date_str, "%Y-%m-%d")

            if episode_date < cutoff_date:
                episode_path = os.path.join(episodes_dir, filename)
                os.remove(episode_path)
                removed_count += 1
                print(f"  Removed old episode: {filename}")

        except:
            continue

    if removed_count > 0:
        print(f"✓ Cleaned up {removed_count} old episodes")


def main():
    """Main publisher entry point."""
    print("=" * 60)
    print("NIGHT-FEED PUBLISHER")
    print("=" * 60)

    date_str = datetime.now().strftime("%Y-%m-%d")

    # Create output directories
    episodes_dir = '/output/episodes'
    os.makedirs(episodes_dir, exist_ok=True)

    # Load script
    print("\n[1/4] Loading generated script...")
    script = load_script(date_str)
    print(f"  ✓ Loaded script ({len(script)} characters)")

    # Generate audio with TTS
    print("\n[2/4] Generating audio with ElevenLabs...")
    tts = TTSClient()

    audio_path = os.path.join(episodes_dir, f'{date_str}.mp3')

    try:
        tts_metadata = tts.generate_audio(script, audio_path)

        # Get audio duration
        duration_seconds = tts.get_audio_duration(audio_path)
        if duration_seconds:
            tts_metadata['duration_seconds'] = duration_seconds

    except Exception as e:
        print(f"\nFATAL: Audio generation failed: {e}")
        sys.exit(1)

    # Update RSS feed
    print("\n[3/4] Updating RSS podcast feed...")
    rss_gen = RSSGenerator()

    feed_path = '/output/feed.xml'

    try:
        rss_gen.generate_feed(episodes_dir, feed_path, max_episodes=30)
    except Exception as e:
        print(f"\nERROR: RSS feed generation failed: {e}")
        sys.exit(1)

    # Cleanup old episodes
    print("\n[4/4] Cleaning up old episodes...")
    cleanup_old_episodes(episodes_dir, days_to_keep=30)

    # Save publisher metadata
    metadata_path = f'/output/scripts/{date_str}_publisher_metadata.json'
    try:
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(tts_metadata, f, indent=2)
        print(f"✓ Metadata saved to {metadata_path}")
    except Exception as e:
        print(f"WARNING: Failed to save metadata: {e}")

    print("\n" + "=" * 60)
    print("PUBLISHING COMPLETE")
    print(f"Episode available at: {os.getenv('PODCAST_BASE_URL', 'http://localhost:8080')}/episodes/{date_str}.mp3")
    print(f"RSS feed: {os.getenv('PODCAST_BASE_URL', 'http://localhost:8080')}/feed.xml")
    print("=" * 60)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
