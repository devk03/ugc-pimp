"""
Continuous TikTok profile analyzer using browser-use AI agent.

This script runs forever, continuously:
1. Fetching TikTok profile handles from Supabase
2. Visiting each profile with browser-use
3. Generating AI descriptions of profile content
4. Saving descriptions back to Supabase
5. Moving to next batch of profiles

Requirements:
    - OPENAI_API_KEY in .env
    - SUPABASE_URL in .env
    - SUPABASE_KEY in .env
    - browser-use library installed (requires openai<2.0.0)

Usage:
    # Analyze 5 profiles per batch (default)
    python describe_tiktok_profiles.py

    # Analyze 10 profiles per batch
    python describe_tiktok_profiles.py --batch-size 10

    # Run without saving to database (testing)
    python describe_tiktok_profiles.py --no-save

Press Ctrl+C to stop.
"""

import asyncio
import os
from typing import List, Dict, Optional
from dotenv import load_dotenv, find_dotenv
from supabase import create_client, Client
from browser_use import Agent, ChatOpenAI as BrowserUseChatOpenAI

# Search for .env in current directory and parent directories
load_dotenv(find_dotenv())


class TikTokProfileAnalyzer:
    def __init__(self):
        """Initialize Supabase client and browser-use settings"""
        # Supabase setup
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY')

        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env")

        self.supabase: Client = create_client(supabase_url, supabase_key)
        print("✓ Supabase client initialized")

        # OpenAI setup for browser-use
        openai_key = os.getenv('OPENAI_API_KEY')
        if not openai_key:
            raise ValueError("OPENAI_API_KEY must be set in .env")

        self.llm = BrowserUseChatOpenAI(model='gpt-4o-mini')
        print("✓ Browser-use LLM initialized")

    def fetch_tiktok_contacts(self, limit: int = 10) -> List[Dict]:
        """
        Fetch contacts with TikTok profiles from Supabase.

        Args:
            limit: Maximum number of contacts to fetch

        Returns:
            List of contact records with TikTok metadata
        """
        print(f"\n🔍 Fetching up to {limit} TikTok contacts from Supabase...")

        try:
            response = self.supabase.table("contact") \
                .select("id, email, firstname, description, metadata") \
                .contains("platform", ["tiktok"]) \
                .limit(limit) \
                .execute()

            contacts = response.data

            # Filter for contacts that have TikTok username in metadata
            filtered_contacts = []
            for contact in contacts:
                metadata = contact.get('metadata', {})
                if metadata and isinstance(metadata, dict):
                    tiktok_data = metadata.get('tiktok', {})
                    if tiktok_data and tiktok_data.get('username'):
                        filtered_contacts.append(contact)

            print(f"✓ Found {len(filtered_contacts)} TikTok contacts with usernames")
            return filtered_contacts

        except Exception as e:
            print(f"✗ Error fetching contacts: {e}")
            import traceback
            traceback.print_exc()
            return []

    def extract_tiktok_username(self, contact: Dict) -> Optional[str]:
        """Extract TikTok username from contact metadata"""
        try:
            metadata = contact.get('metadata', {})
            tiktok_data = metadata.get('tiktok', {})
            username = tiktok_data.get('username', '')

            # Remove @ if present
            if username.startswith('@'):
                username = username[1:]

            return username if username else None
        except:
            return None

    async def analyze_profile(self, username: str) -> Optional[str]:
        """
        Use browser-use to visit TikTok profile and generate AI description.

        Args:
            username: TikTok username (without @)

        Returns:
            AI-generated description of the profile, or None if failed
        """
        profile_url = f"https://www.tiktok.com/@{username}"

        print(f"\n{'='*70}")
        print(f"🤖 Analyzing profile: @{username}")
        print(f"{'='*70}")
        print(f"URL: {profile_url}")

        task = f"""
Visit {profile_url} and analyze this TikTok profile.

Please provide a detailed description including:
1. Content themes and topics (what kind of content do they post about?)
2. Visual style and aesthetic
3. Engagement level (visible from comments, likes if shown)
4. Profile bio summary
5. Any notable patterns or recurring elements
6. Overall impression and niche

Be specific and descriptive. Focus on what makes this creator unique.
"""

        try:
            agent = Agent(
                task=task,
                llm=self.llm,
            )

            print("🌐 Launching browser to analyze profile...")
            result = await agent.run(max_steps=20)

            # Extract description from result
            description = None
            if result:
                try:
                    description = result.final_result()
                    if description:
                        print(f"\n✓ Profile analysis complete!")
                        print(f"\nDescription length: {len(str(description))} characters")
                        return str(description)
                except Exception as e:
                    print(f"✗ Error extracting result: {e}")

            print("✗ Could not generate profile description")
            return None

        except Exception as e:
            print(f"✗ Error analyzing profile: {e}")
            import traceback
            traceback.print_exc()
            return None

    def save_description_to_supabase(self, contact_id: str, description: str) -> bool:
        """
        Save AI-generated description to contact's metadata.

        Args:
            contact_id: Supabase contact ID
            description: AI-generated profile description

        Returns:
            True if successful, False otherwise
        """
        try:
            # Fetch current metadata
            response = self.supabase.table("contact") \
                .select("metadata") \
                .eq("id", contact_id) \
                .single() \
                .execute()

            current_metadata = response.data.get('metadata', {})

            # Add AI description to metadata
            if 'tiktok' not in current_metadata:
                current_metadata['tiktok'] = {}

            current_metadata['tiktok']['ai_description'] = description

            # Update in Supabase
            self.supabase.table("contact") \
                .update({"metadata": current_metadata}) \
                .eq("id", contact_id) \
                .execute()

            print(f"✓ Saved description to Supabase for contact {contact_id}")
            return True

        except Exception as e:
            print(f"✗ Error saving to Supabase: {e}")
            return False

    async def analyze_all_profiles_continuous(self, batch_size: int = 10, save_to_db: bool = True):
        """
        Continuously fetch and analyze TikTok profiles in a loop.

        Args:
            batch_size: Number of profiles to analyze per batch
            save_to_db: Whether to save descriptions back to Supabase
        """
        print("\n" + "="*70)
        print("🚀 CONTINUOUS TIKTOK PROFILE ANALYZER")
        print("="*70)
        print(f"Batch size: {batch_size} profiles")
        print(f"Save to database: {save_to_db}")
        print("\n⚠️  Press Ctrl+C to stop\n")
        print("="*70)

        batch_count = 0
        total_analyzed = 0
        analyzed_contacts = set()  # Track which contacts we've already analyzed

        try:
            while True:
                batch_count += 1

                print(f"\n\n{'='*70}")
                print(f"📊 BATCH #{batch_count}")
                print(f"{'='*70}")

                # Fetch contacts (fetch more than batch_size to account for already-analyzed ones)
                print(f"\n🔍 Fetching up to {batch_size * 3} TikTok contacts...")
                contacts = self.fetch_tiktok_contacts(limit=batch_size * 3)

                if not contacts:
                    print("\n⚠️  No TikTok contacts found in database")
                    print("   Waiting 60 seconds before retrying...")
                    await asyncio.sleep(60)
                    continue

                # Filter out already analyzed contacts
                new_contacts = [c for c in contacts if c.get('id') not in analyzed_contacts]

                if not new_contacts:
                    print(f"\n✓ All {len(contacts)} contacts have been analyzed!")
                    print("   Waiting 60 seconds for new contacts to be added...")
                    await asyncio.sleep(60)
                    continue

                # Take only batch_size contacts
                batch_contacts = new_contacts[:batch_size]
                print(f"✓ Found {len(batch_contacts)} new contacts to analyze")

                batch_results = []

                # Analyze each profile
                for idx, contact in enumerate(batch_contacts, 1):
                    username = self.extract_tiktok_username(contact)

                    if not username:
                        print(f"\n⏭️  [{idx}/{len(batch_contacts)}] Skipping contact {contact.get('id')} - no username found")
                        analyzed_contacts.add(contact.get('id'))
                        continue

                    print(f"\n📊 [{idx}/{len(batch_contacts)}] Processing: @{username}")
                    print(f"   Contact ID: {contact.get('id')}")
                    print(f"   Email: {contact.get('email', 'N/A')}")
                    print(f"   Name: {contact.get('firstname', 'N/A')}")

                    # Analyze profile
                    description = await self.analyze_profile(username)

                    if description:
                        result = {
                            'contact_id': contact.get('id'),
                            'username': username,
                            'email': contact.get('email'),
                            'description': description
                        }
                        batch_results.append(result)

                        # Print description
                        print("\n" + "-"*70)
                        print("AI DESCRIPTION:")
                        print("-"*70)
                        print(description[:500] + "..." if len(description) > 500 else description)
                        print("-"*70)

                        # Save to database
                        if save_to_db:
                            self.save_description_to_supabase(contact.get('id'), description)

                        analyzed_contacts.add(contact.get('id'))
                        total_analyzed += 1
                    else:
                        print(f"✗ Failed to analyze @{username}")
                        analyzed_contacts.add(contact.get('id'))  # Mark as attempted

                    # Small delay between profiles
                    if idx < len(batch_contacts):
                        print("\n⏳ Waiting 5 seconds before next profile...")
                        await asyncio.sleep(5)

                # Batch summary
                print(f"\n{'='*70}")
                print(f"✅ BATCH #{batch_count} COMPLETE")
                print(f"{'='*70}")
                print(f"Batch analyzed: {len(batch_results)}/{len(batch_contacts)}")
                print(f"Total analyzed: {total_analyzed}")
                print(f"{'='*70}")

                # Wait before next batch
                wait_time = 30
                print(f"\n⏳ Waiting {wait_time} seconds before next batch...")
                await asyncio.sleep(wait_time)

        except KeyboardInterrupt:
            print(f"\n\n{'='*70}")
            print("⛔ STOPPING - User pressed Ctrl+C")
            print(f"{'='*70}")
            print(f"📊 Final Statistics:")
            print(f"   Total batches: {batch_count}")
            print(f"   Total profiles analyzed: {total_analyzed}")
            print(f"   Average per batch: {total_analyzed / batch_count if batch_count > 0 else 0:.1f}")
            print(f"{'='*70}")


async def main():
    """Run the TikTok profile analyzer"""
    import argparse

    parser = argparse.ArgumentParser(description='Continuously analyze TikTok profiles using AI')
    parser.add_argument('--batch-size', type=int, default=5, help='Number of profiles to analyze per batch (default: 5)')
    parser.add_argument('--no-save', action='store_true', help='Do not save descriptions to database')

    args = parser.parse_args()

    try:
        analyzer = TikTokProfileAnalyzer()
        await analyzer.analyze_all_profiles_continuous(
            batch_size=args.batch_size,
            save_to_db=not args.no_save
        )
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
