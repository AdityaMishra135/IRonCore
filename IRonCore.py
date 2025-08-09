import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters
)
from fastapi import FastAPI
import uvicorn
import multiprocessing
import logging

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

# Telegram Bot Functions
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message with options"""
    keyboard = [
        [InlineKeyboardButton("➕ Add to Group", url=f"https://t.me/{context.bot.username}?startgroup=true")],
        [InlineKeyboardButton("ℹ️ Bot Info", callback_data="info")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🤖 Welcome to Group Manager Bot!\n\n"
        "Click below to add me to your group:",
        reply_markup=reply_markup
    )

async def new_chat_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle when bot is added to a group"""
    chat = update.effective_chat
    for member in update.message.new_chat_members:
        if member.id == context.bot.id:
            logger.info(f"Bot added to group: {chat.id}")
            
            try:
                # Try to upgrade to supergroup
                if chat.type == "group":
                    await chat.send_message(
                        "👋 I'll help manage this group!\n"
                        "Please make me an admin to unlock all features."
                    )
            except Exception as e:
                logger.error(f"Error in new_chat_members: {e}")

async def promote_to_supergroup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command to upgrade group to supergroup"""
    chat = update.effective_chat
    user = update.effective_user
    
    if chat.type == "group":
        try:
            # This will automatically upgrade to supergroup
            await context.bot.leave_chat(chat.id)
            await context.bot.send_message(
                user.id,
                f"✅ Group {chat.title} needs to be upgraded.\n"
                f"Please add me again to the new supergroup."
            )
        except Exception as e:
            logger.error(f"Error promoting to supergroup: {e}")
            await update.message.reply_text("❌ Failed to upgrade group")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button presses"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "info":
        await query.edit_message_text(
            "🤖 <b>Group Manager Bot</b>\n\n"
            "Features:\n"
            "- Auto group management\n"
            "- Admin tools\n"
            "- Spam protection\n\n"
            "Make me admin for full features!",
            parse_mode="HTML"
        )

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Log errors"""
    logger.error(f"Update {update} caused error {context.error}")

def run_bot():
    """Run Telegram bot with proper event loop management"""
    async def bot_main():
        app = ApplicationBuilder().token(TOKEN).build()
        
        # Add handlers
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("upgrade", promote_to_supergroup))
        app.add_handler(CallbackQueryHandler(button_handler))
        app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_chat_members))
        app.add_error_handler(error_handler)
        
        logger.info("🤖 Starting Telegram bot polling...")
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
