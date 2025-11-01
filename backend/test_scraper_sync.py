"""
Continuous TikTok scraper that builds a diverse creator index.

This script:
1. Generates random campaign descriptions targeting different demographics and niches
2. Fetches a fresh MS token for each campaign
3. Runs the scraper to find creators matching that niche
4. Loops continuously to build a comprehensive, diverse index

Press Ctrl+C to stop.
"""
import asyncio
import os
from openai import AsyncOpenAI
from crawler.tiktok_scraper import run_campaign_scraper_sync, fetch_fresh_ms_token
from dotenv import load_dotenv, find_dotenv

# Search for .env in current directory and parent directories
load_dotenv(find_dotenv())


async def generate_random_campaign() -> str:
    """
    Use OpenAI to generate a diverse, random campaign description.

    Returns:
        Campaign description string targeting a specific demographic/niche
    """
    client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))

    prompt = """Generate a unique, specific campaign description for finding TikTok creators.

Think of diverse demographics, niches, and content types. Be creative and varied.

Examples of good descriptions:
- "Vegan food bloggers who post healthy recipes for busy professionals"
- "Gen Z fashion creators focused on sustainable thrift fashion"
- "Fitness micro-influencers specializing in home workouts for new moms"
- "Pet content creators with small dogs doing funny tricks"
- "Beauty creators focusing on affordable drugstore makeup"
- "Gaming streamers who play indie horror games"
- "Travel creators exploring budget destinations in Southeast Asia"
- "DIY home improvement creators for small apartments"
- "Book reviewers focusing on fantasy and sci-fi novels"
- "Plant parent creators with indoor garden tips"
- "Dance creators teaching beginner-friendly choreography"
- "Cooking creators making quick 15-minute meals"
- "Mental health advocates sharing self-care tips"
- "Small business owners sharing entrepreneurship journeys"

Generate ONE new, creative campaign description (2-3 sentences max) that targets a specific niche. Make it different from the examples above. Focus on a clear demographic or interest group."""

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a marketing expert who specializes in identifying diverse creator niches and demographics."},
                {"role": "user", "content": prompt}
            ],
            temperature=1.0,  # High temperature for maximum diversity
            max_tokens=150
        )

        campaign = response.choices[0].message.content.strip()
        return campaign

    except Exception as e:
        print(f"⚠️  Error generating campaign: {e}")
        # Fallback to a default
        return "UGC creators and content creators who work with brands"


async def continuous_scraper():
    """Main loop that continuously scrapes diverse creator niches"""

    print("="*70)
    print("🚀 CONTINUOUS DIVERSE CREATOR INDEX BUILDER")
    print("="*70)
    print("This script will continuously:")
    print("  1. Fetch FRESH MS token every 3 campaigns")
    print("  2. Rotate proxy randomly for EACH campaign")
    print("  3. Generate random campaign targeting a specific niche")
    print("  4. Scrape TikTok creators matching that niche")
    print("  5. Save to Supabase and repeat")
    print("\n⚠️  Press Ctrl+C to stop\n")
    print("="*70)

    campaign_count = 0
    total_profiles = 0
    ms_token = None
    TOKEN_REFRESH_INTERVAL = 3  # Fetch new token every N campaigns

    # Note: Proxies are rotated automatically by run_campaign_scraper_sync()
    # It picks a random proxy from the pool for each campaign

    try:
        while True:
            campaign_count += 1

            print(f"\n\n{'='*70}")
            print(f"📊 CAMPAIGN #{campaign_count}")
            print(f"{'='*70}")

            # Refresh MS token every N campaigns to avoid detection
            if campaign_count == 1 or (campaign_count - 1) % TOKEN_REFRESH_INTERVAL == 0:
                print(f"\n🎫 Fetching fresh MS token (campaign #{campaign_count})...")
                try:
                    ms_token = await fetch_fresh_ms_token()
                    if ms_token:
                        print(f"✓ Fresh MS token: {ms_token[:20]}...{ms_token[-10:]}")
                    else:
                        print("⚠️  Failed to fetch MS token, falling back to environment variable")
                        ms_token = os.getenv('TIKTOK_MS_TOKEN')
                except Exception as e:
                    print(f"⚠️  Error fetching token: {e}")
                    ms_token = os.getenv('TIKTOK_MS_TOKEN')

                if not ms_token:
                    print("❌ No MS token available. Skipping this campaign.")
                    await asyncio.sleep(30)
                    continue
            else:
                print(f"♻️  Reusing MS token from campaign #{((campaign_count - 1) // TOKEN_REFRESH_INTERVAL) * TOKEN_REFRESH_INTERVAL + 1}")

            # Step 1: Generate random campaign description
            print("\n🎯 Generating random campaign targeting a specific niche...")
            campaign_description = await generate_random_campaign()
            print(f"\n✓ Campaign: {campaign_description}")

            # Step 2: Run scraper for this campaign
            print(f"\n🔍 Starting scraper for campaign #{campaign_count}...")
            try:
                profiles_count = await run_campaign_scraper_sync(
                    campaign_description=campaign_description,
                    num_queries=10,  # 10 search queries per campaign
                    users_per_search=20,  # 20 users per query
                    filter_emails_only=True,
                    ms_token=ms_token
                )

                total_profiles += profiles_count

                print(f"\n{'='*70}")
                print(f"✅ CAMPAIGN #{campaign_count} COMPLETE")
                print(f"{'='*70}")
                print(f"Campaign: {campaign_description[:60]}...")
                print(f"Profiles found: {profiles_count}")
                print(f"Total profiles across all campaigns: {total_profiles}")
                print(f"{'='*70}")

            except Exception as e:
                print(f"\n❌ Error running campaign #{campaign_count}: {e}")
                import traceback
                traceback.print_exc()

            # Wait before next campaign to avoid rate limiting
            wait_time = 30
            print(f"\n⏳ Waiting {wait_time} seconds before next campaign...")
            await asyncio.sleep(wait_time)

    except KeyboardInterrupt:
        print(f"\n\n{'='*70}")
        print("⛔ STOPPING - User pressed Ctrl+C")
        print(f"{'='*70}")
        print(f"📊 Final Statistics:")
        print(f"   Total campaigns run: {campaign_count}")
        print(f"   Total profiles scraped: {total_profiles}")
        print(f"   Average per campaign: {total_profiles / campaign_count if campaign_count > 0 else 0:.1f}")
        print(f"{'='*70}")


if __name__ == "__main__":
    asyncio.run(continuous_scraper())
