"""
TikTok User Scraper using TikTok-Api
Uses the unofficial TikTok API to search for users and extract profile data

Features:
- Search for users by keywords
- AI-generated search queries using OpenAI (optional)
- Extract comprehensive profile information including engagement metrics
- Find emails in user bios
- Calculate avg_likes_per_video and engagement ratios from profile stats
- Save results to JSON incrementally
- Save to Supabase database (optional)
- Much faster than browser automation

Note: Individual video fetching doesn't work due to TikTok's bot detection.
      However, profile stats (heart_count, video_count) let us calculate useful engagement metrics!

Setup:
    pip install TikTokApi openai python-dotenv supabase playwright
    python -m playwright install chromium

IMPORTANT: MS Token Required!
    TikTok has aggressive bot detection. You MUST use an ms_token for this to work.

    How to get your ms_token:
    1. Go to tiktok.com in your browser (logged in or not)
    2. Do a search for any keyword (this activates the token)
    3. Open DevTools (F12) -> Application -> Cookies -> tiktok.com
    4. Find the 'msToken' cookie and copy its value
    5. Add to .env file: TIKTOK_MS_TOKEN=your_token_here

    Without a valid ms_token, TikTok will block all requests!

Environment Variables:
    TIKTOK_MS_TOKEN - Your TikTok ms_token (required)
    OPENAI_API_KEY - OpenAI API key for generating search queries (optional, falls back to defaults)
    USE_AI_QUERIES - Set to 'true' to use AI-generated queries (default: 'true')
    NUM_SEARCH_QUERIES - Number of queries to generate (default: 15)
    SEARCH_FOCUS_AREA - Description of what type of creators to search for
    USERS_PER_SEARCH - Number of users to fetch per search term (default: 20)
    FILTER_EMAILS_ONLY - Only save users with emails in bio (default: 'true')
    SUPABASE_URL - Supabase project URL (optional)
    SUPABASE_KEY - Supabase anon key (optional)
    POST_TO_SUPABASE - Set to 'true' to insert profiles to Supabase (default: 'false')

Usage:
    python tiktok_api_scraper.py
"""

import asyncio
import json
import re
import random
from datetime import datetime
from typing import List, Dict, Optional
from TikTokApi import TikTokApi
from dotenv import load_dotenv
import os
from supabase import create_client, Client
from playwright.async_api import async_playwright
from openai import AsyncOpenAI
from browser_use import Agent, ChatOpenAI as BrowserUseChatOpenAI

load_dotenv()

async def generate_search_queries(
    num_queries: int = 50,
    focus_area: str = "UGC creators and content creators who work with brands"
) -> List[str]:
    """
    Generate diverse TikTok search queries using OpenAI.
    
    Args:
        num_queries: Number of search queries to generate
        focus_area: Description of what type of creators to search for
    
    Returns:
        List of search query strings optimized for TikTok search
    """
    api_key = os.getenv('OPENAI_API_KEY')
    
    if not api_key:
        print("⚠️  OPENAI_API_KEY not found in environment variables")
        print("   Falling back to default search terms...")
        return [
            "ugc creator",
            "fitness"
            "dance"
            "music"
            "art"
            "fashion"
            "beauty"
            "vlogger"
            "food"
            "travel"
            "technology"
            "gaming"
            "sports"
            "hobbies"
            "interests"
            "lifestyle"
            "pets"
            "animals"
            "nature"
        ]
    
    try:
        client = AsyncOpenAI(api_key=api_key)
        
        prompt = f"""Generate {num_queries} diverse TikTok search queries to find {focus_area}.

Requirements:
- Each query should be 1-5 words, optimized for TikTok search
- Make them varied, creative, and use different angles/terminology
- Include hashtag-style terms, professional terms, and casual terms
- Focus on terms that creators might use in their bios or content
- Return a JSON object with a "queries" key containing an array of strings

Example JSON format:
{{
  "queries": ["ugc creator", "brand collaboration", "content creator for hire", "sponsored content creator"]
}}

Generate {num_queries} unique search queries:"""

        response = await client.chat.completions.create(
            model="gpt-4o-mini",  # Using gpt-4o-mini for cost efficiency
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that generates TikTok search queries. Always return valid JSON with a 'queries' key containing an array of search query strings."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.95,  # Higher temperature for more creative/diverse queries
            response_format={"type": "json_object"}
        )
        
        # Parse the response
        content = response.choices[0].message.content
        result = json.loads(content)
        
        # Extract queries from the JSON object
        queries = result.get('queries', [])
        
        if not queries or not isinstance(queries, list):
            raise ValueError(f"No queries found in response. Got: {result}")
        
        print(f"✓ Generated {len(queries)} search queries using OpenAI")
        return queries[:num_queries]  # Ensure we don't exceed requested amount
        
    except Exception as e:
        print(f"⚠️  Error generating queries with OpenAI: {e}")
        print("   Falling back to default search terms...")
        return [
            "ugc creator",
            "user generated content",
            "brand deals",
            "content creator for hire",
            "collab with brands",
            "gifted pr",
            "micro influencer",
            "nano influencer"
        ]


