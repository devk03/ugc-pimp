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
import re
from prompts import (
    INITIAL_OUTREACH_SYSTEM_PROMPT,
    get_initial_outreach_user_prompt,
    NEGOTIATION_SYSTEM_PROMPT,
    get_negotiation_context_prompt,
    AGREEMENT_CONFIRMATION_SYSTEM_PROMPT,
    get_agreement_confirmation_user_prompt,
    get_content_approval_message,
    get_content_rejection_message,
    get_content_url_reminder_message,
    get_content_submission_acknowledgment,
    get_pending_verification_acknowledgment,
    get_delivered_content_acknowledgment,
    get_content_submission_error_message
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

def get_contacts_list(campaign_description: str, limit: int = 10) -> list[dict]:
    """
    Fetch the most relevant contacts from Supabase using semantic search over embeddings.
    Uses vector similarity search to find contacts whose descriptions match the campaign.
    
    Args:
        campaign_description: The campaign description to match against
        limit: Maximum number of contacts to return (default: 10)
    
    Returns:
        List of contact dicts with 'id' and 'email' keys
    """
    logger.info(f"Fetching contacts using semantic search for campaign: {campaign_description[:100]}...")

    default_contacts = [
        {"id": "688793b6-e6d6-4fc6-8aed-a55399bbe254", "email": "derekmillerdev@gmail.com"},
        {"id": "4276764e-7364-495e-9be6-547556ba3536", "email": "dtkunjadia@gmail.com"},
    ]

    try:
        # Generate embedding for campaign description
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            logger.error("OPENAI_API_KEY not found in environment variables")
            logger.warning("Falling back to default contacts")
            return default_contacts[:min(limit, len(default_contacts))]

        openai_client = openai.OpenAI(api_key=openai_api_key)
        
        logger.info("Generating embedding for campaign description")
        embedding_response = openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=campaign_description[:8000]  # Limit length to avoid excessive tokenization
        )
        
        query_embedding = embedding_response.data[0].embedding
        logger.info(f"Generated embedding with {len(query_embedding)} dimensions")

        # Use RPC function to find similar contacts
        response = supabase_client.rpc(
            "match_contacts",
            {
                "query_embedding": query_embedding,
                "match_threshold": 0.7,  # Minimum similarity threshold
                "match_count": limit
            }
        ).execute()

        contacts = []
        if response.data:
            for contact in response.data:
                if contact.get("email"):
                    contacts.append({
                        "id": str(contact["id"]),
                        "email": contact["email"]
                    })
            logger.info(f"Retrieved {len(contacts)} relevant contacts from semantic search")
        
        # Always ensure derekmillerdev contact is included (for testing/monitoring)
        derekmillerdev_contact = default_contacts[0]  # {"id": "688793b6-e6d6-4fc6-8aed-a55399bbe254", "email": "derekmillerdev@gmail.com"}
        if not any(c["id"] == derekmillerdev_contact["id"] for c in contacts):
            contacts.insert(0, derekmillerdev_contact)  # Insert at the beginning
            logger.info("Added derekmillerdev contact as default")
        
        # Fallback to default contacts if no matches found or fewer than needed
        if len(contacts) < limit:
            logger.info(f"Only found {len(contacts)} contacts, supplementing with defaults")
            for default_contact in default_contacts:
                if len(contacts) >= limit:
                    break
                # Avoid duplicates
                if not any(c["id"] == default_contact["id"] for c in contacts):
                    contacts.append(default_contact)
        
        # Return only the requested limit
        return contacts[:limit]

    except Exception as e:
        logger.error(f"Error fetching contacts from Supabase: {str(e)}", exc_info=True)
        logger.info("Falling back to default contacts")
        return default_contacts[:min(limit, len(default_contacts))]

