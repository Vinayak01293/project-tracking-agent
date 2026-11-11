
from dotenv import load_dotenv

# Load environment variables before importing the API router.
load_dotenv()

from fastapi import FastAPI

from core.platform.logging_config import configure_logging

configure_logging()

from core.api.chat_router import router as chat_router
from core.api.user_router import router as user_router

app = FastAPI(
    title="Project Tracking Agent",
    description="Multi-agent system for GitHub and Linear integrations.",
)

app.include_router(user_router)
app.include_router(chat_router)


@app.get("/health")
def health_check():
    return {"status": "healthy"}
