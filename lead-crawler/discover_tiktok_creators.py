"""
Discover TikTok creators and their bios using the TikTok API

This script:
1. Searches TikTok for users based on keywords
2. Extracts user profile information and bios
3. Optionally filters for creators with emails in their bios
4. Saves results to a JSON file

Setup:
1. Install TikTokApi: pip install TikTokApi
2. Install playwright: python -m playwright install
"""
import asyncio
import json
import re
import os
from datetime import datetime
from TikTokApi import TikTokApi


def extract_email_from_bio(bio: str) -> str | None:
	"""
	Extract email address from bio text

	Args:
		bio: Bio text to search

	Returns:
		Email address if found, None otherwise
	"""
	if not bio:
		return None

	# Email regex pattern
	email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
	match = re.search(email_pattern, bio)

	return match.group(0) if match else None


async def get_user_info(api: TikTokApi, username: str) -> dict | None:
	"""
	Get detailed user information

	Args:
		api: TikTokApi instance
		username: TikTok username

	Returns:
		User information dict or None if error
	"""
	try:
		user = api.user(username=username)
		user_data = await user.info()

		if not user_data or 'userInfo' not in user_data:
			return None

		user_info = user_data['userInfo']['user']
		stats = user_data['userInfo']['stats']

		return {
			'username': user_info.get('uniqueId', ''),
			'display_name': user_info.get('nickname', ''),
			'bio': user_info.get('signature', ''),
			'followers': stats.get('followerCount', 0),
			'following': stats.get('followingCount', 0),
			'likes': stats.get('heart', 0),
			'videos': stats.get('videoCount', 0),
			'verified': user_info.get('verified', False),
			'profile_url': f"https://www.tiktok.com/@{user_info.get('uniqueId', '')}",
		}

	except Exception as e:
		print(f"Error fetching user {username}: {e}")
		return None


async def discover_creators_from_trending(api: TikTokApi, count: int = 50, filter_emails: bool = False) -> list[dict]:
	"""
	Discover creators from trending videos

	Args:
		api: TikTokApi instance
		count: Number of trending videos to check
		filter_emails: If True, only return creators with emails in bio

	Returns:
		List of creator information dicts
	"""
	creators = {}
	processed_usernames = set()

	print(f"Fetching {count} trending videos...")

	try:
		async for video in api.trending.videos(count=count):
			video_data = video.as_dict

			# Extract author username
			author = video_data.get('author', {})
			username = author.get('uniqueId', '')

			if not username or username in processed_usernames:
				continue

			processed_usernames.add(username)
			print(f"Processing user: @{username}")

			# Get full user info
			user_info = await get_user_info(api, username)

			if user_info:
				# Check for email if filtering
				email = extract_email_from_bio(user_info['bio'])
				user_info['email'] = email

				if filter_emails:
					if email:
						creators[username] = user_info
						print(f"  ✓ Found email: {email}")
					else:
						print(f"  ✗ No email in bio")
				else:
					creators[username] = user_info

			# Small delay to avoid rate limiting
			await asyncio.sleep(0.5)

	except Exception as e:
		print(f"Error fetching trending videos: {e}")

	return list(creators.values())


async def search_creators_by_keyword(api: TikTokApi, keyword: str, count: int = 30, filter_emails: bool = False) -> list[dict]:
	"""
	Search for creators by keyword

	Args:
		api: TikTokApi instance
		keyword: Search keyword
		count: Number of users to fetch
		filter_emails: If True, only return creators with emails in bio

	Returns:
		List of creator information dicts
	"""
	creators = {}
	processed_usernames = set()

	print(f"Searching for '{keyword}'...")

	try:
		# Search for users
		async for user in api.search.users(keyword, count=count):
			user_data = user.as_dict

			username = user_data.get('uniqueId', '')

			if not username or username in processed_usernames:
				continue

			processed_usernames.add(username)
			print(f"Processing user: @{username}")

			# Get full user info
			user_info = await get_user_info(api, username)

			if user_info:
				# Check for email if filtering
				email = extract_email_from_bio(user_info['bio'])
				user_info['email'] = email

				if filter_emails:
					if email:
						creators[username] = user_info
						print(f"  ✓ Found email: {email}")
					else:
						print(f"  ✗ No email in bio")
				else:
					creators[username] = user_info

			# Small delay to avoid rate limiting
			await asyncio.sleep(0.5)

	except Exception as e:
		print(f"Error searching for '{keyword}': {e}")

	return list(creators.values())


