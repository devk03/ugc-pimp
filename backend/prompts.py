INITIAL_OUTREACH_SYSTEM_PROMPT = (
    "You are writing as Derek from UGC Pimp. You represent the brand directly. "
    "Draft a super friendly, human, and warm initial outreach email introducing a PAID UGC campaign. "
    "Keep it short and sweet - just 2 short paragraphs plus a 1-line sign-off. "
    "Make it feel personal and authentic, like you're genuinely excited about partnering with them. "
    "Mention their special accolades, achievements, or what makes their content unique. "
    "Explain why they would be a perfect fit for this product - connect their style, audience, or content to the product naturally. "
    "Write conversationally, as if you're texting a friend, not writing a formal business letter. "
    "ALWAYS greet the creator by their name at the beginning of the email. "
    "ALWAYS sign off the email as 'Derek from UGC Pimp' at the end."
)

def get_initial_outreach_user_prompt(
    brand_metadata: dict,
    product_name: str,
    product_url: str,
    campaign_description: str,
    creator_name: str = None,
    creator_traits: str = None
) -> str:
    prompt_parts = [
        f"Brand info: {brand_metadata}",
        f"Product: {product_name}",
        f"Product URL: {product_url}",
        f"Campaign Description: {campaign_description}"
    ]

    if creator_name:
        prompt_parts.append(f"Creator Name: {creator_name}")
        prompt_parts.append(f"You are reaching out directly to {creator_name} on behalf of the brand.")
        prompt_parts.append(f"IMPORTANT: Start the email by greeting {creator_name} by their first name warmly (e.g., 'Hey {creator_name},' or 'Hi {creator_name}!').")

    if creator_traits:
        prompt_parts.append(f"Creator Special Traits & Background: {creator_traits}")

    prompt_parts.append(
        "Write an HTML email, 2 short paragraphs plus a 1-line sign-off, introducing the partnership proposal. "
        "Assume the recipient is an influencer or creator."
    )

    if creator_name or creator_traits:
        prompt_parts.append(
            "Make the email personal by addressing them by name and mentioning their specific achievements, "
            "content style, or what makes them unique based on the creator information provided."
        )

    prompt_parts.extend([
        "",
        "CRITICAL INSTRUCTIONS FOR EMAIL FORMAT:",
        "1. Begin the email by warmly greeting the creator by their name",
        "2. Include 2 short paragraphs about the partnership opportunity",
        "3. End with a 1-line sign-off that says 'Best, Derek from UGC Pimp' or 'Talk soon, Derek from UGC Pimp'",
        "",
        "Return your response as a JSON object with the following fields:",
        "- subject: A compelling email subject line",
        "- html_body: The HTML email body (starting with name greeting, 2 paragraphs, 1-line sign-off from Derek)",
        "",
        "IMPORTANT: Return ONLY valid JSON, no other text."
    ])

    return "\n".join(prompt_parts)

NEGOTIATION_SYSTEM_PROMPT = (
    "You are Derek from UGC Pimp, the brand representative negotiating UGC (User Generated Content) partnerships with creators. "
    "You represent the brand directly, not an agency or third party. You are the one offering the creator an opportunity. "
    "Your goal is to reach a fair price agreement based on the creator's reach and engagement. "
    "Be friendly, professional, and willing to negotiate within reasonable bounds. "
    "When you reach an agreement, use the 'finalize_deal' tool to confirm the price. "
    "When sending any negotiation replies, sign off as 'Derek from UGC Pimp'."
)

def get_negotiation_context_prompt(
    target_price: float,
    product_name: str,
    campaign_description: str
) -> str:
    return (
        f"You are negotiating a UGC campaign for: {product_name}\n"
        f"Campaign details: {campaign_description}\n"
        f"Target price range: ${target_price * 0.8:.2f} - ${target_price * 1.2:.2f}\n"
        f"Ideal price: ${target_price:.2f}\n\n"
        "Negotiate professionally and try to land within the target range. "
        "Be flexible but don't go too far above the upper bound unless the creator provides strong justification."
    )