def get_target_price(contact_id: str) -> float:
    """
    Calculate target price based on:
    - 50% from average likes per video
    - 50% from engagement ratio (likes_to_followers_ratio)

    Range: $50-$500
    """
    logger.info(f"Calculating target price for contact: {contact_id}")

    try:
        # Fetch contact metadata from Supabase
        response = supabase_client.table("contact").select("metadata").eq("id", contact_id).single().execute()

        if not response.data:
            logger.warning(f"No contact data found for {contact_id}, using default price")
            return 150.0

        metadata = response.data.get("metadata", {})
        tiktok_data = metadata.get("tiktok", {})

        if not tiktok_data:
            logger.warning(f"No TikTok metadata found for contact {contact_id}, using default price")
            return 150.0

        # Get metrics
        avg_likes = tiktok_data.get("avg_likes_per_video", 0)
        engagement_ratio = tiktok_data.get("likes_to_followers_ratio", 0)

        # Component 1: Price based on average likes ($0.05 per like)
        likes_price = avg_likes * 0.05

        # Component 2: Price based on engagement ratio ($2 per ratio point)
        ratio_price = engagement_ratio * 2.0

        # Combine: 50% each component
        target_price = (likes_price * 0.5) + (ratio_price * 0.5)

        # Enforce minimum and maximum bounds
        target_price = max(50.0, min(500.0, target_price))

        logger.info(f"Target price for contact {contact_id}: ${target_price:.2f} "
                   f"(avg likes: {avg_likes:.0f}, ratio: {engagement_ratio:.2f})")
        return float(target_price)

    except Exception as e:
        logger.error(f"Error calculating target price for contact {contact_id}: {str(e)}", exc_info=True)
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

def strip_quoted_content(text: str) -> str:
    """
    Remove quoted content from email replies to get only the new message content.
    Removes lines starting with '>' and content after common quote markers.
    """
    lines = text.split('\n')
    new_lines = []

    for line in lines:
        # Stop at common email quote markers
        if line.strip().startswith('>'):
            continue
        if 'wrote:' in line.lower() or 'on ' in line.lower() and 'wrote:' in line.lower():
            break
        if line.strip().startswith('----'):
            break
        new_lines.append(line)

    return '\n'.join(new_lines)

def extract_urls_from_text(text: str) -> list[str]:
    """
    Extract all URLs from a text message.
    Returns a list of valid URLs found in the text.
    """
    # Strip quoted content to only get URLs from the new message
    clean_text = strip_quoted_content(text)

    # URL pattern that matches http/https URLs
    url_pattern = r'https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&/=]*)'
    urls = re.findall(url_pattern, clean_text)

    logger.info(f"Extracted {len(urls)} URLs from text (after removing quoted content)")
    return urls

# verify_content_relevance function removed - manual verification now used instead

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

class PendingVerification(BaseModel):
    id: str
    campaign_id: str
    campaign_name: str
    contact_id: str
    contact_name: str
    contact_email: str
    content_url: str
    agreed_price: float
    submitted_at: str

class PendingVerificationsResponse(BaseModel):
    verifications: list[PendingVerification]

class VerifyContentRequest(BaseModel):
    contact_campaign_id: str
    approved: bool
    rejection_reason: Optional[str] = None

