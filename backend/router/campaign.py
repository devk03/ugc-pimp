from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from agents.negotiate_agent import run_conversation
from agentmail import AgentMail
from supabase import create_client, Client
import uuid
import os
import openai
import json
import logging
from prompts import (
    INITIAL_OUTREACH_SYSTEM_PROMPT,
    get_initial_outreach_user_prompt,
    NEGOTIATION_SYSTEM_PROMPT,
    get_negotiation_context_prompt
)
from crawler import run_campaign_scraper_sync

logger = logging.getLogger(__name__)

NEGOTIATE_INBOX_ID = "negotiations@agentmail.to"

agentmail_api_key = os.getenv("AGENTMAIL_API_KEY")
agentmail_client = AgentMail(api_key=agentmail_api_key)

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
supabase_client: Client = create_client(supabase_url, supabase_key)

router = APIRouter(
    prefix="/campaign",
    tags=["campaign"]
)

class InitiateCampaignRequest(BaseModel):
    campaign_id: uuid.UUID
    brand_id: uuid.UUID
    brand_metadata: dict
    product_name: str
    product_url: str
    campaign_description: str

class InitiateCampaignResponse(BaseModel):
    status: str

class WebhookResponse(BaseModel):
    status: str

class Message(BaseModel):
    # Required fields based on actual AgentMail webhook
    from_: str = Field(alias="from")  # Note: It's a string, not a list!
    organization_id: str
    inbox_id: str
    thread_id: str
    message_id: str
    labels: list[str]
    timestamp: str
    to: list[str]
    subject: str
    preview: str
    text: str
    created_at: str
    updated_at: str

    # Optional fields
    html: Optional[str] = None
    in_reply_to: Optional[str] = None
    references: Optional[list[str]] = None
    reply_to: Optional[list[str]] = None
    cc: Optional[list[str]] = None
    bcc: Optional[list[str]] = None

    # Extra fields from AgentMail
    pod_id: Optional[str] = None
    size: Optional[int] = None
    smtp_id: Optional[str] = None

class WebhookPayload(BaseModel):
    event_type: str
    event_id: str
    message: Message
    type: Optional[str] = None
    body_included: Optional[bool] = None

def get_contacts_list(limit: int = 10) -> list[dict]:
    """
    Fetch the most recent contacts with emails from Supabase.

    Args:
        limit: Maximum number of contacts to fetch (default: 10)

    Returns:
        List of contact dictionaries with 'uuid', 'email', and 'firstname' fields
    """
    logger.info(f"Fetching up to {limit} contacts from Supabase")

    try:
        response = supabase_client.table("contact") \
            .select("id, email, firstname, metadata") \
            .not_("email", "is", "null") \
            .order("created_at", desc=True) \
            .limit(limit) \
            .execute()

        contacts = []
        if response.data:
            for contact in response.data:
                if contact.get("email"):
                    contacts.append({
                        "uuid": str(contact["id"]),
                        "email": contact["email"],
                        "firstname": contact.get("firstname", ""),
                        "metadata": contact.get("metadata", {})
                    })

        logger.info(f"Retrieved {len(contacts)} contacts from Supabase")

        if len(contacts) == 0:
            logger.warning("No contacts found in database. Campaign cannot proceed without contacts.")

        return contacts

    except Exception as e:
        logger.error(f"Error fetching contacts from Supabase: {str(e)}", exc_info=True)
        return []

def get_target_price(contact_id: str) -> float:
    """
    Calculate target price based on contact's expected views from recent post history.
    TODO: Implement actual logic to fetch contact's post history and calculate price based on:
    - Average views per post
    - Engagement rate
    - Follower count
    - Platform (Instagram, TikTok, YouTube, etc.)

    For now, returns a placeholder price between $50-$500.
    """
    logger.info(f"Calculating target price for contact: {contact_id}")

    try:
        # TODO: Fetch actual contact data and post history from Supabase
        # response = supabase_client.table("contact").select("*").eq("id", contact_id).execute()
        # contact_data = response.data[0]
        #
        # # Fetch recent posts and calculate average views
        # posts_response = supabase_client.table("post_history").select("views").eq("contact_id", contact_id).limit(10).execute()
        # avg_views = sum([post["views"] for post in posts_response.data]) / len(posts_response.data)
        #
        # # Price formula: $0.10 per 1000 views (CPM model)
        # target_price = (avg_views / 1000) * 0.10

        # Placeholder: Return a random price based on contact_id hash
        import hashlib
        hash_val = int(hashlib.md5(contact_id.encode()).hexdigest(), 16)
        target_price = 50 + (hash_val % 450)  # Range: $50-$500

        logger.info(f"Target price for contact {contact_id}: ${target_price:.2f}")
        return float(target_price)

    except Exception as e:
        logger.error(f"Error calculating target price for contact {contact_id}: {str(e)}", exc_info=True)
        # Default fallback price
        return 150.0

