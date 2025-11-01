from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from router.campaign import router as campaign_router
from dotenv import load_dotenv
from agentmail import AgentMail
from supabase import create_client, Client
import os
import logging
from globals import HOSTNAME

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

WEBHOOK_URL = f"https://{HOSTNAME}/api/v1/campaign/receive-message"

load_dotenv()

agentmail_api_key = os.getenv("AGENTMAIL_API_KEY")
agentmail_client = AgentMail(api_key=agentmail_api_key)

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
supabase_client: Client = create_client(supabase_url, supabase_key)

app = FastAPI(
    title="UGC Pimp API",
    description="API for UGC management",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Log application startup and register webhook"""
    logger.info("UGC Pimp API starting up...")
    logger.info("AgentMail client initialized")
    logger.info("Supabase client initialized")

    # Check if webhook already exists for this URL
    try:
        existing_webhooks = agentmail_client.webhooks.list()
        webhook_exists = False

        for webhook in existing_webhooks.webhooks:
            if webhook.url == WEBHOOK_URL:
                webhook_exists = True
                logger.info(f"Webhook already exists: {webhook.webhook_id} -> {webhook.url}")
                break

        if not webhook_exists:
            webhook = agentmail_client.webhooks.create(url=WEBHOOK_URL, event_types=["message.received"])
            logger.info(f"Webhook registered successfully: {webhook}")
        else:
            logger.info("Skipping webhook registration - already exists")
    except Exception as e:
        logger.error(f"Error managing webhooks: {str(e)}", exc_info=True)
    
@app.on_event("shutdown")
async def shutdown_event():
    """Log application shutdown"""
    logger.info("UGC Pimp API shutting down...")


@app.get("/")
async def root():
    """Root endpoint"""
    logger.info("Root endpoint accessed")
    return {"message": "UGC Pimp API", "status": "alive"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    logger.debug("Health check endpoint accessed")
    return {"status": "healthy"}


app.include_router(campaign_router, prefix="/api/v1")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
