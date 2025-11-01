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
    get_negotiation_context_prompt,
    AGREEMENT_CONFIRMATION_SYSTEM_PROMPT,
    get_agreement_confirmation_user_prompt
)

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
    product_name: str
    product_url: Optional[str] = None
    campaign_description: str
    # Optional fields from trigger
    metadata: Optional[dict] = None
    campaign_name: Optional[str] = None
    state: Optional[str] = None
    scheduled_start_date: Optional[str] = None
    scheduled_end_date: Optional[str] = None

class InitiateCampaignResponse(BaseModel):
    status: str

class WebhookResponse(BaseModel):
    status: str

class Message(BaseModel):
    from_: str = Field(alias="from")
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

def get_contacts_list() -> list[dict]:
    """
    Fetch the two most recent contacts from Supabase.
    Falls back to default values if fewer than 2 contacts are present.
    TODO: fix
    """
    logger.info("Fetching contacts list from Supabase")

    default_contacts = [
        {"id": "688793b6-e6d6-4fc6-8aed-a55399bbe254", "email": "derekmillerdev@gmail.com"},
        {"id": "4276764e-7364-495e-9be6-547556ba3536", "email": "dtkunjadia@gmail.com"},
    ]

    try:
        # response = supabase_client.table("contact") \
        #     .select("id, email") \
        #     .order("created_at", desc=True) \
        #     .limit(2) \
        #     .execute()

        contacts = []
        # if response.data:
        #     for contact in response.data:
        #         if contact.get("email"):
        #             contacts.append({
        #                 "uuid": str(contact["id"]),
        #                 "email": contact["email"]
        #             })

        # logger.info(f"Retrieved {len(contacts)} contacts from Supabase")

        while len(contacts) < 2:
            contacts.append(default_contacts[len(contacts)])
            logger.info(f"Added default contact {len(contacts)}")

        return contacts

    except Exception as e:
        logger.error(f"Error fetching contacts from Supabase: {str(e)}", exc_info=True)
        logger.info("Falling back to default contacts")
        return default_contacts

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

def create_contact_campaign(campaign_id: str, contact_id: str) -> dict:
    """
    Create a contact_campaign record with 'proposed' status.
    Returns the created record or None if it fails.
    """
    logger.info(f"Creating contact_campaign record for campaign {campaign_id}, contact {contact_id}")

    try:
        contact_campaign_data = {
            "campaign_id": campaign_id,
            "contact_id": contact_id,
            "status": "proposed"
        }

        response = supabase_client.table("contact_campaign").insert(contact_campaign_data).execute()
        logger.info(f"contact_campaign record created: {response.data}")
        return response.data[0] if response.data else None

    except Exception as e:
        logger.error(f"Error creating contact_campaign record: {str(e)}", exc_info=True)
        return None

def get_contact_campaign_status(campaign_id: str, contact_id: str) -> str:
    """
    Get the current status of a contact_campaign record.
    Returns the status or None if not found.
    """
    logger.info(f"Fetching contact_campaign status for campaign {campaign_id}, contact {contact_id}")

    try:
        response = supabase_client.table("contact_campaign") \
            .select("status") \
            .eq("campaign_id", campaign_id) \
            .eq("contact_id", contact_id) \
            .single() \
            .execute()

        if response.data:
            status = response.data.get("status")
            logger.info(f"Current contact_campaign status: {status}")
            return status
        else:
            logger.warning(f"No contact_campaign record found for campaign {campaign_id}, contact {contact_id}")
            return None

    except Exception as e:
        logger.error(f"Error fetching contact_campaign status: {str(e)}", exc_info=True)
        return None

def update_contact_campaign_status(campaign_id: str, contact_id: str, status: str) -> bool:
    """
    Update the status of a contact_campaign record.
    Valid statuses: 'proposed', 'negotiating', 'agreed', 'delivered'
    Returns True if successful, False otherwise.
    """
    logger.info(f"Updating contact_campaign status to '{status}' for campaign {campaign_id}, contact {contact_id}")

    try:
        response = supabase_client.table("contact_campaign") \
            .update({"status": status, "updated_at": "now()"}) \
            .eq("campaign_id", campaign_id) \
            .eq("contact_id", contact_id) \
            .execute()

        logger.info(f"contact_campaign status updated successfully")
        return True

    except Exception as e:
        logger.error(f"Error updating contact_campaign status: {str(e)}", exc_info=True)
        return False

