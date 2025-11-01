"""
Create a new Agentmail inbox/email address

Setup:
1. Get your API key from https://agentmail.to
2. Add AGENTMAIL_API_KEY to your .env file
"""
import asyncio
import os
from dotenv import load_dotenv
from agentmail import AsyncAgentMail

# Load environment variables
load_dotenv()


async def create_email(username: str = None, display_name: str = None):
	"""
	Create a new temporary email address using Agentmail

	Args:
		username: Custom username for the email (e.g., "myname" -> myname@agentmail.to)
		             If not provided, a random username will be generated
		display_name: Display name for the inbox
	"""

	# Get API key from environment
	api_key = os.getenv('AGENTMAIL_API_KEY')

	if not api_key:
		print("Error: AGENTMAIL_API_KEY not found in environment variables")
		print("Please add it to your .env file")
		return None

	# Initialize the client
	client = AsyncAgentMail(api_key=api_key)

	if username:
		print(f"Creating email inbox: {username}@agentmail.to...")
	else:
		print("Creating new email inbox with random username...")

	try:
		# Create a new inbox with optional custom username
		inbox = await client.inboxes.create(
			username=username,
			display_name=display_name
		)

		print("\n" + "="*50)
		print("Email Created Successfully!")
		print("="*50)
		print(f"\nEmail Address: {inbox.inbox_id}")
		print(f"Created At: {inbox.created_at}")
		if display_name:
			print(f"Display Name: {display_name}")
		print("\nYou can now use this email address for signups!")
		print("="*50)

		return inbox

	except Exception as e:
		print(f"\nError creating email: {e}")
		return None


async def create_email_and_wait_for_message(username: str = None, display_name: str = None, poll_interval: int = 5):
	"""
	Create a new email and wait for messages by polling

	Args:
		username: Custom username for the email
		display_name: Display name for the inbox
		poll_interval: How often to check for new messages (in seconds)
	"""

	api_key = os.getenv('AGENTMAIL_API_KEY')

	if not api_key:
		print("Error: AGENTMAIL_API_KEY not found in environment variables")
		return None

	client = AsyncAgentMail(api_key=api_key)

	if username:
		print(f"Creating email inbox: {username}@agentmail.to...")
	else:
		print("Creating new email inbox with random username...")

	inbox = await client.inboxes.create(
		username=username,
		display_name=display_name
	)

	print("\n" + "="*50)
	print("Email Created Successfully!")
	print("="*50)
	print(f"\nEmail Address: {inbox.inbox_id}")
	print(f"\nPolling for incoming messages every {poll_interval} seconds...")
	print("(Press Ctrl+C to stop)\n")

	seen_message_ids = set()

	try:
		while True:
			# Get unread messages
			messages = await client.inboxes.messages.list(
				inbox_id=inbox.inbox_id,
				labels=['unread']
			)

			# Check for new messages we haven't seen yet
			for message_summary in messages.messages:
				if message_summary.message_id not in seen_message_ids:
					# Get full message details
					msg = await client.inboxes.messages.get(
						inbox_id=inbox.inbox_id,
						message_id=message_summary.message_id
					)

					print("\n" + "="*50)
					print("New Email Received!")
					print("="*50)
					print(f"From: {msg.from_}")
					print(f"Subject: {msg.subject}")
					print(f"Timestamp: {msg.timestamp}")
					print(f"\nBody Preview:")
					print(msg.text[:200] if msg.text else (msg.html[:200] if msg.html else "No content"))
					print("="*50 + "\n")

					# Mark as seen and read
					seen_message_ids.add(message_summary.message_id)
					await client.inboxes.messages.update(
						inbox_id=inbox.inbox_id,
						message_id=message_summary.message_id,
						remove_labels=['unread']
					)

			# Wait before polling again
			await asyncio.sleep(poll_interval)

	except KeyboardInterrupt:
		print("\n\nStopped listening for messages.")
	except Exception as e:
		print(f"\nError: {e}")


if __name__ == '__main__':
	# Example 1: Create email with random username
	# asyncio.run(create_email("test-username"))

	# Example 2: Create email with custom username
	# asyncio.run(create_email(username="mybot123", display_name="My Bot"))

	# Example 3: Create email and listen for messages
	asyncio.run(create_email_and_wait_for_message(username="tiktok-bot"))
