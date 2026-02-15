import requests
import time
from bs4 import BeautifulSoup


def fetch_top_sellers(max_items=30):
    """Fetch Steam Top Sellers from official API."""
    url = "https://store.steampowered.com/api/featuredcategories"

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()

        top_sellers = data.get('top_sellers', {}).get('items', [])

        results = []
        for idx, game in enumerate(top_sellers[:max_items], 1):
            results.append({
                'appid': game.get('id'),
                'name': game.get('name', 'Unknown'),
                'rank': idx,
                'rank_change': None  # Will be calculated later
            })

        print(f"Fetched {len(results)} top sellers from Steam")
        return results

    except requests.RequestException as e:
        print(f"ERROR: Failed to fetch Steam top sellers: {e}")
        return []
    except Exception as e:
        print(f"ERROR: Failed to parse Steam data: {e}")
        return []


def fetch_new_and_trending(max_items=20):
    """Fetch Steam New & Trending games by scraping the store page."""
    url = "https://store.steampowered.com/?tab=newreleases"

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Find new release items (simplified scraping)
        # Note: Steam's HTML structure can change; this is a basic implementation
        results = []

        # Try to find app links in new releases section
        app_links = soup.find_all('a', href=True, limit=max_items * 2)

        for link in app_links:
            href = link.get('href', '')
            if '/app/' in href and 'store.steampowered.com' in href:
                try:
                    # Extract app ID from URL like https://store.steampowered.com/app/123456/...
                    appid = href.split('/app/')[1].split('/')[0]
                    if not appid.isdigit():
                        continue

                    # Get game name from link text or title
                    name = link.get_text(strip=True) or link.get('title', f'App {appid}')

                    if name and len(name) > 3:  # Filter out noise
                        results.append({
                            'appid': int(appid),
                            'name': name
                        })

                        if len(results) >= max_items:
                            break
                except:
                    continue

        # Fallback: if scraping fails, use Steam250 API (unofficial but reliable)
        if len(results) < 5:
            print("Scraping yielded few results, trying Steam250 API...")
            results = fetch_steam250_trending(max_items)

        print(f"Fetched {len(results)} new & trending games from Steam")
        return results

    except requests.RequestException as e:
        print(f"ERROR: Failed to fetch Steam new & trending: {e}")
        return []
    except Exception as e:
        print(f"ERROR: Failed to parse Steam trending data: {e}")
        return []


def fetch_steam250_trending(max_items=20):
    """Fetch trending games from Steam250 (unofficial API)."""
    url = "https://steam250.com/trending.json"

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()

        results = []
        for game in data[:max_items]:
            results.append({
                'appid': game.get('appid'),
                'name': game.get('name', 'Unknown')
            })

        return results

    except:
        return []


def calculate_rank_changes(current_rankings, previous_rankings):
    """Calculate rank changes by comparing with previous data."""
    if not previous_rankings:
        return current_rankings

    # Get most recent previous ranking
    latest_date = sorted(previous_rankings.keys(), reverse=True)[0]
    previous = previous_rankings[latest_date]

    for game in current_rankings:
        appid = game['appid']
        current_rank = game['rank']

        if appid in previous:
            prev_rank = previous[appid]['rank']
            game['rank_change'] = prev_rank - current_rank  # Positive = moved up
        else:
            game['rank_change'] = None  # New entry

    return current_rankings
