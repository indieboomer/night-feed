#!/usr/bin/env python3
import json
import os
import sys
from datetime import datetime
from jinja2 import Template

from llm_client import LLMClient
from trend_analyzer import analyze_steam_trends, select_deep_dive_topic


def load_signals():
    """Load collected signals from Collector service."""
    signals_path = '/data/signals.json'

    if not os.path.exists(signals_path):
        print(f"ERROR: Signals file not found: {signals_path}")
        print("Make sure Collector service ran successfully first.")
        sys.exit(1)

    try:
        with open(signals_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"ERROR: Failed to load signals: {e}")
        sys.exit(1)


def load_prompts():
    """Load system and user prompt templates."""
    system_prompt_path = '/config/prompts/system_prompt.txt'
    user_prompt_path = '/config/prompts/user_prompt.j2'

    try:
        with open(system_prompt_path, 'r', encoding='utf-8') as f:
            system_prompt = f.read()

        with open(user_prompt_path, 'r', encoding='utf-8') as f:
            user_prompt_template = Template(f.read())

        return system_prompt, user_prompt_template

    except Exception as e:
        print(f"ERROR: Failed to load prompts: {e}")
        sys.exit(1)


def main():
    """Main writer entry point."""
    print("=" * 60)
    print("NIGHT-FEED WRITER")
    print("=" * 60)

    # Load collected signals
    print("\n[1/4] Loading collected signals...")
    signals = load_signals()

    steam_top_sellers = signals['signals'].get('steam_top_sellers', [])
    steam_trending = signals['signals'].get('steam_trending', [])
    rss_items = signals['signals'].get('rss_items', [])
    rss_highlights = signals['signals'].get('rss_highlights', [])

    print(f"  ✓ Loaded {len(steam_top_sellers)} top sellers, {len(steam_trending)} trending, {len(rss_items)} RSS items")

    # Analyze trends
    print("\n[2/4] Analyzing trends...")
    trend_summary = analyze_steam_trends(steam_top_sellers, steam_trending, rss_items)
    deep_dive_topic = select_deep_dive_topic(steam_top_sellers, rss_items)

    print("  Detected trends:")
    for line in trend_summary.split('\n'):
        print(f"    {line}")

    # Load prompts
    print("\n[3/4] Preparing LLM prompts...")
    system_prompt, user_prompt_template = load_prompts()

    # Render user prompt with data
    date_str = signals['date']
    user_prompt = user_prompt_template.render(
        date=date_str,
        steam_top_sellers=steam_top_sellers,
        steam_trending=steam_trending,
        rss_highlights=rss_highlights,
        trend_summary=trend_summary,
        deep_dive_topic=deep_dive_topic
    )

    # Generate script with LLM
    print("\n[4/4] Generating podcast script...")
    llm = LLMClient()

    try:
        script, metadata = llm.generate_script(system_prompt, user_prompt)
    except Exception as e:
        print(f"\nFATAL: Script generation failed: {e}")
        sys.exit(1)

    # Validate script
    target_duration = int(os.getenv('SCRIPT_TARGET_DURATION_MINUTES', '12'))
    is_valid = llm.validate_script(script, target_duration_minutes=target_duration)

    # Save script
    output_dir = '/output/scripts'
    os.makedirs(output_dir, exist_ok=True)

    script_path = f'{output_dir}/{date_str}.txt'
    metadata_path = f'{output_dir}/{date_str}_metadata.json'

    try:
        # Save script
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script)

        # Save metadata
        metadata['date'] = date_str
        metadata['trend_summary'] = trend_summary
        metadata['is_valid'] = is_valid
        metadata['word_count'] = len(script.split())

        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        print(f"\n✓ Script saved to {script_path}")
        print(f"✓ Metadata saved to {metadata_path}")

    except Exception as e:
        print(f"\nERROR: Failed to save script: {e}")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("SCRIPT GENERATION COMPLETE")
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
