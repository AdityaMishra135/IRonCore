import os
import asyncio
from telegram.ext import ApplicationBuilder, CommandHandler
from fastapi import FastAPI
import uvicorn
import multiprocessing
import signal
import sys

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Telegram Bot
async def start(update, context):
    await update.message.reply_text("🤖 Bot is fully operational!")

# FastAPI Web Server
web_app = FastAPI()

@web_app.get("/")
def health_check():
    return {"status": "active", "bot": "running"}

def run_bot():
    """Run Telegram bot in its own event loop"""
    async def bot_main():
        app = ApplicationBuilder().token(TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        print("🤖 Starting Telegram bot polling...")
        await app.run_polling()
    
    # Create new event loop for the bot
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(bot_main())
    finally:
        loop.close()

def run_web():
    """Run health check server"""
    print("🌐 Starting health check server on port 8000")
    uvicorn.run(
        app="IRonCore:web_app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        workers=1
    )

if __name__ == "__main__":
    # Start web server in separate process
    web_process = multiprocessing.Process(target=run_web)
    web_process.start()
    
    # Run bot in main process
    try:
        run_bot()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
    finally:
        web_process.terminate()
        web_process.join()
        sys.exit(0)
