#!/usr/bin/env python3
import json
import os
import sys
from datetime import datetime

# Add sources to path
sys.path.insert(0, '/app')

from sources.steam import (
    fetch_top_sellers,
    fetch_new_and_trending,
    calculate_rank_changes
)
from sources.rss_feeds import fetch_all_rss_feeds, prioritize_rss_items
from utils.db import (
    init_db,
    store_steam_rankings,
    get_previous_rankings,
    cleanup_old_data
)


def main():
    """Main collector entry point."""
    print("=" * 60)
    print("NIGHT-FEED COLLECTOR")
    print("=" * 60)

    # Initialize database
    init_db()

    # Cleanup old data (keep 30 days)
    cleanup_old_data(days_to_keep=30)

    # Get collection parameters from environment
    max_rss_items = int(os.getenv('COLLECTOR_MAX_ITEMS_PER_SOURCE', '50'))
    rss_timeout = int(os.getenv('RSS_FETCH_TIMEOUT', '30'))

    today = datetime.now().strftime("%Y-%m-%d")
    collection_timestamp = datetime.now().isoformat()

    # Collect Steam Top Sellers
    print("\n[1/3] Fetching Steam Top Sellers...")
    steam_top_sellers = fetch_top_sellers(max_items=30)

    # Calculate rank changes
    if steam_top_sellers:
        previous_rankings = get_previous_rankings(days_back=7)
        steam_top_sellers = calculate_rank_changes(steam_top_sellers, previous_rankings)

        # Store today's rankings
        store_steam_rankings(today, steam_top_sellers)
        print(f"  ✓ Stored {len(steam_top_sellers)} top sellers")

    # Collect Steam New & Trending
    print("\n[2/3] Fetching Steam New & Trending...")
    steam_trending = fetch_new_and_trending(max_items=20)

    # Collect RSS feeds
    print("\n[3/3] Fetching RSS feeds...")
    rss_items = fetch_all_rss_feeds(max_items_per_source=max_rss_items)

    # Prioritize RSS items for script
    rss_highlights = prioritize_rss_items(rss_items, max_items=20)

    # Build output structure
    signals = {
        'collection_timestamp': collection_timestamp,
        'date': today,
        'signals': {
            'steam_top_sellers': steam_top_sellers,
            'steam_trending': steam_trending,
            'rss_items': rss_items,
            'rss_highlights': rss_highlights
        },
        'metadata': {
            'total_signals': len(steam_top_sellers) + len(steam_trending) + len(rss_items),
            'steam_top_sellers_count': len(steam_top_sellers),
            'steam_trending_count': len(steam_trending),
            'rss_total_count': len(rss_items),
            'rss_highlights_count': len(rss_highlights)
        }
    }

    # Write to output file
    output_path = '/data/signals.json'
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(signals, f, ensure_ascii=False, indent=2)
        print(f"\n✓ Signals written to {output_path}")
        print(f"  Total signals: {signals['metadata']['total_signals']}")
    except Exception as e:
        print(f"\nERROR: Failed to write signals: {e}")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("COLLECTION COMPLETE")
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