async def discover_creators_from_hashtag(api: TikTokApi, hashtag: str, count: int = 50, filter_emails: bool = False) -> list[dict]:
	"""
	Discover creators from a hashtag

	Args:
		api: TikTokApi instance
		hashtag: Hashtag to search (without #)
		count: Number of videos to check
		filter_emails: If True, only return creators with emails in bio

	Returns:
		List of creator information dicts
	"""
	creators = {}
	processed_usernames = set()

	print(f"Fetching videos from #{hashtag}...")

	try:
		tag = api.hashtag(name=hashtag)
		async for video in tag.videos(count=count):
			video_data = video.as_dict

			# Extract author username
			author = video_data.get('author', {})
			username = author.get('uniqueId', '')

			if not username or username in processed_usernames:
				continue

			processed_usernames.add(username)
			print(f"Processing user: @{username}")

			# Get full user info
			user_info = await get_user_info(api, username)

			if user_info:
				# Check for email if filtering
				email = extract_email_from_bio(user_info['bio'])
				user_info['email'] = email

				if filter_emails:
					if email:
						creators[username] = user_info
						print(f"  ✓ Found email: {email}")
					else:
						print(f"  ✗ No email in bio")
				else:
					creators[username] = user_info

			# Small delay to avoid rate limiting
			await asyncio.sleep(0.5)

	except Exception as e:
		print(f"Error fetching hashtag #{hashtag}: {e}")

	return list(creators.values())


def save_results(creators: list[dict], filename: str = None):
	"""
	Save creator results to JSON file

	Args:
		creators: List of creator dicts
		filename: Output filename (defaults to timestamped file)
	"""
	if not filename:
		timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
		filename = f"tiktok_creators_{timestamp}.json"

	with open(filename, 'w', encoding='utf-8') as f:
		json.dump(creators, f, indent=2, ensure_ascii=False)

	print(f"\nSaved {len(creators)} creators to {filename}")


async def main():
	"""Main function"""

	# Configuration
	SEARCH_METHOD = "trending"  # Options: "trending", "keyword", "hashtag"
	SEARCH_KEYWORD = "ugc creator"  # For keyword search
	SEARCH_HASHTAG = "ugccreator"  # For hashtag search (without #)
	COUNT = 50  # Number of users/videos to check
	FILTER_EMAILS = True  # Only save creators with emails in bio

	print("="*60)
	print("TikTok Creator Discovery Tool")
	print("="*60)
	print(f"Method: {SEARCH_METHOD}")
	if SEARCH_METHOD == "keyword":
		print(f"Keyword: {SEARCH_KEYWORD}")
	elif SEARCH_METHOD == "hashtag":
		print(f"Hashtag: #{SEARCH_HASHTAG}")
	print(f"Filter emails only: {FILTER_EMAILS}")
	print("="*60 + "\n")

	# Get ms_token from environment (optional but helps avoid rate limits)
	ms_token = os.getenv("TIKTOK_MS_TOKEN", None)

	async with TikTokApi() as api:
		# Create sessions
		await api.create_sessions(
			ms_tokens=[ms_token] if ms_token else None,
			num_sessions=1,
			sleep_after=3
		)

		# Discover creators based on method
		if SEARCH_METHOD == "trending":
			creators = await discover_creators_from_trending(api, count=COUNT, filter_emails=FILTER_EMAILS)
		elif SEARCH_METHOD == "keyword":
			creators = await search_creators_by_keyword(api, keyword=SEARCH_KEYWORD, count=COUNT, filter_emails=FILTER_EMAILS)
		elif SEARCH_METHOD == "hashtag":
			creators = await discover_creators_from_hashtag(api, hashtag=SEARCH_HASHTAG, count=COUNT, filter_emails=FILTER_EMAILS)
		else:
			print(f"Unknown search method: {SEARCH_METHOD}")
			return

		# Display results
		print("\n" + "="*60)
		print(f"Found {len(creators)} creators")
		print("="*60)

		for i, creator in enumerate(creators, 1):
			print(f"\n{i}. @{creator['username']} - {creator['display_name']}")
			print(f"   Followers: {creator['followers']:,} | Videos: {creator['videos']}")
			print(f"   Bio: {creator['bio'][:100]}..." if len(creator['bio']) > 100 else f"   Bio: {creator['bio']}")
			if creator.get('email'):
				print(f"   ✉️  Email: {creator['email']}")

		# Save results
		save_results(creators)


if __name__ == '__main__':
	asyncio.run(main())
