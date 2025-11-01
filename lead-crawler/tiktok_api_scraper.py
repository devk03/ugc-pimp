"""
TikTok User Scraper using TikTok-Api
Uses the unofficial TikTok API to search for users and extract profile data

Features:
- Search for users by keywords
- Extract comprehensive profile information including engagement metrics
- Find emails in user bios
- Calculate avg_likes_per_video and engagement ratios from profile stats
- Save results to JSON incrementally
- Much faster than browser automation

Note: Individual video fetching doesn't work due to TikTok's bot detection.
      However, profile stats (heart_count, video_count) let us calculate useful engagement metrics!

Setup:
    pip install TikTokApi
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

Usage:
    python tiktok_api_scraper.py
"""

import asyncio
import json
import re
from datetime import datetime
from typing import List, Dict, Optional
from TikTokApi import TikTokApi
from dotenv import load_dotenv
import os
from supabase import create_client, Client

load_dotenv()


class TikTokUserScraper:
    """Scraper for TikTok users using the unofficial API"""

    def __init__(self, ms_token: Optional[str] = None, output_file: str = "tiktok_api_profiles.json",
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
        """Save profile to JSON file incrementally"""
        if profile:
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

    async def search_users(
        self,
        search_terms: List[str],
        users_per_search: int = 50,
        filter_emails_only: bool = True
    ):
        """
        Search for TikTok users by keywords

        Args:
            search_terms: List of search keywords (e.g., ["entrepreneur", "business coach"])
            users_per_search: Number of users to get per search term
            filter_emails_only: Only save users with emails in their bio
        """
        async with TikTokApi() as api:
            print("="*70)
            print("TIKTOK API USER SCRAPER")
            print("="*70)
            print(f"Search terms: {', '.join(search_terms)}")
            print(f"Users per search: {users_per_search}")
            print(f"Filter emails only: {filter_emails_only}")
            print(f"Output file: {self.output_file}")
            print("="*70 + "\n")

            # Create browser sessions with anti-detection settings
            print("🌐 Creating browser sessions...")

            # Parse proxy if provided (format: ip:port:username:password)
            proxies_list = None
            if self.proxy:
                parts = self.proxy.split(':')
                if len(parts) == 4:
                    # Playwright ProxySettings format: separate username/password fields
                    ip, port, username, password = parts[0], parts[1], parts[2], parts[3]
                    proxy_config = {
                        'server': f'http://{ip}:{port}',
                        'username': username,
                        'password': password
                    }
                    proxies_list = [proxy_config]  # Pass as list
                    print(f"✓ Using proxy: {ip}:{port} (auth: {username})")
                else:
                    print(f"⚠️  Invalid proxy format, skipping proxy")

            try:
                await api.create_sessions(
                    ms_tokens=[self.ms_token] if self.ms_token else [None],
                    num_sessions=1,
                    sleep_after=5,
                    headless=False,
                    browser='chromium',
                    suppress_resource_load_types=["stylesheet", "font", "image"],
                    proxies=proxies_list  # Use the proxies parameter (list format)
                )
                print("✓ Sessions created\n")
            except Exception as e:
                print(f"✗ ERROR: Could not create sessions: {e}")
                import traceback
                traceback.print_exc()

                if proxies_list:
                    print("\nTrying without proxy...")
                    # Try again without proxy
                    try:
                        await api.create_sessions(
                            ms_tokens=[self.ms_token] if self.ms_token else [None],
                            num_sessions=1,
                            sleep_after=5,
                            headless=False,
                            browser='chromium',
                            suppress_resource_load_types=["stylesheet", "font", "image"],
                        )
                        print("✓ Sessions created (without proxy)\n")
                    except Exception as e2:
                        print(f"✗ FATAL: Still could not create sessions: {e2}")
                        raise
                else:
                    raise

            total_found = 0

            # Search for each term
            for search_term in search_terms:
                print(f"\n{'='*70}")
                print(f"🔍 Searching for: '{search_term}'")
                print(f"{'='*70}\n")

                try:
                    users_found = 0

                    async for user in api.search.users(search_term, count=users_per_search):
                        try:
                            username = user.username

                            # Skip if already visited
                            if username in self.visited_usernames:
                                print(f"  ⏭️  Skipping @{username} (already visited)")
                                continue

                            print(f"\n[{total_found + 1}] Fetching profile: @{username}")

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
                            print(f"    Total Hearts: {profile['heart_count']:,} | Engagement Ratio: {profile['likes_to_followers_ratio']}x")
                            if profile.get('email'):
                                print(f"    📧 Email: {profile['email']}")

                            # Save profile
                            await self.save_profile(profile)

                            self.visited_usernames.add(username)
                            users_found += 1
                            total_found += 1

                            # Small delay to be respectful
                            await asyncio.sleep(1)

                        except Exception as e:
                            print(f"  ✗ Error fetching user: {e}")
                            continue

                    print(f"\n✓ Found {users_found} users for '{search_term}'")

                except Exception as e:
                    print(f"✗ Error searching for '{search_term}': {e}")
                    import traceback
                    traceback.print_exc()
                    continue

            print("\n" + "="*70)
            print("SCRAPING COMPLETE")
            print("="*70)
            print(f"✓ Total profiles scraped: {total_found}")
            print(f"✓ Saved to: {self.output_file}")
            if filter_emails_only:
                emails_found = len([p for p in self.profiles_data if p.get('email')])
                print(f"✓ Profiles with emails: {emails_found}")
            print("="*70)

            # Insert profiles to Supabase if client is initialized
            if self.supabase:
                self.insert_profiles_to_supabase()

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

    # Check for MS token
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

    # Configuration
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
    USERS_PER_SEARCH = 20  # How many users to get per search term
    FILTER_EMAILS_ONLY = True  # Only save users with emails in bio

    # Get Supabase credentials from environment
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')

    # Proxy list (format: ip:port:username:password)
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

    # Pick a random proxy from the list
    import random
    selected_proxy = random.choice(PROXIES)

    # Initialize scraper
    scraper = TikTokUserScraper(
        output_file='tiktok_api_users.json',
        supabase_url=supabase_url,
        supabase_key=supabase_key,
        proxy=selected_proxy
    )

    # Search for users
    await scraper.search_users(
        search_terms=SEARCH_TERMS,
        users_per_search=USERS_PER_SEARCH,
        filter_emails_only=FILTER_EMAILS_ONLY
    )

    # Or get a single user profile:
    # profile = await scraper.get_user_profile('therock')


if __name__ == '__main__':
    asyncio.run(main())
