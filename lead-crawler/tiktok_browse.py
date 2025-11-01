"""
TikTok Lead Crawler - Find Content Creators with Emails in Bios
Browses TikTok profiles to find creators who have email addresses in their bios

Setup:
1. Get your API key from https://cloud.browser-use.com/new-api-key
2. Copy .env.example to .env and add your API key
"""
import asyncio
import os
import re
from dotenv import load_dotenv
from pydantic import BaseModel
from browser_use import Agent, Browser, ChatBrowserUse, Tools

# Load environment variables from .env file
load_dotenv()


class CreatorLead(BaseModel):
	username: str
	display_name: str
	email: str  # The email found in bio
	bio: str
	follower_count: str
	profile_url: str
	is_verified: bool


class CreatorLeadList(BaseModel):
	leads: list[CreatorLead]

async def find_creators_with_emails(num_profiles_to_check: int = 10):
	"""
	Browse TikTok and find content creators who have email addresses in their bios.

	Args:
		num_profiles_to_check: Number of profiles to check before stopping
	"""
	print(f"Starting TikTok Lead Crawler...")
	print(f"Will check up to {num_profiles_to_check} profiles for email addresses in bios\n")

	# Create a visible browser so you can watch it work
	browser = Browser(
		headless=False,  # Show the browser
	)

	# Configure tools to use structured output
	tools = Tools(output_model=CreatorLeadList)

	task = f"""
	Your goal is to find TikTok content creators who have EMAIL ADDRESSES in their bios.

	Steps:
	1. Go to https://www.tiktok.com
	2. If you encounter any popups or modals (like login prompts or cookie consent), close them
	3. Browse through the feed and check approximately {num_profiles_to_check} different creator profiles
	4. For each profile you visit:
	   - Look at the bio/description
	   - Check if there's an EMAIL ADDRESS in the bio (look for patterns like name@domain.com)
	   - If there IS an email, extract this data:
	     * username: The handle (e.g., "@username" - include the @)
	     * display_name: The display name
	     * email: The email address found in the bio
	     * bio: The full bio text
	     * follower_count: Number of followers (keep formatting like "1.2M")
	     * profile_url: The profile URL
	     * is_verified: Boolean - true if verified badge present
	   - If there is NO email in the bio, skip this profile and move to the next one
	5. Go back and check more profiles until you find at least 3-5 creators with emails, or until you've checked {num_profiles_to_check} profiles
	6. Return ONLY the profiles that have email addresses in their bios

	IMPORTANT:
	- Only return profiles that HAVE emails in their bios
	- Look for email patterns like: word@domain.com, business@gmail.com, etc.
	- You can scroll the feed or use search to find different creators
	- Focus on finding creators who are looking for business opportunities (they're more likely to have emails)
	"""

	llm = ChatBrowserUse()

	agent = Agent(
		task=task,
		llm=llm,
		browser=browser,
		tools=tools
	)

	print("Navigating to TikTok and searching for creators with emails...\n")
	history = await agent.run()

	print("\n" + "="*50)
	print("Lead Crawling Complete!")
	print("="*50)

	# Parse the structured result
	result = history.final_result()
	if result:
		leads: CreatorLeadList = CreatorLeadList.model_validate_json(result)

		print(f"\nFound {len(leads.leads)} creators with emails in their bios:\n")

		for i, lead in enumerate(leads.leads, 1):
			print(f"--- Lead #{i} ---")
			print(f"  Username:        {lead.username}")
			print(f"  Display Name:    {lead.display_name}")
			print(f"  Email:           {lead.email}")
			print(f"  Followers:       {lead.follower_count}")
			print(f"  Verified:        {'✓' if lead.is_verified else '✗'}")
			print(f"  Bio:             {lead.bio[:100]}..." if len(lead.bio) > 100 else f"  Bio:             {lead.bio}")
			print(f"  Profile URL:     {lead.profile_url}")
			print()

		return leads
	else:
		print("No leads found")
		return None

if __name__ == '__main__':
	# You can adjust the number of profiles to check
	asyncio.run(find_creators_with_emails(num_profiles_to_check=15))