def finalize_deal(campaign_id: str, contact_id: str, agreed_price: float) -> str:
    """
    Finalize the deal by storing it in the database.
    Returns a confirmation message.
    """
    logger.info(f"Finalizing deal for campaign {campaign_id}, contact {contact_id} at ${agreed_price:.2f}")

    try:
        # Store the deal in Supabase
        deal_data = {
            "campaign_id": campaign_id,
            "contact_id": contact_id,
            "agreed_price": agreed_price,
            "status": "agreed"
        }

        response = supabase_client.table("deal").insert(deal_data).execute()
        logger.info(f"Deal finalized successfully: {response.data}")

        return f"Great! We have a deal at ${agreed_price:.2f}. I'll send over the contract details shortly."

    except Exception as e:
        logger.error(f"Error finalizing deal: {str(e)}", exc_info=True)
        return "I've noted our agreement. Our team will follow up with the contract details."

def generate_initial_message_body(request: 'InitiateCampaignRequest') -> dict:
    logger.info(f"Generating initial message for campaign: {request.campaign_id}, product: {request.product_name}")

    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        logger.error("OPENAI_API_KEY not found in environment variables")
        raise RuntimeError("OPENAI_API_KEY not found in environment variables")

    openai_client = openai.OpenAI(api_key=openai_api_key)

    user_prompt = get_initial_outreach_user_prompt(
        brand_metadata=request.brand_metadata,
        product_name=request.product_name,
        product_url=request.product_url,
        campaign_description=request.campaign_description
    )

    messages = [
        {"role": "system", "content": INITIAL_OUTREACH_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt}
    ]

    logger.info("Calling OpenAI API to generate email content")
    completion = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=500,
        temperature=0.7,
        response_format={"type": "json_object"}
    )

    generated_content = completion.choices[0].message.content
    result = json.loads(generated_content)

    logger.info(f"Successfully generated email with subject: {result.get('subject', 'N/A')}")

    return {
        "subject": result.get("subject", ""),
        "html_body": result.get("html_body", "")
    }