async def fetch_fresh_ms_token() -> Optional[str]:
    """
    Fetch a fresh MS_TOKEN from TikTok's search page using Playwright.

    This opens a real browser, navigates to TikTok's search page, performs a search
    to trigger token generation, and extracts the ms_token cookie.

    Returns:
        The ms_token string, or None if extraction fails
    """
    print("\n" + "="*70)
    print("FETCHING FRESH MS_TOKEN FROM TIKTOK...")
    print("="*70)

    try:
        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context()
            page = await context.new_page()

            print("🌐 Opening TikTok search page...")
            await page.goto("https://www.tiktok.com/search", wait_until="networkidle", timeout=30000)

            # Try to perform a search to trigger ms_token generation
            print("🔍 Performing a search to trigger token generation...")
            await page.goto("https://www.tiktok.com/search?q=test", wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(3000)

            # Wait for cookies to be set after interaction
            await page.wait_for_timeout(2000)

            print("🔍 Extracting ms_token from cookies...")

            # Get all cookies multiple times (cookies might be set asynchronously)
            ms_token = None
            
            for attempt in range(3):
                cookies = await context.cookies()
                
                # Debug: print all cookie names (first attempt only)
                if attempt == 0:
                    cookie_names = [c.get('name') for c in cookies]
                    print(f"   Found cookies: {', '.join(cookie_names[:10])}{'...' if len(cookie_names) > 10 else ''}")
                
                # Check for ms_token in various formats
                for cookie in cookies:
                    cookie_name = cookie.get('name', '').lower()
                    
                    # Check multiple variations: msToken, ms_token, etc.
                    if 'mstoken' in cookie_name or cookie_name == 'ms_token':
                        ms_token = cookie.get('value')
                        print(f"✓ Found token cookie: {cookie.get('name')}")
                        break

                print(f"ms_token: {ms_token}")
                if ms_token:
                    break
                    
                # Wait a bit before next attempt
                if attempt < 2:
                    await page.wait_for_timeout(1000)

            await browser.close()

            if ms_token:
                print(f"✓ Fresh MS_TOKEN extracted successfully!")
                print(f"  Token: {ms_token[:20]}...{ms_token[-20:]}")
                print("="*70 + "\n")
                return ms_token
            else:
                print("✗ Could not find ms_token in cookies")
                print("  Make sure you're not blocked by TikTok's bot detection")
                print("="*70 + "\n")
                return None

    except Exception as e:
        print(f"✗ Error fetching ms_token: {e}")
        print("  Falling back to environment variable...")
        print("="*70 + "\n")
        return None


async def fetch_multiple_ms_tokens(num_tokens: int, use_proxies: bool = False, proxies_list: Optional[List[Dict]] = None) -> List[Optional[str]]:
    """
    Fetch multiple unique MS tokens by opening separate browser instances.

    Args:
        num_tokens: Number of tokens to fetch
        use_proxies: Whether to use proxies for token fetching
        proxies_list: List of proxy configurations (Playwright format)

    Returns:
        List of MS tokens (some may be None if fetching failed)
    """
    print("\n" + "="*70)
    print(f"FETCHING {num_tokens} UNIQUE MS_TOKENS FROM TIKTOK...")
    print("="*70)
    print("⚠️  This will open multiple browsers and may take 1-2 minutes")
    print("="*70 + "\n")

    tokens = []

    for i in range(num_tokens):
        print(f"\n🔄 Fetching token {i+1}/{num_tokens}...")

        try:
            async with async_playwright() as p:
                # Select proxy for this token fetch (if using proxies)
                proxy = None
                if use_proxies and proxies_list and len(proxies_list) > 0:
                    proxy = proxies_list[i % len(proxies_list)]
                    print(f"   Using proxy: {proxy['server']}")

                # Launch browser with or without proxy
                browser = await p.chromium.launch(headless=False)
                context = await browser.new_context(proxy=proxy if proxy else None)
                page = await context.new_page()

                print("   🌐 Opening TikTok search page...")
                await page.goto("https://www.tiktok.com/search", wait_until="networkidle", timeout=30000)

                # Perform a search to trigger ms_token generation
                print("   🔍 Triggering token generation...")
                await page.goto("https://www.tiktok.com/search?q=test", wait_until="networkidle", timeout=30000)
                await page.wait_for_timeout(3000)

                # Extract ms_token from cookies
                ms_token = None
                for attempt in range(3):
                    cookies = await context.cookies()

                    for cookie in cookies:
                        cookie_name = cookie.get('name', '').lower()
                        if 'mstoken' in cookie_name or cookie_name == 'ms_token':
                            ms_token = cookie.get('value')
                            break

                    if ms_token:
                        break

                    if attempt < 2:
                        await page.wait_for_timeout(1000)

                await browser.close()

                if ms_token:
                    print(f"   ✓ Token {i+1} extracted: {ms_token[:15]}...{ms_token[-10:]}")
                    tokens.append(ms_token)
                else:
                    print(f"   ✗ Token {i+1} extraction failed")
                    tokens.append(None)

                # Small delay between token fetches to avoid rate limiting
                if i < num_tokens - 1:
                    print("   ⏳ Waiting 3 seconds before next fetch...")
                    await asyncio.sleep(3)

        except Exception as e:
            print(f"   ✗ Error fetching token {i+1}: {e}")
            tokens.append(None)

    successful_tokens = len([t for t in tokens if t])
    print("\n" + "="*70)
    print(f"TOKEN FETCHING COMPLETE: {successful_tokens}/{num_tokens} successful")
    print("="*70 + "\n")

    return tokens


async def fetch_ms_token_with_browser_use() -> Optional[str]:
    """
    Fetch MS token from TikTok using browser-use LOCAL AI agent.

    This uses browser-use library to control a LOCAL browser and autonomously
    navigate to TikTok and extract the msToken cookie. The browser runs locally,
    so the token will be valid for this same environment.

    Requires: OPENAI_API_KEY environment variable

    Returns:
        The ms_token string, or None if extraction fails
    """
    print("\n" + "="*70)
    print("FETCHING MS_TOKEN USING BROWSER-USE LOCAL (AI Agent)...")
    print("="*70)

    try:
        # Check for OpenAI API key
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("✗ OPENAI_API_KEY not found in environment variables")
            print("  Browser-use requires an LLM API key to function")
            print("="*70 + "\n")
            return None

        # Create LLM for browser-use
        llm = BrowserUseChatOpenAI(model='gpt-4o-mini')

        # Define the task for the AI agent
        task = """
1. Navigate to https://www.tiktok.com/ and wait for the homepage to fully load
2. Perform a search for 'test' using the search functionality on the page
3. Wait for the search results page to fully load
4. Extract the value of the 'msToken' cookie from the browser (check cookies named 'msToken', 'ms_token', or containing 'mstoken')
5. Return ONLY the cookie value as a plain string with no additional text
"""

        print("🤖 Launching LOCAL browser with AI agent...")
        print("   Task: Navigate to TikTok and extract msToken cookie")

        # Create and run the browser-use agent with local browser
        agent = Agent(
            task=task,
            llm=llm,
        )

        # Run the agent (this will open a local browser window)
        result = await agent.run(max_steps=15)

        # Extract the token from the result
        ms_token = None
        if result:
            # Get the final result from AgentHistoryList
            try:
                final_output = result.final_result()
                if final_output:
                    # Clean up the token - remove quotes, whitespace, markdown
                    token_text = str(final_output).strip()
                    ms_token = token_text.strip('"\'').strip('`').strip()

                    # Validate token format (should be a long alphanumeric string)
                    if ms_token and len(ms_token) > 20:
                        print(f"✓ MS_TOKEN extracted successfully!")
                        print(f"  Token: {ms_token[:20]}...{ms_token[-20:]}")
                        print("="*70 + "\n")
                        return ms_token
            except Exception as e:
                print(f"✗ Error extracting final_result: {e}")

        print("✗ Could not extract valid ms_token from agent result")
        print(f"  Result type: {type(result)}")
        print("="*70 + "\n")
        return None

    except Exception as e:
        print(f"✗ Error using browser-use: {e}")
        print("  You can try using fetch_fresh_ms_token() as fallback")
        print("="*70 + "\n")
        return None


class TikTokUserScraper:
    """Scraper for TikTok users using the unofficial API"""

    def __init__(self, ms_token: Optional[str] = None, output_file: str = "tiktok_api_profiles.json",
                 supabase_url: Optional[str] = None, supabase_key: Optional[str] = None):
        self.ms_token = ms_token or os.getenv('TIKTOK_MS_TOKEN')
        self.output_file = output_file
        self.profiles_data: List[Dict] = []
        self.visited_usernames: set = set()

        # Thread-safe locks for concurrent access
        self.data_lock = asyncio.Lock()
        self.visited_lock = asyncio.Lock()

        # Initialize Supabase client if credentials provided
        self.supabase: Optional[Client] = None
        self.supabase_url = supabase_url
        self.supabase_key = supabase_key
        if supabase_url and supabase_key:
            self.supabase = create_client(supabase_url, supabase_key)
            print("✓ Supabase client initialized")

    def extract_email_from_bio(self, bio: str) -> Optional[str]:
        """Extract email address from bio text"""
        if not bio:
            return None

        # Common email patterns
        email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
        match = re.search(email_pattern, bio)
        return match.group(0) if match else None

    def format_profile_data(self, user_info: dict) -> Dict:
        """Format user info into a clean profile object"""
        # The user_info dict structure from TikTok API
        user_data = user_info.get('userInfo', {}).get('user', {})
        stats = user_info.get('userInfo', {}).get('stats', {})

        bio = user_data.get('signature', '')
        email = self.extract_email_from_bio(bio)

        follower_count = stats.get('followerCount', 0)
        video_count = stats.get('videoCount', 0)
        heart_count = stats.get('heartCount', 0)  # Total likes across all videos

        # Calculate engagement metrics from available data
        avg_likes_per_video = round(heart_count / video_count, 2) if video_count > 0 else 0
        likes_to_followers_ratio = round(heart_count / follower_count, 2) if follower_count > 0 else 0

        profile = {
            'username': f"@{user_data.get('uniqueId', '')}",
            'display_name': user_data.get('nickname', ''),
            'user_id': user_data.get('id', ''),
            'sec_uid': user_data.get('secUid', ''),
            'bio': bio,
            'email': email,
            'follower_count': follower_count,
            'following_count': stats.get('followingCount', 0),
            'video_count': video_count,
            'heart_count': heart_count,  # Total likes received
            'avg_likes_per_video': avg_likes_per_video,  # Calculated: hearts / videos
            'likes_to_followers_ratio': likes_to_followers_ratio,  # Engagement indicator
            'is_verified': user_data.get('verified', False),
            'profile_url': f"https://www.tiktok.com/@{user_data.get('uniqueId', '')}",
            'avatar_url': user_data.get('avatarLarger', ''),
            'scraped_at': datetime.now().isoformat()
        }

        return profile

    async def save_profile(self, profile: Dict):
        """Save profile to JSON file incrementally (thread-safe)"""
        if profile:
            async with self.data_lock:
                self.profiles_data.append(profile)

                # Save to file
                with open(self.output_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        'total_profiles': len(self.profiles_data),
                        'last_updated': datetime.now().isoformat(),
                        'profiles': self.profiles_data
                    }, f, indent=2, ensure_ascii=False)

                print(f"  💾 Saved to {self.output_file} (Total: {len(self.profiles_data)})")

    def prepare_contact_data(self, profile: Dict) -> Dict:
        """
        Convert TikTok profile data to contact table format

        Maps TikTok fields to the contact table schema:
        - firstname: display_name (no splitting)
        - lastname: leave empty
        - email: from email field
        - platform: ['tiktok']
        - tags: categorization tags
        - description: display_name + bio text
        - metadata: only engagement/demographic metrics
        """
        display_name = profile.get('display_name', '').strip()
        bio = profile.get('bio', '').strip()

        # Build description with display_name and bio
        description_parts = []
        if display_name:
            description_parts.append(f"Name: {display_name}")
        if bio:
            description_parts.append(bio)
        description = '\n'.join(description_parts) if description_parts else None

        # Generate tags based on profile data
        tags = ['tiktok']
        if 'ugc' in bio.lower() or 'ugc' in display_name.lower():
            tags.append('ugc-creator')
        if profile.get('follower_count', 0) < 10000:
            tags.append('nano-influencer')
        elif profile.get('follower_count', 0) < 100000:
            tags.append('micro-influencer')
        elif profile.get('follower_count', 0) < 1000000:
            tags.append('mid-tier-influencer')
        else:
            tags.append('macro-influencer')

        # Store only engagement and demographic metrics in metadata
        metadata = {
            'tiktok': {
                'username': profile.get('username'),
                'profile_url': profile.get('profile_url'),
                'follower_count': profile.get('follower_count'),
                'following_count': profile.get('following_count'),
                'video_count': profile.get('video_count'),
                'heart_count': profile.get('heart_count'),
                'avg_likes_per_video': profile.get('avg_likes_per_video'),
                'likes_to_followers_ratio': profile.get('likes_to_followers_ratio'),
                'is_verified': profile.get('is_verified')
            }
        }

        return {
            'firstname': display_name if display_name else None,
            'lastname': None,
            'email': profile.get('email'),
            'platform': ['tiktok'],
            'tags': tags,
            'description': description,
            'metadata': metadata
        }

    def insert_profiles_to_supabase(self) -> int:
        """
        Insert all scraped profiles into Supabase contact table

        Returns:
            Number of profiles successfully inserted
        """
        if not self.supabase:
            print("\n⚠️  Supabase client not initialized. Skipping database insert.")
            return 0

        if not self.profiles_data:
            print("\n⚠️  No profiles to insert.")
            return 0

        print("\n" + "="*70)
        print("INSERTING PROFILES TO SUPABASE")
        print("="*70)

        inserted_count = 0
        errors = []

        for profile in self.profiles_data:
            try:
                contact_data = self.prepare_contact_data(profile)

                # Insert into contact table
                response = self.supabase.table('contact').insert(contact_data).execute()

                print(f"✓ Inserted: {profile.get('username')} ({profile.get('email', 'no email')})")
                inserted_count += 1

            except Exception as e:
                error_msg = f"✗ Failed to insert {profile.get('username')}: {str(e)}"
                print(error_msg)
                errors.append(error_msg)
                continue

        print("\n" + "="*70)
        print("SUPABASE INSERT COMPLETE")
        print("="*70)
        print(f"✓ Successfully inserted: {inserted_count}/{len(self.profiles_data)}")
        if errors:
            print(f"✗ Errors: {len(errors)}")
            print("\nError details:")
            for error in errors[:5]:  # Show first 5 errors
                print(f"  {error}")
        print("="*70)

        return inserted_count

    async def search_single_term(
        self,
        api: TikTokApi,
        search_term: str,
        users_per_search: int,
        filter_emails_only: bool,
        task_id: int = 0
    ) -> int:
        """
        Search for TikTok users for a single search term using a shared API instance.

        Args:
            api: Shared TikTokApi instance with sessions already created
            search_term: Search keyword
            users_per_search: Number of users to get for this term
            filter_emails_only: Only save users with emails in their bio
            task_id: Task identifier for logging

        Returns:
            Number of users found for this search term
        """
        print(f"\n[Task {task_id}] {'='*60}")
        print(f"[Task {task_id}] 🔍 Searching for: '{search_term}'")
        print(f"[Task {task_id}] {'='*60}\n")

        users_found = 0
        profiles_checked = 0  # Track how many TikTok returned

        try:
            async for user in api.search.users(search_term, count=users_per_search):
                profiles_checked += 1
                try:
                    username = user.username

                    # Check if already visited (thread-safe)
                    async with self.visited_lock:
                        if username in self.visited_usernames:
                            print(f"[Task {task_id}]   ⏭️  Skipping @{username} (already visited)")
                            continue
                        # Mark as visited immediately
                        self.visited_usernames.add(username)

                    print(f"[Task {task_id}]   📥 Fetching profile: @{username}")

                    # Get detailed user info
                    user_info = await user.info()

                    # Format the profile data
                    profile = self.format_profile_data(user_info)

                    # Check email filter
                    if filter_emails_only and not profile.get('email'):
                        print(f"[Task {task_id}]   ⏭️  No email found, skipping")
                        continue

                    print(f"[Task {task_id}]   ✓ @{username}")
                    print(f"[Task {task_id}]     Name: {profile['display_name']}")
                    print(f"[Task {task_id}]     Followers: {profile['follower_count']:,}")
                    print(f"[Task {task_id}]     Videos: {profile['video_count']} | Avg Likes: {profile['avg_likes_per_video']:,.0f}")
                    if profile.get('email'):
                        print(f"[Task {task_id}]     📧 Email: {profile['email']}")

                    # Save profile (thread-safe)
                    await self.save_profile(profile)
                    users_found += 1

                    # Small delay to be respectful
                    await asyncio.sleep(1)

                except Exception as e:
                    print(f"[Task {task_id}]   ✗ Error fetching user: {e}")
                    continue

            print(f"\n[Task {task_id}] ✓ Found {users_found} users with emails (checked {profiles_checked} profiles) for '{search_term}'")

        except Exception as e:
            print(f"[Task {task_id}] ✗ Error searching for '{search_term}': {e}")
            import traceback
            traceback.print_exc()

        return users_found

    async def search_users(
        self,
        search_terms: List[str],
        users_per_search: int = 50,
        filter_emails_only: bool = True,
        proxies: Optional[List[str]] = None,
        fetch_unique_tokens: bool = True
    ):
        """
        Search for TikTok users by keywords (PARALLELIZED).
        Each search term runs concurrently using a shared TikTok API instance with multiple sessions.

        Args:
            search_terms: List of search keywords (e.g., ["entrepreneur", "business coach"])
            users_per_search: Number of users to get per search term
            filter_emails_only: Only save users with emails in their bio
            proxies: List of proxy strings in format "ip:port:username:password"
            fetch_unique_tokens: Whether to fetch unique MS tokens (slower but better results)
        """
        print("="*70)
        print("TIKTOK API USER SCRAPER (PARALLEL MODE)")
        print("="*70)
        print(f"Search terms: {len(search_terms)} terms")
        print(f"Users per search: {users_per_search}")
        print(f"Filter emails only: {filter_emails_only}")
        print(f"Output file: {self.output_file}")
        print(f"Proxies available: {len(proxies) if proxies else 0}")
        print("="*70 + "\n")

        # Parse proxies into Playwright format
        proxies_list = []
        if proxies:
            for proxy in proxies:
                parts = proxy.split(':')
                if len(parts) == 4:
                    ip, port, username, password = parts[0], parts[1], parts[2], parts[3]
                    proxy_config = {
                        'server': f'http://{ip}:{port}',
                        'username': username,
                        'password': password
                    }
                    proxies_list.append(proxy_config)
                    print(f"  ✓ Proxy configured: {ip}:{port}")

        # Determine number of sessions to create (limit to avoid overwhelming the system)
        MAX_CONCURRENT_SESSIONS = 5  # Limit to 5 browsers at once
        num_sessions = min(len(search_terms), len(proxies_list), MAX_CONCURRENT_SESSIONS) if proxies_list else min(len(search_terms), MAX_CONCURRENT_SESSIONS)

        # Fetch unique MS tokens for each session (if enabled)
        if fetch_unique_tokens:
            print(f"🎫 Fetching {num_sessions} unique MS tokens for better results...")
            ms_tokens = await fetch_multiple_ms_tokens(
                num_tokens=num_sessions,
                use_proxies=True if proxies_list else False,
                proxies_list=proxies_list if proxies_list else None
            )

            # Fallback to single token or None if fetching failed
            if not any(ms_tokens):
                print("⚠️  No tokens fetched, falling back to environment token")
                ms_tokens = [self.ms_token] * num_sessions if self.ms_token else [None] * num_sessions
            else:
                # Replace None values with the first successful token
                first_valid_token = next((t for t in ms_tokens if t), self.ms_token)
                ms_tokens = [t if t else first_valid_token for t in ms_tokens]
                print(f"✓ Using {len([t for t in ms_tokens if t])} unique MS tokens")
        else:
            # Reuse same token for all sessions (faster but may be rate limited)
            print(f"⚠️  Using same MS token for all {num_sessions} sessions (fast but may limit results)")
            ms_tokens = [self.ms_token] * num_sessions if self.ms_token else [None] * num_sessions

        print(f"\n🌐 Creating {num_sessions} TikTok API sessions...")
        if num_sessions < len(search_terms):
            print(f"   Note: {len(search_terms)} search terms will share {num_sessions} sessions for stability")

        # Create one shared TikTokApi instance with multiple sessions
        async with TikTokApi() as api:
            try:
                await api.create_sessions(
                    ms_tokens=ms_tokens,
                    num_sessions=num_sessions,
                    sleep_after=5,  # Increased from 3 to 5 seconds
                    headless=False,
                    browser='chromium',
                    suppress_resource_load_types=["stylesheet", "font", "image"],
                    proxies=proxies_list if proxies_list else None,
                    timeout=60000  # 60 second timeout (increased from default 30s)
                )
                print(f"✓ Created {num_sessions} sessions successfully\n")
            except Exception as e:
                print(f"✗ ERROR: Could not create sessions: {e}")
                import traceback
                traceback.print_exc()

                if proxies_list:
                    print("\nTrying without proxies...")
                    try:
                        await api.create_sessions(
                            ms_tokens=ms_tokens,
                            num_sessions=num_sessions,
                            sleep_after=5,
                            headless=False,
                            browser='chromium',
                            suppress_resource_load_types=["stylesheet", "font", "image"],
                            timeout=60000
                        )
                        print(f"✓ Created {num_sessions} sessions (without proxies)\n")
                    except Exception as e2:
                        print(f"✗ FATAL: Could not create sessions: {e2}")
                        return
                else:
                    return

            # Create tasks for each search term (all sharing the same API instance)
            tasks = []
            for i, search_term in enumerate(search_terms):
                task = self.search_single_term(
                    api=api,  # Pass shared API instance
                    search_term=search_term,
                    users_per_search=users_per_search,
                    filter_emails_only=filter_emails_only,
                    task_id=i + 1
                )
                tasks.append(task)

            print(f"🚀 Starting {len(tasks)} parallel search tasks...\n")

            # Run all tasks concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Count successful results
            total_found = 0
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    print(f"\n⚠️  Task {i+1} failed with error: {result}")
                else:
                    total_found += result

            print("\n" + "="*70)
            print("PARALLEL SCRAPING COMPLETE")
            print("="*70)
            print(f"✓ Total profiles scraped: {total_found}")
            print(f"✓ Saved to: {self.output_file}")
            if filter_emails_only:
                emails_found = len([p for p in self.profiles_data if p.get('email')])
                print(f"✓ Profiles with emails: {emails_found}")
            print("="*70)

            # Insert profiles to Supabase if enabled and client is initialized
            post_to_supabase = os.getenv('POST_TO_SUPABASE', 'false').lower() == 'true'
            if post_to_supabase and self.supabase:
                self.insert_profiles_to_supabase()
            elif self.supabase and not post_to_supabase:
                print("\n⚠️  Supabase client initialized but POST_TO_SUPABASE is disabled.")
                print("   Set POST_TO_SUPABASE=true in .env to enable database inserts.")

    async def get_user_profile(self, username: str) -> Optional[Dict]:
        """
        Get a single user's profile by username

        Args:
            username: TikTok username (with or without @)

        Returns:
            Dict with user profile data or None if error
        """
        async with TikTokApi() as api:
            print(f"🔍 Fetching profile for: {username}")

            # Parse proxy if provided
            proxies_list = None
            if self.proxy:
                parts = self.proxy.split(':')
                if len(parts) == 4:
                    ip, port, username, password = parts[0], parts[1], parts[2], parts[3]
                    proxy_config = {
                        'server': f'http://{ip}:{port}',
                        'username': username,
                        'password': password
                    }
                    proxies_list = [proxy_config]
                    print(f"✓ Using proxy: {ip}:{port} (auth: {username})")

            try:
                await api.create_sessions(
                    ms_tokens=[self.ms_token] if self.ms_token else [None],
                    num_sessions=1,
                    sleep_after=5,
                    headless=False,
                    browser="chromium",
                    suppress_resource_load_types=["stylesheet", "font", "image"],
                    proxies=proxies_list
                )

                # Remove @ if present
                username = username.lstrip('@')

                user = api.user(username=username)
                user_info = await user.info()

                profile = self.format_profile_data(user_info)

                print(f"✓ Profile fetched: @{profile['username']}")
                print(f"  Name: {profile['display_name']}")
                print(f"  Followers: {profile['follower_count']:,}")
                if profile.get('email'):
                    print(f"  📧 Email: {profile['email']}")

                return profile

            except Exception as e:
                print(f"✗ Error: {e}")
                import traceback
                traceback.print_exc()
                return None


