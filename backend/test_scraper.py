"""
Quick test script for the sequential TikTok scraper
"""
import asyncio
from crawler import run_campaign_scraper_sync

async def test_scraper():
    """Test the scraper with a simple campaign description"""

    print("Testing parallel TikTok scraper...")
    print("="*70)

    # Test with a small number of queries and users
    profiles_count = await run_campaign_scraper_sync(
        campaign_description="ugc fitness creators",
        num_queries=100,  # 10 search queries
        users_per_search=10,  # 50 users per query
        filter_emails_only=True
        # Note: sync version always uses single MS token from .env (no fetch_unique_tokens param)
    )

    print("="*70)
    print(f"\n✅ Test completed! Found {profiles_count} profiles")

if __name__ == "__main__":
    asyncio.run(test_scraper())
