"""
Test script for the sequential (sync) TikTok scraper
Fetches a fresh MS token using Playwright (no proxy), then runs the scraper
"""
import asyncio
from crawler.tiktok_scraper import run_campaign_scraper_sync, fetch_fresh_ms_token
import os

async def test_scraper_sync():
    """Test the sequential scraper with a fresh MS token"""

    print("Testing SEQUENTIAL TikTok scraper with FRESH MS TOKEN (NO PROXY)...")
    print("="*70)
    print("This version:")
    print("  - Fetches a FRESH MS token using Playwright (NO PROXY)")
    print("  - Uses 1 browser session")
    print("  - Uses 1 randomly selected proxy for scraping")
    print("  - Searches sequentially (not parallel)")
    print("  - Tests if token + proxy combo works")
    print("="*70)

    # Step 1: Fetch a fresh MS token using Playwright (no proxy)
    print("\n🎫 Fetching fresh MS token locally (no proxy)...")
    ms_token = await fetch_fresh_ms_token()

    if not ms_token:
        print("❌ Failed to fetch MS token, falling back to environment variable")
        ms_token = os.getenv('TIKTOK_MS_TOKEN')
        if not ms_token:
            print("❌ No MS token available. Exiting.")
            return
    else:
        print(f"✓ Successfully fetched fresh MS token: {ms_token[:20]}...{ms_token[-10:]}")

    # Step 2: Run the scraper with the fresh token
    profiles_count = await run_campaign_scraper_sync(
        campaign_description="ugc fashion creators",
        num_queries=100,  # 5 search queries
        users_per_search=10,  # 20 users per query
        filter_emails_only=True,
        ms_token=ms_token  # Pass the fresh MS token!
    )

    print("="*70)
    print(f"\n✅ Test completed! Found {profiles_count} profiles")

if __name__ == "__main__":
    asyncio.run(test_scraper_sync())