async def main():
    """Main function - configure and run scraper"""

    # Try to fetch a fresh MS token automatically
    print("\n🚀 STARTING TIKTOK SCRAPER")
    print("="*70)

    ms_token = await fetch_fresh_ms_token()

    # Fallback to environment variable if fetching fails
    if not ms_token:
        print("⚠️  Attempting to use MS_TOKEN from environment variable...")
        ms_token = os.getenv('TIKTOK_MS_TOKEN')

        if not ms_token:
            print("="*70)
            print("⚠️  WARNING: NO MS TOKEN FOUND!")
            print("="*70)
            print("TikTok will likely block your requests without an ms_token.")
            print("\nHow to get your ms_token:")
            print("1. Go to tiktok.com in your browser")
            print("2. Do a search for any keyword")
            print("3. Open DevTools (F12) -> Application -> Cookies -> tiktok.com")
            print("4. Copy the 'msToken' cookie value")
            print("5. Add to .env: TIKTOK_MS_TOKEN=your_token_here")
            print("\nPress Enter to continue anyway, or Ctrl+C to exit...")
            input()
        else:
            print(f"✓ Using MS_TOKEN from environment variable")
            print(f"  Token: {ms_token[:20]}...{ms_token[-20:]}\n")

    # Configuration
    USE_AI_GENERATED_QUERIES = os.getenv('USE_AI_QUERIES', 'true').lower() == 'true'
    NUM_QUERIES_TO_GENERATE = int(os.getenv('NUM_SEARCH_QUERIES', '15'))
    FOCUS_AREA = os.getenv('SEARCH_FOCUS_AREA', 'UGC creators and content creators who work with brands')
    
    USERS_PER_SEARCH = int(os.getenv('USERS_PER_SEARCH', '20'))  # How many users to get per search term
    FILTER_EMAILS_ONLY = os.getenv('FILTER_EMAILS_ONLY', 'true').lower() == 'true'  # Only save users with emails in bio

    # Generate search queries using OpenAI
    if USE_AI_GENERATED_QUERIES:
        print("\n" + "="*70)
        print("GENERATING SEARCH QUERIES WITH OPENAI")
        print("="*70)
        print(f"Focus area: {FOCUS_AREA}")
        print(f"Number of queries: {NUM_QUERIES_TO_GENERATE}")
        print("="*70 + "\n")
        
        SEARCH_TERMS = await generate_search_queries(
            num_queries=NUM_QUERIES_TO_GENERATE,
            focus_area=FOCUS_AREA
        )
        
        print("\nGenerated search queries:")
        for i, term in enumerate(SEARCH_TERMS, 1):
            print(f"  {i}. {term}")
        print()
    else:
        # Use default hardcoded search terms
        SEARCH_TERMS = [
            "ugc creator",
            "user generated content",
            "brand deals",
            "content creator for hire",
            "collab with brands",
            "gifted pr",
            "micro influencer",
            "nano influencer"
        ]
        print(f"Using default search terms: {', '.join(SEARCH_TERMS)}")

    # Get Supabase credentials from environment
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')
    POST_TO_SUPABASE = os.getenv('POST_TO_SUPABASE', 'false').lower() == 'true'


    # Proxy list (format: ip:port:username:password) - distributed across parallel tasks
    PROXIES = [
        "142.111.48.253:7030:nxdfbugl:mfptu9q4swio",
        "31.59.20.176:6754:nxdfbugl:mfptu9q4swio",
        "23.95.150.145:6114:nxdfbugl:mfptu9q4swio",
        "198.23.239.134:6540:nxdfbugl:mfptu9q4swio",
        "45.38.107.97:6014:nxdfbugl:mfptu9q4swio",
        "107.172.163.27:6543:nxdfbugl:mfptu9q4swio",
        "64.137.96.74:6641:nxdfbugl:mfptu9q4swio",
        "216.10.27.159:6837:nxdfbugl:mfptu9q4swio",
        "142.111.67.146:5611:nxdfbugl:mfptu9q4swio",
        "142.147.128.93:6593:nxdfbugl:mfptu9q4swio",
    ]

    # Initialize scraper (no single proxy needed - each parallel task gets its own)
    scraper = TikTokUserScraper(
        ms_token=ms_token,  # Pass the fresh MS token
        output_file='tiktok_api_users.json',
        supabase_url=supabase_url,
        supabase_key=supabase_key
    )

    if supabase_url and supabase_key:
        if POST_TO_SUPABASE:
            print("✓ Supabase posting ENABLED - profiles will be inserted to database")
        else:
            print("⚠️  Supabase credentials found but POST_TO_SUPABASE=false")
            print("   Profiles will be saved to JSON only. Set POST_TO_SUPABASE=true to enable database inserts.")

    # Search for users in parallel - each search term runs concurrently with its own proxy
    await scraper.search_users(
        search_terms=SEARCH_TERMS,
        users_per_search=USERS_PER_SEARCH,
        filter_emails_only=FILTER_EMAILS_ONLY,
        proxies=PROXIES  # Pass all proxies - they'll be distributed across tasks
    )

    # Or get a single user profile:
    # profile = await scraper.get_user_profile('therock')


