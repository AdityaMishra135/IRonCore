import os
import asyncio
from telegram.ext import ApplicationBuilder, CommandHandler
from fastapi import FastAPI
import uvicorn
import multiprocessing

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Telegram Bot
async def start(update, context):
    await update.message.reply_text("✅ Bot is working perfectly now!")

# Web Server for Health Checks
web_app = FastAPI()

@web_app.get("/")
def health_check():
    return {"status": "active", "bot": "ready"}

def run_bot():
    """Run Telegram bot in polling mode"""
    async def bot_main():
        app = ApplicationBuilder().token(TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        print("🤖 Bot polling started")
        await app.run_polling()

    asyncio.run(bot_main())

def run_web():
    """Run health check server"""
    uvicorn.run(web_app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    # Start web server in separate process
    web_process = multiprocessing.Process(target=run_web)
    web_process.start()
    
    # Run bot in main process
    run_bot()