class VerifyContentResponse(BaseModel):
    status: str
    message: str

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
        logger.info(f"Starting crawler for campaign: {request.campaign_description}")

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

        contacts_list = get_contacts_list(request.campaign_description)

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

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error initiating campaign {request.campaign_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/pending-verifications", response_model=PendingVerificationsResponse)
async def get_pending_verifications(campaign_id: Optional[str] = None, brand_id: Optional[str] = None):
    """
    Get all pending content verifications, optionally filtered by campaign_id or brand_id.
    """
    logger.info(f"Fetching pending verifications for campaign_id={campaign_id}, brand_id={brand_id}")

    try:
        # Build the query
        query = supabase_client.table("contact_campaign") \
            .select("id, campaign_id, contact_id, content_url, agreed_price, updated_at, campaign(*), contact(*)") \
            .eq("status", "pending_verification")

        if campaign_id:
            query = query.eq("campaign_id", campaign_id)
        elif brand_id:
            # Filter by brand_id through campaign relationship
            query = query.eq("campaign.brand_id", brand_id)

        response = query.execute()

        verifications = []
        for item in response.data:
            campaign_data = item.get("campaign", {})
            contact_data = item.get("contact", {})

            # Handle both dict and list responses for nested data
            if isinstance(campaign_data, list) and len(campaign_data) > 0:
                campaign_data = campaign_data[0]
            if isinstance(contact_data, list) and len(contact_data) > 0:
                contact_data = contact_data[0]

            verifications.append(PendingVerification(
                id=item["id"],
                campaign_id=item["campaign_id"],
                campaign_name=campaign_data.get("name", "Unknown Campaign") if campaign_data else "Unknown Campaign",
                contact_id=item["contact_id"],
                contact_name=f"{contact_data.get('firstname', '')} {contact_data.get('lastname', '')}".strip() if contact_data else "Unknown",
                contact_email=contact_data.get("email", "") if contact_data else "",
                content_url=item.get("content_url", ""),
                agreed_price=item.get("agreed_price", 0.0),
                submitted_at=item.get("updated_at", "")
            ))

        logger.info(f"Found {len(verifications)} pending verifications")
        return {"verifications": verifications}

    except Exception as e:
        logger.error(f"Error fetching pending verifications: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/verify-content", response_model=VerifyContentResponse)
async def verify_content(request: VerifyContentRequest):
    """
    Manually approve or reject submitted content.
    - If approved: status changes to 'delivered'
    - If rejected: status changes back to 'agreed' and creator is notified
    """
    logger.info(f"Verifying content for contact_campaign_id={request.contact_campaign_id}, approved={request.approved}")

    try:
        # Fetch the contact_campaign record
        cc_response = supabase_client.table("contact_campaign") \
            .select("*, campaign(*), contact(*)") \
            .eq("id", request.contact_campaign_id) \
            .single() \
            .execute()

        if not cc_response.data:
            raise HTTPException(status_code=404, detail="Contact campaign not found")

        cc_data = cc_response.data
        campaign_id = cc_data["campaign_id"]
        contact_id = cc_data["contact_id"]

        if cc_data["status"] != "pending_verification":
            raise HTTPException(status_code=400, detail=f"Content is not pending verification (current status: {cc_data['status']})")

        if request.approved:
            # Approve: Update status to 'delivered'
            supabase_client.table("contact_campaign") \
                .update({
                    "status": "delivered",
                    "updated_at": "now()"
                }) \
                .eq("id", request.contact_campaign_id) \
                .execute()

            logger.info(f"Content approved and marked as delivered for contact_campaign {request.contact_campaign_id}")

            # Send email notification to creator about approval
            try:
                contact_data = cc_data.get("contact", {})
                campaign_data = cc_data.get("campaign", {})

                # Handle both dict and list responses for nested data
                if isinstance(contact_data, list) and len(contact_data) > 0:
                    contact_data = contact_data[0]
                if isinstance(campaign_data, list) and len(campaign_data) > 0:
                    campaign_data = campaign_data[0]

                contact_email = contact_data.get("email") if contact_data else None
                campaign_name = campaign_data.get("name", "the campaign") if campaign_data else "the campaign"
                agreed_price = cc_data.get("agreed_price", 0)

                if contact_email:
                    approval_message = get_content_approval_message(
                        campaign_name=campaign_name,
                        agreed_price=agreed_price,
                        content_url=cc_data.get('content_url', 'N/A')
                    )

                    agentmail_client.inboxes.messages.send(
                        inbox_id=NEGOTIATE_INBOX_ID,
                        to=contact_email,
                        subject=f"Content Approved - {campaign_name}",
                        text=approval_message,
                        labels=[f"{campaign_id}:{contact_id}"]
                    )
                    logger.info(f"Sent approval email to {contact_email}")
                else:
                    logger.warning(f"No email found for contact {contact_id}, skipping approval notification")

            except Exception as e:
                logger.error(f"Error sending approval email: {str(e)}", exc_info=True)
                # Don't fail the request if email fails

            return {
                "status": "success",
                "message": "Content approved and marked as delivered"
            }
        else:
            # Reject: Update status back to 'agreed'
            supabase_client.table("contact_campaign") \
                .update({
                    "status": "agreed",
                    "content_url": None,  # Clear the rejected URL
                    "updated_at": "now()"
                }) \
                .eq("id", request.contact_campaign_id) \
                .execute()

            logger.info(f"Content rejected for contact_campaign {request.contact_campaign_id}")

            # Send email notification to creator about rejection
            try:
                contact_data = cc_data.get("contact", {})
                campaign_data = cc_data.get("campaign", {})

                # Handle both dict and list responses for nested data
                if isinstance(contact_data, list) and len(contact_data) > 0:
                    contact_data = contact_data[0]
                if isinstance(campaign_data, list) and len(campaign_data) > 0:
                    campaign_data = campaign_data[0]

                contact_email = contact_data.get("email") if contact_data else None
                campaign_name = campaign_data.get("name", "the campaign") if campaign_data else "the campaign"
                agreed_price = cc_data.get("agreed_price", 0)
                rejected_url = cc_data.get("content_url", "N/A")

                if contact_email:
                    rejection_message = get_content_rejection_message(
                        campaign_name=campaign_name,
                        agreed_price=agreed_price,
                        rejected_url=rejected_url,
                        rejection_reason=request.rejection_reason
                    )

                    agentmail_client.inboxes.messages.send(
                        inbox_id=NEGOTIATE_INBOX_ID,
                        to=contact_email,
                        subject=f"Content Needs Revision - {campaign_name}",
                        text=rejection_message,
                        labels=[f"{campaign_id}:{contact_id}"]
                    )
                    logger.info(f"Sent rejection email to {contact_email}")
                    if request.rejection_reason:
                        logger.info(f"Rejection reason: {request.rejection_reason}")
                else:
                    logger.warning(f"No email found for contact {contact_id}, skipping rejection notification")
                    if request.rejection_reason:
                        logger.info(f"Rejection reason: {request.rejection_reason}")

            except Exception as e:
                logger.error(f"Error sending rejection email: {str(e)}", exc_info=True)
                # Don't fail the request if email fails

            return {
                "status": "success",
                "message": "Content rejected, status reset to 'agreed'"
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying content: {str(e)}", exc_info=True)
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
            # Deal is agreed, waiting for deliverable content URL
            logger.info(f"Deal is agreed. Checking for deliverable content URL.")

            # Extract URLs from the message
            urls = extract_urls_from_text(message.text)

            if not urls:
                # No URLs found, remind them to provide one
                logger.info("No URLs found in message. Reminding contact to provide content link.")
                response_text = get_content_url_reminder_message()
                agentmail_client.inboxes.messages.reply(
                    inbox_id=NEGOTIATE_INBOX_ID,
                    message_id=message.message_id,
                    text=response_text,
                    labels=[f"{campaign_id}:{contact_id}"]
                )
                logger.info("Sent reminder to provide content URL")
                return {"status": "success - requested content URL"}

            # Store the URL and update status to pending_verification
            submitted_url = urls[0]  # Take the first URL
            logger.info(f"Content URL submitted: {submitted_url}")

            try:
                supabase_client.table("contact_campaign") \
                    .update({
                        "status": "pending_verification",
                        "content_url": submitted_url,
                        "updated_at": "now()"
                    }) \
                    .eq("campaign_id", campaign_id) \
                    .eq("contact_id", contact_id) \
                    .execute()

                response_text = get_content_submission_acknowledgment()

                agentmail_client.inboxes.messages.reply(
                    inbox_id=NEGOTIATE_INBOX_ID,
                    message_id=message.message_id,
                    text=response_text,
                    labels=[f"{campaign_id}:{contact_id}"]
                )

                logger.info(f"Content URL stored and status updated to pending_verification")
                return {"status": "success - content pending verification"}

            except Exception as e:
                logger.error(f"Error updating contact_campaign to pending_verification: {str(e)}", exc_info=True)
                response_text = get_content_submission_error_message()
                agentmail_client.inboxes.messages.reply(
                    inbox_id=NEGOTIATE_INBOX_ID,
                    message_id=message.message_id,
                    text=response_text,
                    labels=[f"{campaign_id}:{contact_id}"]
                )
                return {"status": "error - failed to update status"}

        elif current_status == "pending_verification":
            # Content is pending manual verification
            logger.info(f"Content is pending verification. Acknowledging message.")
            response_text = get_pending_verification_acknowledgment()
            agentmail_client.inboxes.messages.reply(
                inbox_id=NEGOTIATE_INBOX_ID,
                message_id=message.message_id,
                text=response_text,
                labels=[f"{campaign_id}:{contact_id}"]
            )
            logger.info("Sent acknowledgment for pending verification")
            return {"status": "success - acknowledged pending verification"}

        elif current_status == "delivered":
            # Content already delivered, handle follow-up questions
            logger.info(f"Content already delivered. Contact may have follow-up questions.")
            response_text = get_delivered_content_acknowledgment()
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