async def run_campaign_scraper(
    campaign_description: str,
    num_queries: int = 10,
    users_per_search: int = 10,
    filter_emails_only: bool = True,
    supabase_url: Optional[str] = None,
    supabase_key: Optional[str] = None,
    fetch_unique_tokens: bool = True
) -> int:
    """
    Run the TikTok scraper for a specific campaign.
    This is the main entry point for the FastAPI backend.

    Args:
        campaign_description: Description of the campaign to use for generating search queries
        num_queries: Number of search queries to generate (default: 10)
        users_per_search: Number of users to scrape per search term (default: 10)
        filter_emails_only: Only save profiles with emails (default: True)
        supabase_url: Supabase project URL (optional, falls back to env var)
        supabase_key: Supabase key (optional, falls back to env var)
        fetch_unique_tokens: Fetch unique MS tokens for each session (slower but better results, default: True)

    Returns:
        Number of profiles scraped and saved
    """
    print("\n🚀 STARTING CAMPAIGN SCRAPER")
    print("="*70)
    print(f"Campaign focus: {campaign_description}")
    print("="*70)

    # Get MS token from environment (auto-fetch is too slow for API calls)
    ms_token = os.getenv('TIKTOK_MS_TOKEN')
    # ms_token = await fetch_fresh_ms_token()
    if not ms_token:
        print("⚠️  WARNING: TIKTOK_MS_TOKEN not found in environment")
        print("   The scraper may not work without a valid ms_token")

    # Generate search queries using the campaign description
    search_terms = await generate_search_queries(
        num_queries=num_queries,
        focus_area=campaign_description
    )

    print(f"\nGenerated {len(search_terms)} search queries:")
    for i, term in enumerate(search_terms, 1):
        print(f"  {i}. {term}")
    print()

    # Use provided Supabase credentials or fall back to environment
    supabase_url = supabase_url or os.getenv('SUPABASE_URL')
    supabase_key = supabase_key or os.getenv('SUPABASE_KEY')

    # Proxy list - will be distributed across parallel tasks
    PROXIES = [
        "142.111.48.253:7030:nxdfbugl:mfptu9q4swio",
        "31.59.20.176:6754:nxdfbugl:mfptu9q4swio",
        "23.95.150.145:6114:nxdfbugl:mfptu9q4swio",
        "198.23.239.134:6540:nxdfbugl:mfptu9q4swio",
        "45.38.107.97:6014:nxdfbugl:mfptu9q4swio",
        "107.172.163.27:6543:nxdfbugl:mfptu9q4swio",
        "64.137.96.74:6641:nxdfbugl:mfptu9q4swio",
        "216.10.27.159:6837:nxdfbugl:mfptu9q4swio",
        "142.111.67.146:5611:nxdfbugl:mfptu9q4swio",
        "142.147.128.93:6593:nxdfbugl:mfptu9q4swio",
    ]

    # Initialize scraper (no single proxy needed - each task gets its own)
    scraper = TikTokUserScraper(
        ms_token=ms_token,
        output_file='tiktok_campaign_scrape.json',
        supabase_url=supabase_url,
        supabase_key=supabase_key
    )

    # Run the scraping in parallel - each search term gets a different proxy
    await scraper.search_users(
        search_terms=search_terms,
        users_per_search=users_per_search,
        filter_emails_only=filter_emails_only,
        proxies=PROXIES,  # Pass all proxies - they'll be distributed across tasks
        fetch_unique_tokens=fetch_unique_tokens  # Whether to fetch unique tokens
    )

    # Return the number of profiles scraped
    profiles_count = len(scraper.profiles_data)
    print(f"\n✓ Campaign scraper completed: {profiles_count} profiles scraped")

    return profiles_count