@router.post("/initiate", response_model=InitiateCampaignResponse)
async def initiate_campaign(request: InitiateCampaignRequest):
    """
    Initiate a campaign by:
    1. Scraping TikTok for relevant creators based on campaign description
    2. Fetching the newly scraped contacts from database
    3. Sending outreach emails to those contacts
    """
    logger.info(f"Initiating campaign: {request.campaign_id} for brand: {request.brand_id}")

    try:
        # Step 1: Run the TikTok crawler to find relevant creators
        logger.info(f"Starting crawler for campaign: {request.campaign_description}")

        # profiles_scraped = await run_campaign_scraper_sync(
        #     campaign_description=request.campaign_description,
        #     num_queries=10,  # Generate 10 search queries
        #     users_per_search=10,  # Get 10 users per query = ~100 total contacts
        #     filter_emails_only=True,  # Only get profiles with emails
        #     supabase_url=os.getenv('SUPABASE_URL'),
        #     supabase_key=os.getenv('SUPABASE_KEY')
        # )

        # logger.info(f"Crawler completed: {profiles_scraped} profiles scraped and saved to database")

        # Step 2: Fetch the newly scraped contacts from database
        contacts_list = get_contacts_list(10)

        if len(contacts_list) == 0:
            logger.error("No contacts found after scraping. Cannot send emails.")
            raise HTTPException(
                status_code=400,
                detail="No contacts found. Scraping may have failed or no profiles matched criteria."
            )

        # Step 3: Generate email content and send to contacts
        email_content = generate_initial_message_body(request)

        for contact in contacts_list:
            contact_id = contact["uuid"]
            contact_email = contact["email"]
            logger.info(f"Sending email to {contact_email} for campaign {request.campaign_id}")

            sent_message = agentmail_client.inboxes.messages.send(
                inbox_id=NEGOTIATE_INBOX_ID,
                to=contact_email,
                labels=[f"{request.campaign_id}:{contact_id}"],
                subject=email_content["subject"],
                text="We are looking for a paid partnership opportunity for UGC for this product...",
                html=email_content["html_body"],
            )
            logger.info(f"Email sent successfully to {contact_email}: {sent_message}")

        logger.info(f"Campaign {request.campaign_id} initiated successfully. Sent to {len(contacts_list)} contacts")
        return {"status": "campaign initiated"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error initiating campaign {request.campaign_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/receive-message", response_model=WebhookResponse)
async def handle_webhook(payload: WebhookPayload):
    logger.info(f"Received webhook event: {payload.event_type}")

    try:
        message = payload.message

        # Labels aren't preserved in replies, so we need to find them from the thread
        # Fetch all messages in the thread to find the original message with our labels
        campaign_id = None
        contact_id = None
        thread_messages = None

        try:
            # Use threads.get() to retrieve the thread and its messages
            thread = agentmail_client.threads.get(thread_id=message.thread_id)
            thread_messages = thread.messages if hasattr(thread, 'messages') else []
            logger.info(f"Retrieved thread with {len(thread_messages)} messages")

            # Look through thread messages to find our campaign_id:contact_id label
            for thread_msg in thread_messages:
                # Messages might be objects or dicts, handle both
                labels = thread_msg.labels if hasattr(thread_msg, 'labels') else thread_msg.get('labels', [])
                for label in labels:
                    if ":" in label and label not in ["received", "unread", "sent"]:
                        parts = label.split(":")
                        if len(parts) == 2:
                            campaign_id = parts[0]
                            contact_id = parts[1]
                            logger.info(f"Found campaign labels from thread: {campaign_id}:{contact_id}")
                            break
                if campaign_id:
                    break

        except Exception as e:
            logger.error(f"Error fetching thread: {str(e)}", exc_info=True)

        if not campaign_id or not contact_id:
            logger.warning(f"Could not find campaign_id:contact_id labels in thread {message.thread_id}")
            return {"status": "ignored - no campaign labels found in thread"}

        logger.info(f"Processing message for campaign: {campaign_id}, contact: {contact_id}")

        try:
            campaign_response = supabase_client.table("campaign") \
                .select("*") \
                .eq("id", campaign_id) \
                .single() \
                .execute()
            campaign_data = campaign_response.data
        except Exception as e:
            logger.error(f"Error fetching campaign {campaign_id}: {str(e)}")
            campaign_data = {
                "product_name": "Our Product",
                "campaign_description": "UGC Campaign"
            }

        target_price = get_target_price(contact_id)

        conversation_messages = [
            {"role": "system", "content": NEGOTIATION_SYSTEM_PROMPT},
            {
                "role": "system",
                "content": get_negotiation_context_prompt(
                    target_price=target_price,
                    product_name=campaign_data.get("product_name", "Our Product"),
                    campaign_description=campaign_data.get("campaign_description", "UGC Campaign")
                )
            }
        ]

        if thread_messages:
            for msg in thread_messages:
                # Handle both object and dict formats
                inbox_id = msg.inbox_id if hasattr(msg, 'inbox_id') else msg.get('inbox_id')
                text = msg.text if hasattr(msg, 'text') else msg.get('text')

                if inbox_id == NEGOTIATE_INBOX_ID:
                    role = "assistant"
                else:
                    role = "user"

                conversation_messages.append({
                    "role": role,
                    "content": text
                })

        negotiation_tools = [
            {
                "type": "function",
                "function": {
                    "name": "finalize_deal",
                    "description": "Finalize the deal when both parties agree on a price",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "agreed_price": {
                                "type": "number",
                                "description": "The final agreed price in USD",
                            },
                        },
                        "required": ["agreed_price"],
                    },
                },
            }
        ]

        def finalize_deal_wrapper(agreed_price: float) -> str:
            return finalize_deal(campaign_id, contact_id, agreed_price)

        available_tools_map = {
            "finalize_deal": finalize_deal_wrapper
        }
        agent_response = run_conversation(
            conversation_messages,
            negotiation_tools,
            available_tools_map
        )

        if not agent_response:
            logger.error("Agent returned no response")
            return {"status": "error - no agent response"}

        response_text = agent_response.content

        # Send response via AgentMail using reply method
        logger.info(f"Sending agent response to thread: {message.thread_id}")

        # Use messages.reply() to reply to the incoming message
        agentmail_client.inboxes.messages.reply(
            inbox_id=NEGOTIATE_INBOX_ID,
            message_id=message.message_id,
            text=response_text,
            labels=[f"{campaign_id}:{contact_id}"]  # Preserve our campaign labels
        )

        logger.info("Response sent successfully")
        return {"status": "success"}

    except Exception as e:
        logger.error(f"Error handling webhook: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))