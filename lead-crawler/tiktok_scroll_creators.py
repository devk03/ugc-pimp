"""
TikTok Creator Crawler - Scroll and Extract Creator Info
Uses browser-use to scroll TikTok feed and extract creator profiles with emails

This script:
1. Opens TikTok without login
2. Scrolls through the feed
3. Clicks on creator profiles
4. Extracts bio and contact information
5. Saves creators with emails to a file
"""
import asyncio
import json
from datetime import datetime
from dotenv import load_dotenv
from pydantic import BaseModel
from browser_use import Agent, Browser, ChatBrowserUse, Tools

load_dotenv()


class CreatorProfile(BaseModel):
	username: str
	display_name: str
	bio: str
	email: str | None = None
	follower_count: str
	profile_url: str
	is_verified: bool


class CreatorList(BaseModel):
	creators: list[CreatorProfile]


async def scroll_and_find_creators(num_profiles: int = 20, filter_emails: bool = True):
	"""
	Scroll TikTok and extract creator profiles

	Args:
		num_profiles: Number of creator profiles to check
		filter_emails: Only return creators with emails in bio
	"""
	print("="*60)
	print("TikTok Creator Crawler")
	print("="*60)
	print(f"Target profiles: {num_profiles}")
	print(f"Filter emails only: {filter_emails}")
	print("="*60 + "\n")

	# Create visible browser
	browser = Browser(headless=False)

	# Configure tools with structured output
	tools = Tools(output_model=CreatorList)

	# Create the task
	if filter_emails:
		task = f"""
		Go to TikTok and find creators who have EMAIL ADDRESSES in their bios.

		Steps:
		1. Go to https://www.tiktok.com
		2. Wait 3-5 seconds for the page to load
		3. Close any popups, cookie banners, or login prompts (click "Not now" or close buttons)
		4. Scroll through the TikTok feed slowly
		5. For each video you see, click on the creator's profile/username to view their full profile
		6. On the profile page, look at their bio for an EMAIL ADDRESS
		7. If there IS an email, extract these details:
		   - username: The @username handle
		   - display_name: Their display name
		   - bio: Full bio text
		   - email: The email address found in bio
		   - follower_count: Number of followers (e.g., "1.2M", "50K")
		   - profile_url: The current profile URL
		   - is_verified: Boolean - true if they have a verification badge
		8. If there is NO email in bio, go back and check the next creator
		9. Continue until you've found at least {num_profiles} creators WITH emails, or checked {num_profiles * 3} profiles total
		10. Return ONLY creators that have emails in their bios

		IMPORTANT:
		- Scroll slowly and naturally (2-3 seconds between scrolls)
		- Wait for profiles to load fully before extracting info
		- Look for email patterns like: word@domain.com, contact@email.com, etc.
		- Don't rush - take time between clicking profiles
		- If you get stuck or blocked, explain what happened
		- Close any "Log in" or "Sign up" popups that appear
		"""
	else:
		task = f"""
		Go to TikTok and extract information from {num_profiles} creator profiles.

		Steps:
		1. Go to https://www.tiktok.com
		2. Wait 3-5 seconds for the page to load
		3. Close any popups, cookie banners, or login prompts
		4. Scroll through the TikTok feed slowly
		5. For each video, click on the creator's profile/username
		6. Extract these details from their profile:
		   - username: The @username handle
		   - display_name: Their display name
		   - bio: Full bio text
		   - email: Email address if found in bio (can be null)
		   - follower_count: Number of followers
		   - profile_url: The current profile URL
		   - is_verified: Boolean - verification status
		7. Go back and continue to the next creator
		8. Repeat until you've checked {num_profiles} different creator profiles
		9. Return all {num_profiles} creators

		IMPORTANT:
		- Scroll slowly (2-3 seconds between actions)
		- Wait for profiles to load fully
		- Check for emails in bios (can be null if not found)
		- Close any login prompts
		"""

	llm = ChatBrowserUse()

	agent = Agent(
		task=task,
		llm=llm,
		browser=browser,
		tools=tools,
		max_actions_per_step=10,
	)

	print("Starting TikTok crawler...\n")

	try:
		history = await agent.run()

		# Parse results
		result = history.final_result()
		if result:
			creators_data: CreatorList = CreatorList.model_validate_json(result)

			print("\n" + "="*60)
			print(f"Found {len(creators_data.creators)} creators!")
			print("="*60)

			# Display results
			for i, creator in enumerate(creators_data.creators, 1):
				print(f"\n{i}. @{creator.username} - {creator.display_name}")
				print(f"   Followers: {creator.follower_count}")
				print(f"   Verified: {'✓' if creator.is_verified else '✗'}")
				if creator.email:
					print(f"   ✉️  Email: {creator.email}")
				print(f"   Bio: {creator.bio[:80]}..." if len(creator.bio) > 80 else f"   Bio: {creator.bio}")
				print(f"   URL: {creator.profile_url}")

			# Save results
			timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
			filename = f"tiktok_creators_{timestamp}.json"

			with open(filename, 'w', encoding='utf-8') as f:
				json.dump(
					[creator.model_dump() for creator in creators_data.creators],
					f,
					indent=2,
					ensure_ascii=False
				)

			print(f"\n✓ Saved {len(creators_data.creators)} creators to {filename}")

			return creators_data.creators

		else:
			print("No results returned")
			return []

	except Exception as e:
		print(f"\n\nError during crawling: {e}")
		import traceback
		traceback.print_exc()
		return []


async def main():
	"""Main function"""

	# Configuration
	NUM_PROFILES = 15  # Number of profiles to check
	FILTER_EMAILS = True  # Only get creators with emails

	creators = await scroll_and_find_creators(
		num_profiles=NUM_PROFILES,
		filter_emails=FILTER_EMAILS
	)

	print("\n" + "="*60)
	print("Summary")
	print("="*60)
	print(f"Total creators found: {len(creators)}")
	if FILTER_EMAILS:
		print(f"Creators with emails: {len([c for c in creators if c.email])}")
	print("="*60)


if __name__ == '__main__':
	asyncio.run(main())