class TikTokUserScraperSync:
    """
    Simplified synchronous TikTok scraper.
    Uses a single browser session with one proxy and searches sequentially.
    Better for avoiding bot detection and rate limits.
    """

    def __init__(self, ms_token: Optional[str] = None, output_file: str = "tiktok_sync_profiles.json",
                 supabase_url: Optional[str] = None, supabase_key: Optional[str] = None, proxy: Optional[str] = None):
        self.ms_token = ms_token or os.getenv('TIKTOK_MS_TOKEN')
        self.output_file = output_file
        self.profiles_data: List[Dict] = []
        self.visited_usernames: set = set()
        self.proxy = proxy

        # Initialize Supabase client if credentials provided
        self.supabase: Optional[Client] = None
        if supabase_url and supabase_key:
            self.supabase = create_client(supabase_url, supabase_key)
            print("✓ Supabase client initialized")

    def extract_email_from_bio(self, bio: str) -> Optional[str]:
        """Extract email address from bio text"""
        if not bio:
            return None
        email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
        match = re.search(email_pattern, bio)
        return match.group(0) if match else None

    def format_profile_data(self, user_info: dict) -> Dict:
        """Format user info into a clean profile object"""
        user_data = user_info.get('userInfo', {}).get('user', {})
        stats = user_info.get('userInfo', {}).get('stats', {})

        bio = user_data.get('signature', '')
        email = self.extract_email_from_bio(bio)

        follower_count = stats.get('followerCount', 0)
        video_count = stats.get('videoCount', 0)
        heart_count = stats.get('heartCount', 0)

        avg_likes_per_video = round(heart_count / video_count, 2) if video_count > 0 else 0
        likes_to_followers_ratio = round(heart_count / follower_count, 2) if follower_count > 0 else 0

        profile = {
            'username': f"@{user_data.get('uniqueId', '')}",
            'display_name': user_data.get('nickname', ''),
            'user_id': user_data.get('id', ''),
            'sec_uid': user_data.get('secUid', ''),
            'bio': bio,
            'email': email,
            'follower_count': follower_count,
            'following_count': stats.get('followingCount', 0),
            'video_count': video_count,
            'heart_count': heart_count,
            'avg_likes_per_video': avg_likes_per_video,
            'likes_to_followers_ratio': likes_to_followers_ratio,
            'is_verified': user_data.get('verified', False),
            'profile_url': f"https://www.tiktok.com/@{user_data.get('uniqueId', '')}",
            'avatar_url': user_data.get('avatarLarger', ''),
            'scraped_at': datetime.now().isoformat()
        }

        return profile

    def save_profile(self, profile: Dict):
        """Save profile to JSON file incrementally"""
        if profile:
            self.profiles_data.append(profile)

            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'total_profiles': len(self.profiles_data),
                    'last_updated': datetime.now().isoformat(),
                    'profiles': self.profiles_data
                }, f, indent=2, ensure_ascii=False)

            print(f"  💾 Saved to {self.output_file} (Total: {len(self.profiles_data)})")

    def prepare_contact_data(self, profile: Dict) -> Dict:
        """Convert TikTok profile data to contact table format"""
        display_name = profile.get('display_name', '').strip()
        bio = profile.get('bio', '').strip()

        description_parts = []
        if display_name:
            description_parts.append(f"Name: {display_name}")
        if bio:
            description_parts.append(bio)
        description = '\n'.join(description_parts) if description_parts else None

        tags = ['tiktok']
        if 'ugc' in bio.lower() or 'ugc' in display_name.lower():
            tags.append('ugc-creator')
        if profile.get('follower_count', 0) < 10000:
            tags.append('nano-influencer')
        elif profile.get('follower_count', 0) < 100000:
            tags.append('micro-influencer')
        elif profile.get('follower_count', 0) < 1000000:
            tags.append('mid-tier-influencer')
        else:
            tags.append('macro-influencer')

        metadata = {
            'tiktok': {
                'username': profile.get('username'),
                'profile_url': profile.get('profile_url'),
                'follower_count': profile.get('follower_count'),
                'following_count': profile.get('following_count'),
                'video_count': profile.get('video_count'),
                'heart_count': profile.get('heart_count'),
                'avg_likes_per_video': profile.get('avg_likes_per_video'),
                'likes_to_followers_ratio': profile.get('likes_to_followers_ratio'),
                'is_verified': profile.get('is_verified')
            }
        }

        return {
            'firstname': display_name if display_name else None,
            'lastname': None,
            'email': profile.get('email'),
            'platform': ['tiktok'],
            'tags': tags,
            'description': description,
            'metadata': metadata
        }

    def insert_profiles_to_supabase(self) -> int:
        """Insert all scraped profiles into Supabase contact table"""
        if not self.supabase:
            print("\n⚠️  Supabase client not initialized. Skipping database insert.")
            return 0

        if not self.profiles_data:
            print("\n⚠️  No profiles to insert.")
            return 0

        print("\n" + "="*70)
        print("INSERTING PROFILES TO SUPABASE")
        print("="*70)

        inserted_count = 0
        errors = []

        for profile in self.profiles_data:
            try:
                contact_data = self.prepare_contact_data(profile)
                self.supabase.table('contact').insert(contact_data).execute()
                print(f"✓ Inserted: {profile.get('username')} ({profile.get('email', 'no email')})")
                inserted_count += 1
            except Exception as e:
                error_msg = f"✗ Failed to insert {profile.get('username')}: {str(e)}"
                print(error_msg)
                errors.append(error_msg)
                continue

        print("\n" + "="*70)
        print("SUPABASE INSERT COMPLETE")
        print("="*70)
        print(f"✓ Successfully inserted: {inserted_count}/{len(self.profiles_data)}")
        if errors:
            print(f"✗ Errors: {len(errors)}")
            print("\nError details:")
            for error in errors[:5]:
                print(f"  {error}")
        print("="*70)

        return inserted_count

    async def search_users_sequential(
        self,
        search_terms: List[str],
        users_per_search: int = 50,
        filter_emails_only: bool = True
    ):
        """
        Search for TikTok users sequentially (one at a time).
        Uses a single browser session with one proxy.

        Args:
            search_terms: List of search keywords
            users_per_search: Number of users to get per search term
            filter_emails_only: Only save users with emails in their bio
        """
        print("="*70)
        print("TIKTOK API USER SCRAPER (SEQUENTIAL MODE)")
        print("="*70)
        print(f"Search terms: {len(search_terms)} terms")
        print(f"Users per search: {users_per_search}")
        print(f"Filter emails only: {filter_emails_only}")
        print(f"Output file: {self.output_file}")
        if self.proxy:
            parts = self.proxy.split(':')
            if len(parts) >= 2:
                print(f"Proxy: {parts[0]}:{parts[1]}")
        print("="*70 + "\n")

        # Parse proxy if provided
        proxies_list = None
        if self.proxy:
            parts = self.proxy.split(':')
            if len(parts) == 4:
                ip, port, username, password = parts[0], parts[1], parts[2], parts[3]
                proxy_config = {
                    'server': f'http://{ip}:{port}',
                    'username': username,
                    'password': password
                }
                proxies_list = [proxy_config]
                print(f"✓ Using proxy: {ip}:{port}\n")

        # Create one TikTok API instance with one session
        async with TikTokApi() as api:
            print("🌐 Creating single TikTok API session...")
            try:
                await api.create_sessions(
                    ms_tokens=[self.ms_token] if self.ms_token else [None],
                    num_sessions=1,
                    sleep_after=5,
                    headless=False,
                    browser='chromium',
                    suppress_resource_load_types=["stylesheet", "font", "image"],
                    proxies=proxies_list,
                    timeout=60000
                )
                print("✓ Session created successfully\n")
            except Exception as e:
                print(f"✗ ERROR: Could not create session: {e}")
                return

            total_found = 0

            # Search for each term sequentially
            for idx, search_term in enumerate(search_terms, 1):
                print(f"\n{'='*70}")
                print(f"🔍 [{idx}/{len(search_terms)}] Searching for: '{search_term}'")
                print(f"{'='*70}\n")

                profiles_checked = 0
                users_found = 0

                try:
                    async for user in api.search.users(search_term, count=users_per_search):
                        profiles_checked += 1
                        try:
                            username = user.username

                            # Skip if already visited
                            if username in self.visited_usernames:
                                print(f"  ⏭️  Skipping @{username} (already visited)")
                                continue

                            print(f"  📥 Fetching profile: @{username}")

                            # Get detailed user info
                            user_info = await user.info()

                            # Format the profile data
                            profile = self.format_profile_data(user_info)

                            # Check email filter
                            if filter_emails_only and not profile.get('email'):
                                print(f"  ⏭️  No email found, skipping")
                                continue

                            print(f"  ✓ @{username}")
                            print(f"    Name: {profile['display_name']}")
                            print(f"    Followers: {profile['follower_count']:,}")
                            print(f"    Videos: {profile['video_count']} | Avg Likes: {profile['avg_likes_per_video']:,.0f}")
                            if profile.get('email'):
                                print(f"    📧 Email: {profile['email']}")

                            # Save profile
                            self.save_profile(profile)

                            self.visited_usernames.add(username)
                            users_found += 1
                            total_found += 1

                            # Small delay to be respectful
                            await asyncio.sleep(1)

                        except Exception as e:
                            print(f"  ✗ Error fetching user: {e}")
                            continue

                    print(f"\n✓ Found {users_found} users with emails (checked {profiles_checked} profiles) for '{search_term}'")

                except Exception as e:
                    print(f"✗ Error searching for '{search_term}': {e}")
                    import traceback
                    traceback.print_exc()
                    continue

            print("\n" + "="*70)
            print("SEQUENTIAL SCRAPING COMPLETE")
            print("="*70)
            print(f"✓ Total profiles scraped: {total_found}")
            print(f"✓ Saved to: {self.output_file}")
            if filter_emails_only:
                emails_found = len([p for p in self.profiles_data if p.get('email')])
                print(f"✓ Profiles with emails: {emails_found}")
            print("="*70)

            # Insert profiles to Supabase if enabled
            if self.supabase:
                self.insert_profiles_to_supabase()


