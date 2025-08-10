import os
import asyncio
import multiprocessing
import logging
from dotenv import load_dotenv
from telegram.ext import Application
from telegram.ext import ApplicationBuilder
from handlers.admin import setup_admin_handlers
from handlers.group import setup_group_handlers
from handlers.info import setup_info_handler
from handlers.web_server import run_web_server

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def main():
     # Initialize database first
    from database.database import init_db
    init_db()

    """Main application entry point"""
    app = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()
    
    # Setup handlers
    setup_group_handlers(app)
    setup_admin_handlers(app)
    setup_info_handler(app)
    

    logger.info("Starting bot in %s environment", os.getenv("ENVIRONMENT"))
    await app.initialize()
    await app.run_polling()
    await app.start()
    await app.updater.start_polling()
    
    # Keep alive
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    # Start web server
    web_process = multiprocessing.Process(
        target=run_web_server,
        daemon=True
    )
    web_process.start()
    
    # Run bot
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
    finally:
        web_process.terminate()
        web_process.join()
