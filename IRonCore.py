from telegram.ext import ApplicationBuilder, CommandHandler
from fastapi import FastAPI
import uvicorn
import os
import asyncio
import signal
import sys

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Telegram Bot
async def start(update, context):
    await update.message.reply_text("🚀 Bot is fully operational!")

# FastAPI App
web_app = FastAPI()

@web_app.get("/")
def health_check():
    return {"status": "running", "service": "telegram-bot"}

async def run_bot():
    """Run Telegram bot with proper shutdown handling"""
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    
    await app.initialize()
    await app.start()
    print("🤖 Bot polling started")
    
    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        print("\n🛑 Received shutdown signal")
        await app.stop()
        await app.shutdown()

def run_web_server():
    """Run the web server with proper config"""
    uvicorn.run(
        app="IRonCore:web_app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        workers=1
    )

if __name__ == "__main__":
    # Signal handling for clean shutdown
    def signal_handler(sig, frame):
        print("\n🚦 Received termination signal")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start web server in a process
    from multiprocessing import Process
    web_process = Process(target=run_web_server)
    web_process.start()
    
    # Run bot in main thread
    try:
        asyncio.run(run_bot())
    finally:
        web_process.terminate()
        web_process.join()
