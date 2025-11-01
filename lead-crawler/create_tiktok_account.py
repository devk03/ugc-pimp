"""
Create a new TikTok account using browser-use and Agentmail

This script:
1. Creates a temporary email address using Agentmail
2. Uses browser-use AI agent to navigate TikTok signup flow
3. Handles email verification if needed

Setup:
1. Add BROWSER_USE_API_KEY and AGENTMAIL_API_KEY to your .env file
"""
import asyncio
import os
from dotenv import load_dotenv
from agentmail import AsyncAgentMail
from browser_use import Agent, Browser, ChatBrowserUse, Tools

# Load environment variables
load_dotenv()


class TikTokAccountCreator:
	def __init__(self):
		self.browser_api_key = os.getenv('BROWSER_USE_API_KEY')
		self.agentmail_api_key = os.getenv('AGENTMAIL_API_KEY')

		if not self.browser_api_key:
			raise ValueError("BROWSER_USE_API_KEY not found in environment")
		if not self.agentmail_api_key:
			raise ValueError("AGENTMAIL_API_KEY not found in environment")

		self.email_client = AsyncAgentMail(api_key=self.agentmail_api_key)
		self.email_address = None
		self.inbox = None

	async def create_email(self, username: str = None):
		"""Create a new temporary email address"""
		print("Creating temporary email address...")

		self.inbox = await self.email_client.inboxes.create(username=username)
		self.email_address = self.inbox.inbox_id

		print(f"Email created: {self.email_address}")
		return self.email_address

	async def get_verification_code(self, timeout: int = 60):
		"""
		Poll for verification email and extract code

		Args:
			timeout: Maximum time to wait for email (seconds)
		"""
		print(f"Waiting for verification email (timeout: {timeout}s)...")

		import time
		start_time = time.time()

		while time.time() - start_time < timeout:
			# Get unread messages
			messages = await self.email_client.inboxes.messages.list(
				inbox_id=self.inbox.inbox_id,
				labels=['unread']
			)

			if messages.messages:
				# Get the first unread message
				msg = await self.email_client.inboxes.messages.get(
					inbox_id=self.inbox.inbox_id,
					message_id=messages.messages[0].message_id
				)

				print(f"Received email from: {msg.from_}")
				print(f"Subject: {msg.subject}")

				# Extract text content
				email_body = msg.text or msg.html or ""

				# Mark as read
				await self.email_client.inboxes.messages.update(
					inbox_id=self.inbox.inbox_id,
					message_id=msg.message_id,
					remove_labels=['unread']
				)

				return email_body

			# Wait 5 seconds before checking again
			await asyncio.sleep(5)

		raise TimeoutError(f"No verification email received within {timeout} seconds")

	async def create_tiktok_account(self, username: str, password: str, email_username: str = None):
		"""
		Create a TikTok account using browser automation

		Args:
			username: Desired TikTok username
			password: Account password
			email_username: Optional custom email username (defaults to random)
		"""
		# Create email first
		await self.create_email(username=email_username)

		# Create browser with stealth settings to avoid bot detection
		browser = Browser(
			headless=False,
			disable_security=False,  # Keep security enabled to look more real
		)

		# Set up custom tools with email access
		tools = Tools()

		@tools.action('Get the email address for TikTok signup')
		async def get_email_address() -> str:
			"""Returns the temporary email address to use for signup"""
			return self.email_address

		@tools.action('Get verification code from email. Call this after TikTok sends verification email.')
		async def get_verification_code() -> str:
			"""
			Waits for and retrieves the verification code/link from email.
			Returns the full email content.
			"""
			email_content = await self.get_verification_code(timeout=90)
			return f"Email received. Content:\n{email_content}"

		# Create the task for the agent
		task = f"""
		Create a new TikTok account with these details:
		- Username: {username}
		- Password: {password}
		- Email: Use the get_email_address action to get the email

		Steps:
		1. Go to https://www.tiktok.com/signup
		2. WAIT 3-5 seconds for the page to fully load (act more human-like)
		3. Close any cookie banners or popups if they appear
		4. Choose "Sign up with email or username" option
		5. WAIT 2 seconds after clicking
		6. Use get_email_address action to get the email address
		7. Enter the email address in the email field SLOWLY (type naturally, not instantly)
		8. WAIT 2 seconds
		9. Enter username: {username} SLOWLY in the username field
		10. WAIT 2 seconds
		11. Enter password: {password} SLOWLY in the password field
		12. WAIT 2 seconds
		13. Solve any CAPTCHA if it appears (take your time with this)
		14. Click the signup/next button
		15. WAIT 5-10 seconds for TikTok to process
		16. If asked for email verification:
		    - Use get_verification_code action to retrieve the code from email
		    - Enter the verification code SLOWLY
		    - WAIT 3 seconds between entering code and submitting
		17. If successful, you should be logged in or see a success message
		18. Confirm the account was created successfully

		CRITICAL - ACT HUMAN:
		- ALWAYS add 2-5 second pauses between actions
		- Type slowly and naturally (not instant paste)
		- If you get errors or blocks, STOP and report (don't retry aggressively)
		- Wait for elements to appear before interacting
		- Close popups gently, don't rush
		- If you hit maximum retries or errors, explain what happened
		"""

		llm = ChatBrowserUse()

		agent = Agent(
			task=task,
			llm=llm,
			browser=browser,
			tools=tools,
			max_actions_per_step=10,  # Limit actions to prevent aggressive retries
		)

		print("\n" + "="*50)
		print("Starting TikTok Account Creation")
		print("="*50)
		print(f"Username: {username}")
		print(f"Email: {self.email_address}")
		print(f"Password: {password}")
		print("="*50 + "\n")

		try:
			result = await agent.run()

			print("\n" + "="*50)
			print("TikTok Account Creation Complete!")
			print("="*50)
			print(f"Username: {username}")
			print(f"Email: {self.email_address}")
			print(f"Password: {password}")
			print("="*50)

			return {
				'username': username,
				'email': self.email_address,
				'password': password,
				'success': True
			}

		except Exception as e:
			print(f"\n\nError creating account: {e}")
			return {
				'username': username,
				'email': self.email_address,
				'password': password,
				'success': False,
				'error': str(e)
			}


async def main():
	"""Main function to create a TikTok account"""

	# Account details
	TIKTOK_USERNAME = "testbot12345"  # Change this
	TIKTOK_PASSWORD = "SecurePassword123!"  # Change this
	EMAIL_USERNAME = "ugc-test1"  # Optional: custom email username

	creator = TikTokAccountCreator()

	result = await creator.create_tiktok_account(
		username=TIKTOK_USERNAME,
		password=TIKTOK_PASSWORD,
		email_username=EMAIL_USERNAME
	)

	print("\n\nFinal Result:")
	print(result)

	# Optionally save credentials to a file
	if result['success']:
		with open('tiktok_accounts.txt', 'a') as f:
			f.write(f"\n{result['username']}:{result['password']}:{result['email']}\n")
		print("\nCredentials saved to tiktok_accounts.txt")


if __name__ == '__main__':
	asyncio.run(main())
