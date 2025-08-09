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
    """Run Telegram bot with proper event loop management"""
    async def bot_main():
        app = ApplicationBuilder().token(TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        print("🤖 Starting Telegram bot polling...")
        try:
            await app.initialize()
            await app.start()
            await app.updater.start_polling()
            while True:
                await asyncio.sleep(3600)  # Keep alive
        except asyncio.CancelledError:
            print("\n🛑 Received shutdown signal")
        finally:
            await app.stop()
            await app.shutdown()
    
    # Create new event loop for the bot
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(bot_main())
    finally:
        loop.close()

def run_web():
    """Run health check server with proper shutdown"""
    print("🌐 Starting health check server on port 8000")
    config = uvicorn.Config(
        app="IRonCore:web_app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        workers=1,
        loop="asyncio"
    )
    server = uvicorn.Server(config)
    server.run()

if __name__ == "__main__":
    # Start web server in separate process
    web_process = multiprocessing.Process(target=run_web)
    web_process.start()
    
    # Run bot in main process
    try:
        run_bot()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down gracefully...")
    finally:
        web_process.terminate()
        web_process.join()
        sys.exit(0)
