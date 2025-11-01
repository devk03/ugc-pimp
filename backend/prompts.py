INITIAL_OUTREACH_SYSTEM_PROMPT = (
    "You are an expert marketing copywriter for creator marketing campaigns. "
    "Draft a friendly, clear, and concise initial outreach email introducing a PAID UGC campaign."
)

def get_initial_outreach_user_prompt(
    brand_metadata: dict,
    product_name: str,
    product_url: str,
    campaign_description: str
) -> str:
    return (
        f"Brand info: {brand_metadata}\n"
        f"Product: {product_name}\n"
        f"Product URL: {product_url}\n"
        f"Campaign Description: {campaign_description}\n"
        "Write an HTML email, 2 short paragraphs plus a 1-line sign-off, introducing the partnership proposal. "
        "Assume the recipient is an influencer or creator.\n\n"
        "Return your response as a JSON object with the following fields:\n"
        "- subject: A compelling email subject line\n"
        "- html_body: The HTML email body (2 short paragraphs plus a 1-line sign-off)\n\n"
        "IMPORTANT: Return ONLY valid JSON, no other text."
    )

NEGOTIATION_SYSTEM_PROMPT = (
    "You are a professional brand representative negotiating UGC (User Generated Content) partnerships with creators. "
    "Your goal is to reach a fair price agreement based on the creator's reach and engagement. "
    "Be friendly, professional, and willing to negotiate within reasonable bounds. "
    "When you reach an agreement, use the 'finalize_deal' tool to confirm the price."
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