async def run_campaign_scraper_sync(
    campaign_description: str,
    num_queries: int = 10,
    users_per_search: int = 10,
    filter_emails_only: bool = True,
    supabase_url: Optional[str] = None,
    supabase_key: Optional[str] = None,
    ms_token: Optional[str] = None
) -> int:
    """
    Run the sequential TikTok scraper (simpler, one session, one proxy).

    Args:
        campaign_description: Description of the campaign
        num_queries: Number of search queries to generate
        users_per_search: Number of users to scrape per search term
        filter_emails_only: Only save profiles with emails
        supabase_url: Supabase project URL
        supabase_key: Supabase key
        ms_token: MS token to use (optional, falls back to environment)

    Returns:
        Number of profiles scraped
    """
    print("\n🚀 STARTING SEQUENTIAL CAMPAIGN SCRAPER")
    print("="*70)
    print(f"Campaign focus: {campaign_description}")
    print("="*70)

    # Get MS token from parameter or environment
    if not ms_token:
        ms_token = os.getenv('TIKTOK_MS_TOKEN')
        if not ms_token:
            print("⚠️  WARNING: TIKTOK_MS_TOKEN not found in environment")
        else:
            print(f"✓ Using MS token from environment: {ms_token[:20]}...{ms_token[-10:]}")
    else:
        print(f"✓ Using provided MS token: {ms_token[:20]}...{ms_token[-10:]}")

    # Generate search queries
    search_terms = await generate_search_queries(
        num_queries=num_queries,
        focus_area=campaign_description
    )

    print(f"\nGenerated {len(search_terms)} search queries:")
    for i, term in enumerate(search_terms, 1):
        print(f"  {i}. {term}")
    print()

    # Use provided Supabase credentials or fall back to environment
    supabase_url = supabase_url or os.getenv('SUPABASE_URL')
    supabase_key = supabase_key or os.getenv('SUPABASE_KEY')

    # Proxy list - pick one randomly
    PROXIES = [
        "142.111.48.253:7030:nxdfbugl:mfptu9q4swio",
        "31.59.20.176:6754:nxdfbugl:mfptu9q4swio",
        "23.95.150.145:6114:nxdfbugl:mfptu9q4swio",
        "198.23.239.134:6540:nxdfbugl:mfptu9q4swio",
        "45.38.107.97:6014:nxdfbugl:mfptu9q4swio",
        "107.172.163.27:6543:nxdfbugl:mfptu9q4swio",
        "64.137.96.74:6641:nxdfbugl:mfptu9q4swio",
        "216.10.27.159:6837:nxdfbugl:mfptu9q4swio",
        "142.111.67.146:5611:nxdfbugl:mfptu9q4swio",
        "142.147.128.93:6593:nxdfbugl:mfptu9q4swio",
    ]

    import random
    selected_proxy = random.choice(PROXIES)
    print(f"📍 Selected random proxy: {selected_proxy.split(':')[0]}:{selected_proxy.split(':')[1]}\n")

    # Initialize scraper
    scraper = TikTokUserScraperSync(
        ms_token=ms_token,
        output_file='tiktok_sync_scrape.json',
        supabase_url=supabase_url,
        supabase_key=supabase_key,
        proxy=selected_proxy
    )

    # Run the sequential scraping
    await scraper.search_users_sequential(
        search_terms=search_terms,
        users_per_search=users_per_search,
        filter_emails_only=filter_emails_only
    )

    # Return the number of profiles scraped
    profiles_count = len(scraper.profiles_data)
    print(f"\n✓ Sequential scraper completed: {profiles_count} profiles scraped")

    return profiles_count


if __name__ == '__main__':
    asyncio.run(main())
