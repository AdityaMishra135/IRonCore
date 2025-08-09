import os
from fastapi import FastAPI
import uvicorn
from dotenv import load_dotenv

load_dotenv()

web_app = FastAPI()

@web_app.get("/")
def health_check():
    return {
        "service": os.getenv("SERVICE_NAME"),
        "status": "running",
        "environment": os.getenv("ENVIRONMENT")
    }

def run_web_server():
    uvicorn.run(
        app="handlers.web:web_app",
        host=os.getenv("HOST"),
        port=int(os.getenv("PORT")),
        workers=int(os.getenv("WORKERS")),
        reload=os.getenv("DEBUG").lower() == "true"
    )
