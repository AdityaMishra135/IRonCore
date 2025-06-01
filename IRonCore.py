import os
import asyncio
import nest_asyncio
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# Apply nest_asyncio to avoid event loop issues (especially on Render)
nest_asyncio.apply()

TOKEN = os.getenv("TOKEN")

# Dictionary to track known usernames {user_id: username}
known_usernames = {}

# Helper: Check if username changed
def has_username_changed(user_id, new_username):
    if user_id in known_usernames:
        return known_usernames[user.id] != new_username
    return False

# Command: /activate - Activates the bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Bot activated! Use /help to see available commands.")

# Command: /totalusers - Show total number of users in the chat
async def total_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    count = await context.bot.get_chat_member_count(chat_id)
    await update.message.reply_text(f"👥 Total users in this group: {count}")

# Command: /userinfo - Show details about a replied-to user
async def user_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply = update.message.reply_to_message
    if not reply:
        await update.message.reply_text("❌ Please reply to a message to get user info.")
        return

    user = reply.from_user
    if not user:
        await update.message.reply_text("❌ Unable to retrieve user info.")
        return

    # Check if account is deleted
    if user.is_deleted:
        await update.message.reply_text("💀 This user has a deleted account.")
        return

    # Build response
    info = (
        f"👤 <b>User Info</b>\n"
        f"ID: {user.id}\n"
        f"First Name: {user.first_name}\n"
        f"Last Name: {user.last_name or 'N/A'}\n"
        f"Username: @{user.username if user.username else 'No username'}\n"
        f"Is Bot: {'Yes' if user.is_bot else 'No'}\n"
        f"Language Code: {user.language_code or 'Unknown'}"
    )
    await update.message.reply_text(info, parse_mode='HTML')

# Handler: Detect username changes in real-time
async def detect_username_change(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user:
        return

    if has_username_changed(user.id, user.username):
        old = known_usernames.get(user.id, "None")
        new = user.username or "Deleted username"
        await update.message.reply_text(
            f"🔄 User @{old} has changed their username to @{new}!"
        )

    # Update known username
    known_usernames[user.id] = user.username or ""

# Handler: Detect new member joining
async def greet_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for new_user in update.message.new_chat_members:
        welcome_msg = (
            f"👋 Welcome, {new_user.first_name}!\n"
            f"ID: {new_user.id}\n"
            f"Username: @{new_user.username if new_user.username else 'No username'}\n"
            f"Account Deleted: {'Yes' if new_user.is_deleted else 'No'}"
        )
        await update.message.reply_text(welcome_msg)

# Handler: Detect user leaving
async def farewell_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    left_user = update.message.left_chat_member
    if left_user:
        farewell_msg = (
            f"😢 {left_user.first_name} has left the group.\n"
            f"ID: {left_user.id}\n"
            f"Username: @{left_user.username if left_user.username else 'No username'}"
        )
        await update.message.reply_text(farewell_msg)

# Global error handler
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    exception = context.error
    if isinstance(exception, Exception):
        print(f"Error occurred: {exception}")
    if "Conflict" in str(exception):
        await update.message.reply_text(
            "⚠️ Conflict detected: Another instance of this bot may be running. "
            "Please ensure only one instance is active."
        )

# Main function
async def main():
    try:
        app = ApplicationBuilder().token(TOKEN).build()
    except Exception as e:
        print(f"Failed to initialize bot: {e}")
        return

    # Register commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("totalusers", total_users))
    app.add_handler(CommandHandler("userinfo", user_info))

    # Register event handlers
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, greet_new_member))
    app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, farewell_member))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, detect_username_change))
    app.add_error_handler(error_handler)

    print("✅ Bot started successfully!")
    await app.run_polling()

if __name__ == '__main__':
    asyncio.run(main())
