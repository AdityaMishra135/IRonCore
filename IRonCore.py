import os
import asyncio
from dotenv import load_dotenv
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ChatPermissions
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

# Load environment variables
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_USER_ID = os.getenv("ADMIN_USER_ID")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    user = update.effective_user
    keyboard = [
        [
            InlineKeyboardButton("ℹ️ Info", callback_data="info"),
            InlineKeyboardButton("➕ Add to Group", callback_data="add_to_group"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_html(
        rf"Hi {user.mention_html()}! 👋",
        reply_markup=reply_markup,
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button presses."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "info":
        await query.edit_message_text(
            text="🤖 <b>Bot Information</b>\n\n"
                 "This is a basic Telegram bot created with python-telegram-bot library.\n\n"
                 "Features:\n"
                 "- /start command\n"
                 "- Info button\n"
                 "- Add to group button\n\n"
                 "Created by you!",
            parse_mode="HTML"
        )
    elif query.data == "add_to_group":
        await query.edit_message_text(
            text="To add this bot to your group:\n\n"
                 "1. Go to your group\n"
                 "2. Click on group name\n"
                 "3. Select 'Add members'\n"
                 "4. Search for this bot's username\n"
                 "5. Add it to the group\n\n"
                 "Note: Make sure to make me admin if you want me to work properly!",
            parse_mode="HTML"
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /help is issued."""
    await update.message.reply_text("Type /start to begin!")

async def main():
    """Start the bot with proper async handling."""
    application = None
    try:
        # Create and configure application
        application = ApplicationBuilder().token(TOKEN).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CallbackQueryHandler(button))
        
        print("Bot starting...")
        await application.initialize()
        await application.start()
        print("Bot running...")
        
        # Keep the application running
        await application.updater.start_polling()
        await idle()
        
    except Exception as e:
        print(f"Bot failed: {e}")
    finally:
        if application:
            print("Shutting down bot...")
            await application.stop()
            await application.shutdown()
        print("Bot stopped.")

def run_bot():
    """Run the bot with proper event loop handling."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()

if __name__ == "__main__":
    run_bot()
