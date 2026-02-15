import feedparser
import yaml
import os
from datetime import datetime
from utils.db import is_rss_item_new, mark_rss_item_seen


def load_rss_sources():
    """Load RSS sources from config file."""
    config_path = "/config/rss_sources.yml"

    if not os.path.exists(config_path):
        print(f"WARNING: RSS config not found at {config_path}")
        return []

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            return config.get('sources', [])
    except Exception as e:
        print(f"ERROR: Failed to load RSS config: {e}")
        return []


def fetch_rss_feed(source, max_items=50, timeout=30):
    """Fetch and parse a single RSS feed."""
    name = source.get('name', 'unknown')
    url = source.get('url')
    language = source.get('language', 'unknown')
    category = source.get('category', 'general')

    if not url:
        print(f"ERROR: No URL for source {name}")
        return []

    try:
        print(f"Fetching RSS: {name} ({url})")
        feed = feedparser.parse(url)

        if feed.bozo:
            print(f"WARNING: Feed {name} has parsing errors")

        items = []
        for entry in feed.entries[:max_items]:
            # Extract data
            title = entry.get('title', 'No title')
            link = entry.get('link', '')
            published = entry.get('published', entry.get('updated', ''))

            # Try to parse published date
            published_timestamp = None
            if published:
                try:
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        published_timestamp = datetime(*entry.published_parsed[:6]).isoformat()
                    elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                        published_timestamp = datetime(*entry.updated_parsed[:6]).isoformat()
                except:
                    published_timestamp = published

            # Skip if no link
            if not link:
                continue

            # Check if new (deduplication)
            if not is_rss_item_new(link):
                continue

            items.append({
                'source': name,
                'title': title,
                'url': link,
                'published': published_timestamp,
                'language': language,
                'category': category
            })

            # Mark as seen
            mark_rss_item_seen(link, title, name)

        print(f"  → {len(items)} new items from {name}")
        return items

    except Exception as e:
        print(f"ERROR: Failed to fetch RSS {name}: {e}")
        return []


def fetch_all_rss_feeds(max_items_per_source=50):
    """Fetch all configured RSS feeds."""
    sources = load_rss_sources()

    if not sources:
        print("WARNING: No RSS sources configured")
        return []

    all_items = []

    for source in sources:
        items = fetch_rss_feed(source, max_items=max_items_per_source)
        all_items.extend(items)

    print(f"Total new RSS items collected: {len(all_items)}")
    return all_items


def prioritize_rss_items(items, max_items=20):
    """Prioritize RSS items by source priority and recency."""
    # Simple prioritization: high priority sources first, then recent items
    high_priority = [item for item in items if 'hacker_news' in item['source'] or 'eurogamer' in item['source'] or 'spiders' in item['source']]
    others = [item for item in items if item not in high_priority]

    # Combine and limit
    prioritized = high_priority[:max_items // 2] + others[:max_items // 2]

    return prioritized[:max_items]
