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
    MessageHandler,
    ContextTypes,
    filters
)

# Load environment variables
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_USER_ID = os.getenv("ADMIN_USER_ID")

# Helper functions
async def is_admin_or_owner(chat_id, user_id, context):
    """Check if user is admin or owner"""
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        return member.status in ['administrator', 'creator']
    except Exception as e:
        print(f"Admin check failed: {e}")
        return False

async def get_target_user(update, context):
    """Extract target user from message"""
    try:
        if update.message.reply_to_message:
            return update.message.reply_to_message.from_user.id
        elif context.args:
            return int(context.args[0])
        else:
            await update.message.reply_text("Please reply to a user or provide a user ID")
            return None
    except (ValueError, IndexError):
        await update.message.reply_text("Invalid user ID format")
        return None

# Command handlers
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

async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    chat_id = chat.id
    if not await is_admin_or_owner(chat_id, user.id, context):
        return await update.message.reply_text("❌ This command requires admin rights.")
    target_id = await get_target_user(update, context)
    if not target_id:
        return
    try:
        await context.bot.restrict_chat_member(
            chat_id, target_id, ChatPermissions(can_send_messages=False)
        )
        await update.message.reply_text(f"🔇 User `{target_id}` has been muted.")
    except Exception as e:
        await update.message.reply_text("⚠️ Failed to mute user.")
        print(f"[ERROR] Mute failed: {e}")

# [Include all your other command handlers here...]

# Main function
async def main():
    """Start the bot."""
    try:
        application = ApplicationBuilder().token(TOKEN).build()

        # Add command handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("mute", mute_user))
        # [Add all your other command handlers here...]
        
        # Add callback query handler for buttons
        application.add_handler(CallbackQueryHandler(button))

        print("Bot is running...")
        await application.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        print(f"Failed to start bot: {e}")

if __name__ == "__main__":
    asyncio.run(main())
