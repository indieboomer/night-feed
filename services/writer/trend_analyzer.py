def analyze_steam_trends(steam_top_sellers, steam_trending, rss_items):
    """Analyze signals and generate trend summary."""
    trends = []

    # Analyze Steam rank changes
    big_movers = [
        game for game in steam_top_sellers
        if game.get('rank_change') and abs(game['rank_change']) >= 5
    ]

    if big_movers:
        movers_up = [g for g in big_movers if g['rank_change'] > 0]
        movers_down = [g for g in big_movers if g['rank_change'] < 0]

        if movers_up:
            top_mover = max(movers_up, key=lambda x: x['rank_change'])
            trends.append(
                f"Największy wzrost: {top_mover['name']} (+{top_mover['rank_change']} pozycji, teraz #{top_mover['rank']})"
            )

        if movers_down:
            top_faller = min(movers_down, key=lambda x: x['rank_change'])
            trends.append(
                f"Największy spadek: {top_faller['name']} ({top_faller['rank_change']} pozycji, teraz #{top_faller['rank']})"
            )

    # Analyze new entries in top sellers (no previous rank)
    new_entries = [
        game for game in steam_top_sellers[:10]
        if game.get('rank_change') is None
    ]

    if new_entries:
        trends.append(
            f"Nowe gry w top 10: {', '.join([g['name'] for g in new_entries[:3]])}"
        )

    # Analyze RSS topics (simple keyword clustering)
    ai_keywords = ['ai', 'artificial intelligence', 'machine learning', 'gpt', 'llm', 'neural']
    gaming_keywords = ['game', 'steam', 'playstation', 'xbox', 'nintendo', 'indie']
    tech_keywords = ['microsoft', 'google', 'apple', 'tech', 'startup']

    ai_count = sum(1 for item in rss_items if any(kw in item['title'].lower() for kw in ai_keywords))
    gaming_count = sum(1 for item in rss_items if any(kw in item['title'].lower() for kw in gaming_keywords))
    tech_count = sum(1 for item in rss_items if any(kw in item['title'].lower() for kw in tech_keywords))

    if ai_count >= 3:
        trends.append(f"Wzmożona aktywność wokół AI ({ai_count} wiadomości)")
    if gaming_count >= 5:
        trends.append(f"Wiele newsów z branży gier ({gaming_count} wiadomości)")

    # Fallback if no trends detected
    if not trends:
        trends.append("Stabilny dzień bez znaczących zmian w rankingach")

    return "\n".join(f"- {trend}" for trend in trends)


def select_deep_dive_topic(steam_top_sellers, rss_items):
    """Select the most interesting topic for deep dive section."""
    # Priority 1: Big rank changes
    big_movers = [
        game for game in steam_top_sellers[:15]
        if game.get('rank_change') and abs(game['rank_change']) >= 8
    ]

    if big_movers:
        top_mover = max(big_movers, key=lambda x: abs(x['rank_change']))
        return {
            'type': 'steam_mover',
            'game': top_mover['name'],
            'rank': top_mover['rank'],
            'change': top_mover['rank_change']
        }

    # Priority 2: Interesting RSS topic
    high_priority_items = [
        item for item in rss_items
        if item.get('source') in ['hacker_news', 'eurogamer_pl', 'spiders_web']
    ]

    if high_priority_items:
        return {
            'type': 'rss_topic',
            'title': high_priority_items[0]['title'],
            'source': high_priority_items[0]['source'],
            'url': high_priority_items[0]['url']
        }

    # Fallback: first item from top sellers
    if steam_top_sellers:
        return {
            'type': 'steam_leader',
            'game': steam_top_sellers[0]['name'],
            'rank': steam_top_sellers[0]['rank']
        }

    return None
