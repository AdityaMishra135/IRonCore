from fastapi import FastAPI
import uvicorn
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

web_app = FastAPI()

@web_app.get("/")
def health_check():
    return {
        "status": "running",
        "service": os.getenv("SERVICE_NAME"),
        "environment": os.getenv("ENVIRONMENT")
    }

def run_web_server():
    uvicorn.run(
        app="handlers.web_server:web_app",
        host=os.getenv("HOST"),
        port=int(os.getenv("PORT")),
        workers=int(os.getenv("WEB_WORKERS")),
        reload=os.getenv("DEBUG_MODE").lower() == "true"
    )
