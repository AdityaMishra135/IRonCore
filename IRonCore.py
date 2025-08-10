import os
import asyncio
import multiprocessing
import logging
import fcntl
from pathlib import Path
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

def prevent_multiple_instances():
    """Ensure only one bot instance runs at a time"""
    lockfile = Path("bot_instance.lock")
    try:
        lockfile.touch(exist_ok=True)
        lockfile_fd = os.open(lockfile, os.O_WRONLY)
        fcntl.flock(lockfile_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return lockfile_fd
    except (IOError, BlockingIOError):
        logger.error("Another bot instance is already running")
        raise SystemExit(1)
    except Exception as e:
        logger.error(f"Failed to create lockfile: {e}")
        raise SystemExit(1)

async def main():
    """Main application entry point"""
    # Initialize database first
    from database.database import init_db
    init_db()

    # Build application with conflict prevention
    app = (
        ApplicationBuilder()
        .token(os.getenv("BOT_TOKEN"))
        .concurrent_updates(True)
        .http_version("1.1")
        .get_updates_http_version("1.1")
        .build()
    )
    
    # Setup handlers
    setup_group_handlers(app)
    setup_admin_handlers(app)
    setup_info_handler(app)
    
    logger.info("Starting bot in %s environment", os.getenv("ENVIRONMENT"))
    
    try:
        await app.initialize()
        await app.start()
        await app.updater.start_polling(
            bootstrap_retries=-1,
            timeout=30,
            read_timeout=30
        )
        
        # Keep alive
        while True:
            await asyncio.sleep(3600)
            
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
    finally:
        if hasattr(app, 'updater') and app.updater.running:
            await app.updater.stop()
        if hasattr(app, 'running') and app.running:
            await app.stop()

if __name__ == "__main__":
    # Prevent multiple instances
    lock_fd = prevent_multiple_instances()
    
    try:
        # Start web server
        web_process = multiprocessing.Process(
            target=run_web_server,
            daemon=True
        )
        web_process.start()
        
        # Run bot
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    finally:
        # Cleanup
        try:
            if 'web_process' in locals():
                web_process.terminate()
                web_process.join()
            if 'lock_fd' in locals():
                os.close(lock_fd)
                Path("bot_instance.lock").unlink(missing_ok=True)
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