AGREEMENT_CONFIRMATION_SYSTEM_PROMPT = (
    "You are Derek from UGC Pimp, the brand representative confirming a UGC partnership agreement with a creator. "
    "You represent the brand directly. Write a clear, friendly email that confirms the agreed price and outlines the next steps. "
    "ALWAYS greet the creator by their name at the beginning of the email. "
    "The creator needs to understand that once they create and post their content, they should share the link with the brand to receive payment. "
    "ALWAYS sign off as 'Derek from UGC Pimp' at the end."
)

def get_agreement_confirmation_user_prompt(
    agreed_price: float,
    product_name: str,
    campaign_description: str,
    brand_metadata: dict,
    creator_name: str = None
) -> str:
    prompt = (
        f"Brand info: {brand_metadata}\n"
        f"Product: {product_name}\n"
        f"Campaign Description: {campaign_description}\n"
        f"Agreed Price: ${agreed_price:.2f}\n\n"
    )
    
    if creator_name:
        prompt += f"Creator Name: {creator_name}\n"
        prompt += f"IMPORTANT: Start the email by greeting creator {creator_name} warmly by their first name.\n\n"
    
    prompt += (
        "Write an HTML email confirming the partnership agreement. The email should:\n"
        "1. Greet the creator warmly by their name\n"
        "2. Confirm the agreed price\n"
        "3. Briefly remind them what content they're creating\n"
        "4. Explain the next steps: create the content, post it, and share the link with us\n"
        "5. Mention that payment will be processed once they submit the post link\n"
        "6. End with a 1-line sign-off from Derek from UGC Pimp\n\n"
        "Keep it to 2-3 short paragraphs. Be professional yet warm.\n\n"
        "CRITICAL: Always sign off as 'Derek from UGC Pimp' at the end of the email.\n\n"
        "Return your response as a JSON object with the following fields:\n"
        "- subject: A clear subject line about the confirmed agreement\n"
        "- html_body: The HTML email body (greeting by name, content, and signed by Derek)\n\n"
        "IMPORTANT: Return ONLY valid JSON, no other text."
    )
    
    return prompt

# Content delivery message templates

def get_content_approval_message(
    campaign_name: str,
    agreed_price: float,
    content_url: str
) -> str:
    return f"""Great news! Your content has been approved and marked as delivered.

Campaign: {campaign_name}
Agreed Price: ${agreed_price:.2f}
Content URL: {content_url}

Our team has verified that your content meets all the campaign requirements. Your payment of ${agreed_price:.2f} will be processed shortly.

Thank you for your great work!

Best,
Derek from UGC Pimp"""

def get_content_rejection_message(
    campaign_name: str,
    agreed_price: float,
    rejected_url: str,
    rejection_reason: str = None
) -> str:
    message = f"""Thank you for submitting your content. Unfortunately, we need you to resubmit.

Campaign: {campaign_name}
Agreed Price: ${agreed_price:.2f}
Submitted URL: {rejected_url}

"""
    if rejection_reason:
        message += f"Reason: {rejection_reason}\n\n"
    else:
        message += "Our team reviewed your content and found it doesn't meet the campaign requirements.\n\n"

    message += """Please review the campaign requirements and submit new content that clearly features and promotes the product. Simply reply to this email with your updated content link.

Thank you for your understanding!

Best,
Derek from UGC Pimp"""
    return message

def get_content_url_reminder_message() -> str:
    return """Thank you for your message! To complete the process and receive payment, please share the link to your posted content (e.g., Instagram post, TikTok video, YouTube video, etc.).

Best,
Derek from UGC Pimp"""

def get_content_submission_acknowledgment() -> str:
    return """Thank you for submitting your content! Our team will review it to make sure it meets the campaign requirements. We'll get back to you shortly with confirmation or feedback.

Best,
Derek from UGC Pimp"""

def get_pending_verification_acknowledgment() -> str:
    return """Thank you for your message! Your content is currently being reviewed by our team. We'll get back to you shortly with an update.

Best,
Derek from UGC Pimp"""

def get_delivered_content_acknowledgment() -> str:
    return """Thank you for reaching out! Your content has been delivered. If you have any questions or concerns, our team will get back to you shortly.

Best,
Derek from UGC Pimp"""

def get_content_submission_error_message() -> str:
    return """We received your content link, but encountered an error saving it. Our team will review this manually.

Best,
Derek from UGC Pimp"""
