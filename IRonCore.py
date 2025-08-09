import os
import asyncio
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)
from fastapi import FastAPI
import uvicorn
import multiprocessing

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# FastAPI Web Server
web_app = FastAPI()

@web_app.get("/")
def health_check():
    return {"status": "active", "bot": "running"}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bot introduction with add-to-group button"""
    keyboard = [
        [InlineKeyboardButton("➕ Add to Group", 
         url=f"https://t.me/{context.bot.username}?startgroup=true")]
    ]
    await update.message.reply_text(
        "🤖 <b>Supergroup Auto-Upgrade Bot</b>\n\n"
        "I automatically convert any group to supergroup when added!\n"
        "Just add me to your group and I'll handle the rest.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def new_chat_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Detect when bot is added to a group and trigger upgrade"""
    chat = update.effective_chat
    bot_id = context.bot.id
    
    # Check if bot was added
    if any(member.id == bot_id for member in update.message.new_chat_members):
        logger.info(f"Bot added to group {chat.id} ({chat.title})")
        
        if chat.type == "group":
            try:
                # Notify group before leaving
                await update.message.reply_text(
                    "🔄 <b>Starting Supergroup Upgrade</b>\n\n"
                    "This group will be upgraded to supergroup automatically.\n"
                    "Please re-add me to the new supergroup after upgrade.",
                    parse_mode="HTML"
                )
                
                # Leave to trigger upgrade
                await context.bot.leave_chat(chat.id)
                
                logger.info(f"Triggered upgrade for group {chat.id}")
                
            except Exception as e:
                logger.error(f"Upgrade failed for {chat.id}: {e}")
                await update.message.reply_text(
                    "⚠️ Upgrade failed. Please make sure I have admin rights."
                )

async def handle_migration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle successful group migration"""
    old_id = update.message.migrate_from_chat_id
    new_id = update.message.migrate_to_chat_id
    
    logger.info(f"Group migrated from {old_id} to supergroup {new_id}")
    
    # Send welcome message in new supergroup
    await context.bot.send_message(
        new_id,
        "🎉 <b>Upgrade Complete!</b>\n\n"
        "This is now a supergroup with all features unlocked!\n\n"
        "Please add @{context.bot.username} back and make me admin "
        "for full management capabilities.",
        parse_mode="HTML"
    )

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Log errors"""
    logger.error(f"Update {update} caused error {context.error}")

def run_bot():
    """Run Telegram bot with auto-upgrade feature"""
    async def bot_main():
        app = ApplicationBuilder().token(TOKEN).build()
        
        # Add handlers
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(
            filters.StatusUpdate.NEW_CHAT_MEMBERS, 
            new_chat_members
        ))
        app.add_handler(MessageHandler(
            filters.StatusUpdate.MIGRATE,
            handle_migration
        ))
        app.add_error_handler(error_handler)
        
        logger.info("🤖 Starting bot with auto-upgrade feature...")
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        
        # Keep alive
        while True:
            await asyncio.sleep(3600)
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(bot_main())
    finally:
        loop.close()

def run_web():
    """Run health check server"""
    logger.info("🌐 Starting health check server on port 8000")
    config = uvicorn.Config(
        app="IRonCore:web_app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        workers=1
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
        logger.info("🛑 Shutting down gracefully...")
    finally:
        web_process.terminate()
        web_process.join()