def confirm_agreement(
    campaign_id: str,
    contact_id: str,
    agreed_price: float,
    message_id: str,
    campaign_data: dict,
    brand_metadata: dict
) -> dict:
    """
    Confirm the agreement by storing it in the database, updating status to 'agreed',
    and sending a confirmation email with next steps.
    Note: The deal still needs to be delivered (status will be updated to 'delivered' later).
    Returns a dict with 'success' boolean and 'message' string.
    """
    logger.info(f"Confirming agreement for campaign {campaign_id}, contact {contact_id} at ${agreed_price:.2f}")

    try:
        # Update contact_campaign with agreed price and status
        supabase_client.table("contact_campaign") \
            .update({
                "status": "agreed",
                "agreed_price": agreed_price,
                "updated_at": "now()"
            }) \
            .eq("campaign_id", campaign_id) \
            .eq("contact_id", contact_id) \
            .execute()

        logger.info(f"Agreement confirmed successfully: ${agreed_price:.2f}")

        # Generate and send confirmation email immediately
        try:
            confirmation_content = generate_confirmed_message_body(
                agreed_price=agreed_price,
                product_name=campaign_data.get("product", "Our Product"),
                campaign_description=campaign_data.get("description", ""),
                brand_metadata=brand_metadata
            )

            # Send the confirmation email
            agentmail_client.inboxes.messages.reply(
                inbox_id=NEGOTIATE_INBOX_ID,
                message_id=message_id,
                text=confirmation_content["html_body"],
                html=confirmation_content["html_body"],
                labels=[f"{campaign_id}:{contact_id}"]
            )
            logger.info("Sent confirmation email with next steps")
            return {
                "success": True,
                "message": "Agreement confirmed and confirmation email sent"
            }

        except Exception as e:
            logger.error(f"Error sending confirmation email: {str(e)}", exc_info=True)
            return {
                "success": True,
                "message": "Agreement confirmed but failed to send confirmation email"
            }

    except Exception as e:
        logger.error(f"Error confirming agreement: {str(e)}", exc_info=True)
        return {
            "success": False,
            "message": "Failed to confirm agreement"
        }

def generate_initial_message_body(
    product_name: str,
    product_url: str,
    campaign_description: str,
    brand_metadata: dict
) -> dict:
    logger.info(f"Generating initial message for product: {product_name}")

    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        logger.error("OPENAI_API_KEY not found in environment variables")
        raise RuntimeError("OPENAI_API_KEY not found in environment variables")

    openai_client = openai.OpenAI(api_key=openai_api_key)

    user_prompt = get_initial_outreach_user_prompt(
        brand_metadata=brand_metadata,
        product_name=product_name,
        product_url=product_url,
        campaign_description=campaign_description
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

def generate_confirmed_message_body(
    agreed_price: float,
    product_name: str,
    campaign_description: str,
    brand_metadata: dict
) -> dict:
    """
    Generate an agreement confirmation email using OpenAI.
    Returns a dict with 'subject' and 'html_body'.
    """
    logger.info(f"Generating confirmation message for agreed price: ${agreed_price:.2f}")

    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        logger.error("OPENAI_API_KEY not found in environment variables")
        raise RuntimeError("OPENAI_API_KEY not found in environment variables")

    openai_client = openai.OpenAI(api_key=openai_api_key)

    user_prompt = get_agreement_confirmation_user_prompt(
        agreed_price=agreed_price,
        product_name=product_name,
        campaign_description=campaign_description,
        brand_metadata=brand_metadata
    )

    messages = [
        {"role": "system", "content": AGREEMENT_CONFIRMATION_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt}
    ]

    logger.info("Calling OpenAI API to generate confirmation email")
    completion = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=500,
        temperature=0.7,
        response_format={"type": "json_object"}
    )

    generated_content = completion.choices[0].message.content
    result = json.loads(generated_content)

    logger.info(f"Successfully generated confirmation email with subject: {result.get('subject', 'N/A')}")

    return {
        "subject": result.get("subject", ""),
        "html_body": result.get("html_body", "")
    }

