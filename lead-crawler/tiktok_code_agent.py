"""
TikTok Creator Scraper using CodeAgent
Uses browser-use CodeAgent to write JavaScript code for fast data extraction

CodeAgent writes Python code that executes JavaScript in the browser,
making it much faster than manual clicking/scrolling.

Setup:
1. Add BROWSER_USE_API_KEY to your .env file
"""
import asyncio
from dotenv import load_dotenv
from browser_use.code_use import CodeAgent
from browser_use.code_use.notebook_export import export_to_ipynb, session_to_python_script

load_dotenv()


async def scrape_tiktok_creators(num_profiles: int = 30, filter_emails: bool = True):
	"""
	Use CodeAgent to scrape TikTok creator profiles

	Args:
		num_profiles: Target number of creator profiles to collect
		filter_emails: Only collect creators with emails in bio
	"""

	if filter_emails:
		task = f"""
		Scrape TikTok creator profiles who have EMAIL ADDRESSES in their bios.

		Requirements:
		1. Go to https://www.tiktok.com
		2. Close any popups or cookie banners
		3. Write JavaScript code to:
		   - Scroll through the feed and collect video elements
		   - Extract creator usernames from videos
		   - For each creator, navigate to their profile page
		   - Extract profile data from the DOM including:
		     * username (e.g., @username)
		     * display_name
		     * bio (full bio text)
		     * follower_count
		     * is_verified (boolean)
		     * profile_url
		   - Check if bio contains an email address (patterns like: name@domain.com)
		   - Only keep creators that HAVE emails in their bio

		4. Collect approximately {num_profiles} creators WITH emails
		5. Save the results to a JSON file named 'tiktok_creators_with_emails.json'

		Output format (JSON array):
		[
		  {{
		    "username": "@creator1",
		    "display_name": "Creator Name",
		    "bio": "Full bio text here...",
		    "email": "contact@email.com",
		    "follower_count": "1.2M",
		    "is_verified": true,
		    "profile_url": "https://www.tiktok.com/@creator1"
		  }},
		  ...
		]

		Important:
		- Use JavaScript DOM manipulation for speed
		- Add delays between profile visits to avoid rate limiting (1-2 seconds)
		- Handle any login prompts by closing them
		- Focus on finding creators with emails
		- Save results incrementally to avoid losing data
		"""
	else:
		task = f"""
		Scrape {num_profiles} TikTok creator profiles.

		Requirements:
		1. Go to https://www.tiktok.com
		2. Close any popups or cookie banners
		3. Write JavaScript code to:
		   - Scroll through the feed
		   - Extract creator usernames from videos
		   - For each creator, navigate to their profile
		   - Extract profile data:
		     * username
		     * display_name
		     * bio
		     * follower_count
		     * is_verified
		     * profile_url
		   - Check for email in bio (can be null)

		4. Collect {num_profiles} creator profiles
		5. Save results to 'tiktok_creators.json'

		Output format: JSON array with creator objects
		"""

	print("="*60)
	print("TikTok Creator Scraper (CodeAgent)")
	print("="*60)
	print(f"Target: {num_profiles} profiles")
	print(f"Filter emails: {filter_emails}")
	print("="*60 + "\n")

	# Create CodeAgent
	agent = CodeAgent(
		task=task,
		max_steps=50,  # Allow enough steps for scraping
	)

	try:
		print("Starting CodeAgent...\n")
		print("The agent will write JavaScript code to extract data efficiently.\n")

		# Run the agent
		session = await agent.run()

		print("\n" + "="*60)
		print("Scraping Complete!")
		print("="*60)

		# Export session to reusable formats
		print("\nExporting session for future use...")

		# Export to Python script
		python_script = session_to_python_script(agent)
		script_filename = "tiktok_scraper_generated.py"
		with open(script_filename, "w") as f:
			f.write(python_script)
		print(f"✓ Saved Python script: {script_filename}")

		# Export to Jupyter notebook
		notebook_filename = "tiktok_scraper_generated.ipynb"
		export_to_ipynb(agent, notebook_filename)
		print(f"✓ Saved Jupyter notebook: {notebook_filename}")

		print("\n" + "="*60)
		print("Next Steps:")
		print("="*60)
		print(f"1. Check '{script_filename}' to rerun the scraper")
		print(f"2. Open '{notebook_filename}' in Jupyter to iterate on the code")
		print("3. Check the generated JSON file for scraped data")
		print("="*60)

		return session

	except Exception as e:
		print(f"\n\nError during scraping: {e}")
		import traceback
		traceback.print_exc()
		return None

	finally:
		await agent.close()


async def main():
	"""Main function"""

	# Configuration
	NUM_PROFILES = 30  # How many profiles to scrape
	FILTER_EMAILS = True  # Only get creators with emails

	await scrape_tiktok_creators(
		num_profiles=NUM_PROFILES,
		filter_emails=FILTER_EMAILS
	)


if __name__ == '__main__':
	asyncio.run(main())
