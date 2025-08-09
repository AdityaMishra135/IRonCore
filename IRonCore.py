from telegram.ext import ApplicationBuilder, CommandHandler
from fastapi import FastAPI
import uvicorn
import os
import asyncio

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
PORT = int(os.getenv("PORT", 10000))  # Render provides PORT for web services

# Telegram Bot
async def start(update, context):
    await update.message.reply_text("🌐 Web Service Bot Activated!")

telegram_app = ApplicationBuilder().token(TOKEN).build()
telegram_app.add_handler(CommandHandler("start", start))

# FastAPI Web Server
web_app = FastAPI()

@web_app.get("/")
def health_check():
    return {"status": "OK", "bot": "running"}

async def run():
    # Start both services
    await telegram_app.initialize()
    await telegram_app.start()
    
    config = uvicorn.Config(
        web_app,
        host="0.0.0.0",
        port=PORT,
        log_level="info"
    )
    server = uvicorn.Server(config)
    
    await server.serve()

if __name__ == "__main__":
    asyncio.run(run())
