"""
TikTok User Search using Apify API
Searches for TikTok users based on keywords and retrieves detailed profile data

Setup:
1. Install the Apify client: pip install apify-client
2. Get your API token from https://console.apify.com/account/integrations
3. Add APIFY_API_TOKEN to your .env file
"""

import os
from dotenv import load_dotenv
from apify_client import ApifyClient
import json
from typing import List, Dict, Optional

load_dotenv()


class TikTokUserSearcher:
    """Search for TikTok users using Apify API"""

    def __init__(self, api_token: Optional[str] = None):
        """
        Initialize the TikTok User Searcher

        Args:
            api_token: Apify API token (defaults to APIFY_API_TOKEN env var)
        """
        self.api_token = api_token or os.getenv('APIFY_API_TOKEN')
        if not self.api_token:
            raise ValueError("APIFY_API_TOKEN not found in environment variables")

        self.client = ApifyClient(self.api_token)

    def search_users(
        self,
        search_queries: List[str],
        max_results_per_query: int = 100,
        actor_id: str = "clockworks/tiktok-user-search-scraper"
    ) -> List[Dict]:
        """
        Search for TikTok users based on search queries

        Args:
            search_queries: List of search terms (e.g., ["fitness coach", "entrepreneur"])
            max_results_per_query: Maximum number of users to retrieve per search
            actor_id: Apify actor to use for scraping
                     Options:
                     - "clockworks/tiktok-user-search-scraper" (recommended)
                     - "powerai/tiktok-user-search-scraper"

        Returns:
            List of user profile dictionaries
        """
        all_users = []

        for query in search_queries:
            print(f"\n{'='*60}")
            print(f"Searching for: '{query}'")
            print(f"{'='*60}")

            try:
                # Configure the actor input
                run_input = {
                    "search": query,
                    "resultsPerPage": max_results_per_query,
                }

                # Run the actor and wait for it to finish
                print(f"Starting Apify actor: {actor_id}")
                run = self.client.actor(actor_id).call(run_input=run_input)

                # Fetch results from the default dataset
                print("Retrieving results...")
                dataset_items = self.client.dataset(run["defaultDatasetId"]).list_items()

                users = dataset_items.items
                print(f"✓ Found {len(users)} users for '{query}'")

                # Add search query metadata to each user
                for user in users:
                    user['search_query'] = query

                all_users.extend(users)

            except Exception as e:
                print(f"✗ Error searching for '{query}': {e}")
                continue

        print(f"\n{'='*60}")
        print(f"Total users found: {len(all_users)}")
        print(f"{'='*60}")

        return all_users

    def save_results(self, users: List[Dict], filename: str = "tiktok_users.json"):
        """
        Save user data to a JSON file

        Args:
            users: List of user profile dictionaries
            filename: Output filename
        """
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(users, f, indent=2, ensure_ascii=False)
        print(f"\n✓ Saved {len(users)} users to {filename}")

    def print_summary(self, users: List[Dict]):
        """Print a summary of the found users"""
        print(f"\n{'='*60}")
        print("User Summary")
        print(f"{'='*60}\n")

        for i, user in enumerate(users[:10], 1):  # Show first 10
            username = user.get('uniqueId') or user.get('username', 'N/A')
            nickname = user.get('nickname') or user.get('display_name', 'N/A')
            followers = user.get('followerCount') or user.get('stats', {}).get('followerCount', 0)
            verified = user.get('verified', False)

            print(f"{i}. @{username}")
            print(f"   Name: {nickname}")
            print(f"   Followers: {followers:,}")
            print(f"   Verified: {'✓' if verified else '✗'}")
            print()

        if len(users) > 10:
            print(f"... and {len(users) - 10} more users\n")


def main():
    """Main function to demonstrate usage"""

    # Configuration
    SEARCH_QUERIES = [
        "fitness coach",
        "entrepreneur",
        "content creator"
    ]
    MAX_RESULTS_PER_QUERY = 35  # Get ~35 per search to reach 100+ total

    print("="*60)
    print("TikTok User Search via Apify API")
    print("="*60)
    print(f"Search queries: {', '.join(SEARCH_QUERIES)}")
    print(f"Max results per query: {MAX_RESULTS_PER_QUERY}")
    print("="*60)

    # Initialize searcher
    try:
        searcher = TikTokUserSearcher()
    except ValueError as e:
        print(f"\n✗ Error: {e}")
        print("Please add your APIFY_API_TOKEN to the .env file")
        print("Get your token from: https://console.apify.com/account/integrations")
        return

    # Search for users
    users = searcher.search_users(
        search_queries=SEARCH_QUERIES,
        max_results_per_query=MAX_RESULTS_PER_QUERY
    )

    if users:
        # Print summary
        searcher.print_summary(users)

        # Save results
        searcher.save_results(users, "tiktok_users_apify.json")

        print("\n" + "="*60)
        print("Complete!")
        print("="*60)
        print(f"✓ Retrieved {len(users)} user profiles")
        print("✓ Data saved to: tiktok_users_apify.json")
        print("="*60)
    else:
        print("\n✗ No users found")


if __name__ == '__main__':
    main()
