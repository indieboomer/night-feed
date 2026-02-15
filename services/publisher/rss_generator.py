import os
from datetime import datetime
import pytz
from feedgen.feed import FeedGenerator
from mutagen.mp3 import MP3


class RSSGenerator:
    """RSS 2.0 podcast feed generator."""

    def __init__(self):
        self.title = os.getenv('PODCAST_TITLE', 'Night-Feed: Sygnały Gaming & Tech')
        self.author = os.getenv('PODCAST_AUTHOR', 'Night-Feed Bot')
        self.description = os.getenv('PODCAST_DESCRIPTION', 'Codzienny briefing o trendach w grach i technologii')
        self.base_url = os.getenv('PODCAST_BASE_URL', 'http://localhost:8080')

    def create_feed(self):
        """Create base RSS feed structure."""
        fg = FeedGenerator()

        fg.load_extension('podcast')

        fg.title(self.title)
        fg.description(self.description)
        fg.author({'name': self.author})
        fg.language('pl')
        fg.link(href=self.base_url, rel='alternate')

        # Podcast-specific tags
        fg.podcast.itunes_author(self.author)
        fg.podcast.itunes_category('Technology')
        fg.podcast.itunes_explicit('no')
        fg.podcast.itunes_summary(self.description)

        return fg

    def add_episode(self, fg, episode_date, episode_file):
        """Add an episode to the feed."""
        # Get episode number from date (days since epoch % 10000)
        episode_num = (datetime.strptime(episode_date, "%Y-%m-%d") - datetime(2020, 1, 1)).days

        fe = fg.add_entry()
        fe.id(f"night-feed-{episode_date}")
        fe.title(f"Night-Feed #{episode_num} - {episode_date}")
        fe.description(f"Codzienny briefing o trendach w grach i technologii - {episode_date}")

        # Episode URL
        episode_url = f"{self.base_url}/episodes/{episode_date}.mp3"

        # Get file size and duration
        file_size = os.path.getsize(episode_file)

        try:
            audio = MP3(episode_file)
            duration_seconds = int(audio.info.length)
            duration_str = self.format_duration(duration_seconds)
        except:
            duration_seconds = None
            duration_str = "00:00:00"

        # Enclosure (audio file)
        fe.enclosure(episode_url, str(file_size), 'audio/mpeg')

        # Publication date (timezone-aware for proper RSS format)
        warsaw_tz = pytz.timezone('Europe/Warsaw')
        pub_date = datetime.strptime(episode_date, "%Y-%m-%d").replace(hour=21, minute=30)
        pub_date = warsaw_tz.localize(pub_date)
        fe.pubDate(pub_date)

        # iTunes-specific tags
        if duration_str:
            fe.podcast.itunes_duration(duration_str)

        print(f"  Added episode: {episode_date} ({duration_str}, {file_size / 1024 / 1024:.1f} MB)")

        return fe

    def format_duration(self, seconds):
        """Format duration as HH:MM:SS."""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def generate_feed(self, episodes_dir, output_path, max_episodes=30):
        """Generate complete RSS feed with all episodes."""
        print(f"Generating RSS feed...")

        fg = self.create_feed()

        # Find all MP3 files in episodes directory
        episode_files = []
        if os.path.exists(episodes_dir):
            for filename in os.listdir(episodes_dir):
                if filename.endswith('.mp3'):
                    # Extract date from filename (YYYY-MM-DD.mp3)
                    episode_date = filename.replace('.mp3', '')
                    episode_path = os.path.join(episodes_dir, filename)
                    episode_files.append((episode_date, episode_path))

        # Sort by date (newest first)
        episode_files.sort(reverse=True)

        # Add episodes (limit to max_episodes)
        for episode_date, episode_path in episode_files[:max_episodes]:
            try:
                self.add_episode(fg, episode_date, episode_path)
            except Exception as e:
                print(f"  WARNING: Failed to add episode {episode_date}: {e}")

        # Write RSS file
        fg.rss_file(output_path, pretty=True)

        print(f"✓ RSS feed generated: {output_path}")
        print(f"  Total episodes: {len(episode_files[:max_episodes])}")

        return True