@router.post("/initiate", response_model=InitiateCampaignResponse)
async def initiate_campaign(request: InitiateCampaignRequest):
    # TODO: get the actual relevant contacts for the campaign
    logger.info(f"Initiating campaign: {request.campaign_id} for brand: {request.brand_id}")

    try:
        # Fetch brand metadata from database
        try:
            brand_response = supabase_client.table("brand") \
                .select("*") \
                .eq("id", str(request.brand_id)) \
                .single() \
                .execute()
            brand_metadata = brand_response.data
            logger.info(f"Fetched brand metadata for brand: {request.brand_id}")
        except Exception as e:
            logger.error(f"Error fetching brand metadata: {str(e)}", exc_info=True)
            brand_metadata = {}

        contacts_list = get_contacts_list()

        email_content = generate_initial_message_body(
            product_name=request.product_name,
            product_url=request.product_url,
            campaign_description=request.campaign_description,
            brand_metadata=brand_metadata
        )

        for contact in contacts_list:
            contact_id = contact["id"]
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

            # Create contact_campaign record with 'proposed' status
            create_contact_campaign(str(request.campaign_id), contact_id)

        logger.info(f"Campaign {request.campaign_id} initiated successfully. Sent to {len(contacts_list)} contacts")
        return {"status": "campaign initiated"}
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

        # Check current contact_campaign status to determine appropriate action
        current_status = get_contact_campaign_status(campaign_id, contact_id)

        if not current_status:
            logger.warning(f"No contact_campaign record found for campaign {campaign_id}, contact {contact_id}")
            return {"status": "ignored - no contact_campaign record found"}

        logger.info(f"Current contact_campaign status: {current_status}")

        # Handle different states
        if current_status == "proposed" or current_status == "negotiating":
            # Run negotiation agent for proposed and negotiating states
            if current_status == "proposed":
                logger.info(f"Contact responded for the first time, transitioning to 'negotiating'")
                update_contact_campaign_status(campaign_id, contact_id, "negotiating")
            else:
                logger.info(f"Continuing negotiation with contact")

            # Fetch campaign data and brand metadata
            try:
                campaign_response = supabase_client.table("campaign") \
                    .select("*") \
                    .eq("id", campaign_id) \
                    .single() \
                    .execute()
                campaign_data = campaign_response.data

                brand_response = supabase_client.table("brand") \
                    .select("*") \
                    .eq("id", campaign_data.get("brand_id")) \
                    .single() \
                    .execute()
                brand_metadata = brand_response.data
            except Exception as e:
                logger.error(f"Error fetching campaign/brand data: {str(e)}")
                campaign_data = {
                    "product": "Our Product",
                    "description": "UGC Campaign"
                }
                brand_metadata = {}

            target_price = get_target_price(contact_id)

            # Build conversation history
            conversation_messages = [
                {"role": "system", "content": NEGOTIATION_SYSTEM_PROMPT},
                {
                    "role": "system",
                    "content": get_negotiation_context_prompt(
                        target_price=target_price,
                        product_name=campaign_data.get("product", "Our Product"),
                        campaign_description=campaign_data.get("description", "UGC Campaign")
                    )
                }
            ]

            if thread_messages:
                for msg in thread_messages:
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

            # Setup negotiation tools
            negotiation_tools = [
                {
                    "type": "function",
                    "function": {
                        "name": "confirm_agreement",
                        "description": "Confirm the agreement when both parties agree on a price. This will immediately send a confirmation email with next steps.",
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

            # Track if agreement was confirmed
            agreement_confirmed = False

            def confirm_agreement_wrapper(agreed_price: float) -> str:
                nonlocal agreement_confirmed
                result = confirm_agreement(
                    campaign_id=campaign_id,
                    contact_id=contact_id,
                    agreed_price=agreed_price,
                    message_id=message.message_id,
                    campaign_data=campaign_data,
                    brand_metadata=brand_metadata
                )
                agreement_confirmed = result.get("success", False)
                return result.get("message", "Agreement processed")

            available_tools_map = {
                "confirm_agreement": confirm_agreement_wrapper
            }

            # Run the negotiation agent
            agent_response = run_conversation(
                conversation_messages,
                negotiation_tools,
                available_tools_map
            )

            if not agent_response:
                logger.error("Agent returned no response")
                return {"status": "error - no agent response"}

            # If agreement was confirmed, confirmation email was already sent
            if agreement_confirmed:
                logger.info("Agreement confirmed, confirmation email already sent")
                return {"status": "success - agreement confirmed"}

            # Otherwise, send the agent's negotiation response
            response_text = agent_response.content
            logger.info(f"Sending negotiation response to thread: {message.thread_id}")

            agentmail_client.inboxes.messages.reply(
                inbox_id=NEGOTIATE_INBOX_ID,
                message_id=message.message_id,
                text=response_text,
                labels=[f"{campaign_id}:{contact_id}"]
            )

            logger.info("Negotiation response sent successfully")
            return {"status": "success"}

        elif current_status == "agreed":
            # Deal is already agreed, remind them to deliver content
            logger.info(f"Deal is already agreed. Reminding contact to deliver content.")
            response_text = "Thank you for your message! We've already confirmed our agreement. To complete the process and receive payment, please create and post your content, then share the link with us here."
            agentmail_client.inboxes.messages.reply(
                inbox_id=NEGOTIATE_INBOX_ID,
                message_id=message.message_id,
                text=response_text,
                labels=[f"{campaign_id}:{contact_id}"]
            )
            logger.info("Sent delivery reminder")
            return {"status": "success - sent delivery reminder"}

        elif current_status == "delivered":
            # Content already delivered, handle follow-up questions
            logger.info(f"Content already delivered. Contact may have follow-up questions.")
            response_text = "Thank you for reaching out! Your content has been delivered. If you have any questions or concerns, our team will get back to you shortly."
            agentmail_client.inboxes.messages.reply(
                inbox_id=NEGOTIATE_INBOX_ID,
                message_id=message.message_id,
                text=response_text,
                labels=[f"{campaign_id}:{contact_id}"]
            )
            logger.info("Sent acknowledgment for delivered content")
            return {"status": "success - acknowledged delivered content"}

    except Exception as e:
        logger.error(f"Error handling webhook: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))