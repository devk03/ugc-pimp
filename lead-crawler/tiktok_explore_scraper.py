"""
TikTok Explore Scraper using Playwright
Navigates to tiktok.com/explore, clicks on user profiles, and extracts profile data

Features:
- Direct browser control with Playwright (no AI agent)
- Clicks on users from explore page
- Extracts comprehensive profile information
- Saves results to JSON incrementally
- Handles popups and login prompts

Setup:
    pip install playwright
    playwright install chromium

Usage:
    python tiktok_explore_scraper.py
"""

import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from typing import Dict, List, Optional


class TikTokExploreScraper:
    """Scraper for TikTok explore page using Playwright"""

    def __init__(self, headless: bool = False, output_file: str = "tiktok_profiles.json"):
        self.headless = headless
        self.output_file = output_file
        self.profiles_data: List[Dict] = []
        self.visited_usernames: set = set()

    async def close_popups(self, page: Page):
        """Close any popups, login prompts, or cookie banners"""
        try:
            # Common selectors for TikTok popups
            popup_selectors = [
                'button:has-text("Not now")',
                'button:has-text("Close")',
                'button:has-text("Dismiss")',
                'button[aria-label="Close"]',
                'div[role="dialog"] button',
                '.tiktok-modal-close',
            ]

            for selector in popup_selectors:
                try:
                    await page.click(selector, timeout=2000)
                    print("  ✓ Closed popup")
                    await asyncio.sleep(1)
                except:
                    pass

        except Exception as e:
            pass  # No popups to close

    async def extract_profile_data(self, page: Page) -> Optional[Dict]:
        """Extract profile data from the current profile page"""
        try:
            # Wait for profile to load
            await page.wait_for_load_state('networkidle', timeout=10000)
            await asyncio.sleep(2)

            # Extract username from URL
            current_url = page.url
            username_match = re.search(r'/@([^/?]+)', current_url)
            username = f"@{username_match.group(1)}" if username_match else None

            if not username or username in self.visited_usernames:
                return None

            print(f"\n  📱 Extracting profile: {username}")

            # Extract profile information using JavaScript
            profile_data = await page.evaluate("""
                () => {
                    // Helper function to get text content safely
                    const getText = (selector) => {
                        const el = document.querySelector(selector);
                        return el ? el.textContent.trim() : '';
                    };

                    // Helper to get attribute safely
                    const getAttr = (selector, attr) => {
                        const el = document.querySelector(selector);
                        return el ? el.getAttribute(attr) : '';
                    };

                    // Try multiple selectors for each field
                    const getTextMultiple = (selectors) => {
                        for (const selector of selectors) {
                            const text = getText(selector);
                            if (text) return text;
                        }
                        return '';
                    };

                    // Display name
                    const displayName = getTextMultiple([
                        'h1[data-e2e="user-title"]',
                        'h2[data-e2e="user-title"]',
                        'h1.user-title',
                        'span[data-e2e="user-title"]'
                    ]);

                    // Username
                    const username = getTextMultiple([
                        'h2[data-e2e="user-subtitle"]',
                        'h1[data-e2e="user-subtitle"]',
                        'span[data-e2e="user-subtitle"]',
                        '.user-subtitle'
                    ]);

                    // Bio/Description
                    const bio = getTextMultiple([
                        'h2[data-e2e="user-bio"]',
                        'div[data-e2e="user-bio"]',
                        '.user-bio'
                    ]);

                    // Follower count
                    const followerCount = getTextMultiple([
                        'strong[data-e2e="followers-count"]',
                        'div[data-e2e="followers-count"]',
                        'strong[title*="Followers"]',
                        '.follower-count'
                    ]);

                    // Following count
                    const followingCount = getTextMultiple([
                        'strong[data-e2e="following-count"]',
                        'div[data-e2e="following-count"]',
                        'strong[title*="Following"]',
                        '.following-count'
                    ]);

                    // Likes count
                    const likesCount = getTextMultiple([
                        'strong[data-e2e="likes-count"]',
                        'div[data-e2e="likes-count"]',
                        'strong[title*="Likes"]',
                        '.likes-count'
                    ]);

                    // Check for verification badge
                    const isVerified = !!document.querySelector('[data-e2e="user-verified-badge"], .verified-badge, svg[fill="url(#icon-badge-verification)"]');

                    return {
                        displayName,
                        username,
                        bio,
                        followerCount,
                        followingCount,
                        likesCount,
                        isVerified
                    };
                }
            """)

            # Extract email from bio using regex
            email = None
            if profile_data.get('bio'):
                email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', profile_data['bio'])
                if email_match:
                    email = email_match.group(0)

            # Build complete profile object
            profile = {
                'username': username,
                'display_name': profile_data.get('displayName', ''),
                'bio': profile_data.get('bio', ''),
                'email': email,
                'follower_count': profile_data.get('followerCount', ''),
                'following_count': profile_data.get('followingCount', ''),
                'likes_count': profile_data.get('likesCount', ''),
                'is_verified': profile_data.get('isVerified', False),
                'profile_url': current_url,
                'scraped_at': datetime.now().isoformat()
            }

            print(f"  ✓ {username}")
            print(f"    Name: {profile['display_name']}")
            print(f"    Followers: {profile['follower_count']}")
            if email:
                print(f"    📧 Email: {email}")

            self.visited_usernames.add(username)
            return profile

        except Exception as e:
            print(f"  ✗ Error extracting profile: {e}")
            return None

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

    async def scrape_explore(self, max_profiles: int = 50):
        """
        Navigate to TikTok explore and scrape user profiles

        Args:
            max_profiles: Maximum number of profiles to scrape
        """
        async with async_playwright() as p:
            print("="*70)
            print("TIKTOK EXPLORE SCRAPER")
            print("="*70)
            print(f"Target profiles: {max_profiles}")
            print(f"Output file: {self.output_file}")
            print("="*70 + "\n")

            # Launch browser
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = await context.new_page()

            try:
                # Navigate to TikTok explore
                print("📍 Navigating to TikTok Explore...")
                await page.goto('https://www.tiktok.com/explore', wait_until='domcontentloaded')
                await asyncio.sleep(3)

                # Close popups
                await self.close_popups(page)

                print("\n🔍 Finding user profiles...\n")

                profiles_scraped = 0
                scroll_attempts = 0
                max_scroll_attempts = 100

                while profiles_scraped < max_profiles and scroll_attempts < max_scroll_attempts:
                    # Find all user profile links on the page
                    user_links = await page.query_selector_all('a[href*="/@"]')

                    print(f"  Found {len(user_links)} user links on page")

                    # Click on each user link
                    for i, link in enumerate(user_links):
                        if profiles_scraped >= max_profiles:
                            break

                        try:
                            # Get the href before clicking (element might become stale)
                            href = await link.get_attribute('href')

                            # Extract username from href
                            username_match = re.search(r'/@([^/?]+)', href) if href else None
                            if not username_match:
                                continue

                            username = f"@{username_match.group(1)}"

                            # Skip if already visited
                            if username in self.visited_usernames:
                                continue

                            print(f"\n[{profiles_scraped + 1}/{max_profiles}] Clicking on {username}...")

                            # Click the link and wait for navigation
                            await link.click()
                            await asyncio.sleep(2)

                            # Close any popups that might appear
                            await self.close_popups(page)

                            # Extract profile data
                            profile = await self.extract_profile_data(page)

                            if profile:
                                await self.save_profile(profile)
                                profiles_scraped += 1

                            # Go back to explore page
                            await page.go_back(wait_until='domcontentloaded')
                            await asyncio.sleep(2)

                            # Close popups again after going back
                            await self.close_popups(page)

                        except Exception as e:
                            print(f"  ✗ Error clicking link: {e}")
                            # Try to go back if we're stuck
                            try:
                                await page.go_back()
                                await asyncio.sleep(1)
                            except:
                                pass

                    # Scroll down to load more content
                    print("\n  ⬇️  Scrolling to load more profiles...")
                    await page.evaluate('window.scrollBy(0, window.innerHeight * 2)')
                    await asyncio.sleep(3)

                    scroll_attempts += 1

                print("\n" + "="*70)
                print("SCRAPING COMPLETE")
                print("="*70)
                print(f"✓ Scraped {profiles_scraped} profiles")
                print(f"✓ Saved to {self.output_file}")
                print("="*70)

            except Exception as e:
                print(f"\n✗ Error during scraping: {e}")
                import traceback
                traceback.print_exc()

            finally:
                await browser.close()


async def main():
    """Main function"""
    scraper = TikTokExploreScraper(
        headless=False,  # Set to True to run in background
        output_file='tiktok_explore_profiles.json'
    )

    await scraper.scrape_explore(max_profiles=50)


if __name__ == '__main__':
    asyncio.run(main())
