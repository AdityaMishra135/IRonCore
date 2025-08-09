from telegram.ext import ApplicationBuilder, CommandHandler
from fastapi import FastAPI
import uvicorn
import os
import asyncio
import multiprocessing

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Telegram Bot Functions
async def start(update, context):
    """Handle /start command"""
    await update.message.reply_text("🚀 Bot is fully operational!")

# FastAPI Web Server
web_app = FastAPI()

@web_app.get("/")
def health_check():
    """Koyeb health check endpoint"""
    return {"status": "running", "service": "telegram-bot"}

async def run_bot():
    """Run Telegram bot in polling mode"""
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    
    print("🤖 Starting Telegram bot polling...")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    print("✅ Telegram bot is now polling")

def run_web_server():
    """Run the health check web server"""
    uvicorn.run(
        web_app,
        host="0.0.0.0",
        port=8000,  # Koyeb expects port 8000 by default
        log_level="info"
    )

if __name__ == "__main__":
    # Start both services in parallel
    web_process = multiprocessing.Process(target=run_web_server)
    web_process.start()
    
    print("🌐 Starting health check server on port 8000")
    asyncio.run(run_bot())
