import os
import asyncio
import nest_asyncio
from telegram import Update, ChatPermissions
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# Fix for nested event loops (e.g., on Render.com)
nest_asyncio.apply()

TOKEN = os.getenv("TOKEN")

# ===== CONFIGURATION =====
YOUR_TELEGRAM_ID = 911386241  # Replace with your actual Telegram user ID
# =========================

# Dictionary to track known usernames {user_id: username}
known_usernames = {}

# Helper: Check if username changed
def has_username_changed(user_id, new_username):
    return known_usernames.get(user_id) != new_username

# Helper: Check if user is admin or owner
async def is_admin(chat_id, user_id, context):
    if user_id == YOUR_TELEGRAM_ID:
        return True
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        return member.status in ['administrator', 'creator']
    except Exception as e:
        print(f"[ERROR] Could not check admin status: {e}")
        return False

# Command: /start - Activates the bot
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

    # Try to get from_user or sender_chat
    if reply.from_user:
        user = reply.from_user
    elif reply.sender_chat:
        user = reply.sender_chat
    else:
        await update.message.reply_text("❌ Unable to retrieve user info.")
        return

    # Build response dynamically based on what type of user it is
    info = (
        f"👤 <b>User Info</b>\n"
        f"ID: {user.id}\n"
        f"First Name: {getattr(user, 'first_name', 'N/A')}\n"
        f"Last Name: {getattr(user, 'last_name', 'N/A')}\n"
        f"Username: @{user.username if getattr(user, 'username', None) else 'No username'}\n"
        f"Is Bot: {'Yes' if getattr(user, 'is_bot', False) else 'No'}\n"
        f"Type: {getattr(user, 'type', 'Unknown')}\n"
        f"Language Code: {getattr(user, 'language_code', 'Unknown')}"
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
            f"🔄 User @{old} has changed their username to @{new}!",
            parse_mode='HTML'
        )

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

# === ADMIN-ONLY COMMANDS ===

async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    chat_id = chat.id

    if not await is_admin(chat_id, user.id, context):
        await update.message.reply_text("❌ This command requires admin rights.")
        return

    if not context.args or len(context.args) != 1:
        return await update.message.reply_text("❌ Usage: /mute <user_id>")

    try:
        target_id = int(context.args[0])
    except ValueError:
        return await update.message.reply_text("❌ Invalid user ID.")

    await context.bot.restrict_chat_member(
        chat.id, target_id, ChatPermissions(can_send_messages=False)
    )
    await update.message.reply_text(f"🔇 User `{target_id}` has been muted.")

async def unmute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if not await is_admin(chat.id, user.id, context):
        await update.message.reply_text("❌ This command requires admin rights.")
        return

    if not context.args or len(context.args) != 1:
        return await update.message.reply_text("❌ Usage: /unmute <user_id>")

    try:
        target_id = int(context.args[0])
    except ValueError:
        return await update.message.reply_text("❌ Invalid user ID.")

    await context.bot.restrict_chat_member(
        chat.id, target_id, ChatPermissions(can_send_messages=True)
    )
    await update.message.reply_text(f"🔊 User `{target_id}` has been unmuted.")

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if not await is_admin(chat.id, user.id, context):
        await update.message.reply_text("❌ This command requires admin rights.")
        return

    if not context.args:
        return await update.message.reply_text("❌ Usage: /ban <user_id> [reason]")

    try:
        target_id = int(context.args[0])
        reason = " ".join(context.args[1:]) or "No reason provided"
    except ValueError:
        return await update.message.reply_text("❌ Invalid user ID.")

    await context.bot.ban_chat_member(chat.id, target_id)
    await update.message.reply_text(f"🚫 User `{target_id}` has been banned. Reason: {reason}")

async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if not await is_admin(chat.id, user.id, context):
        await update.message.reply_text("❌ This command requires admin rights.")
        return

    if not context.args or len(context.args) != 1:
        return await update.message.reply_text("❌ Usage: /unban <user_id>")

    try:
        target_id = int(context.args[0])
    except ValueError:
        return await update.message.reply_text("❌ Invalid user ID.")

    await context.bot.unban_chat_member(chat.id, target_id)
    await update.message.reply_text(f"✅ User `{target_id}` has been unbanned.")

async def promote_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if not await is_admin(chat.id, user.id, context):
        await update.message.reply_text("❌ This command requires admin rights.")
        return

    if not context.args or len(context.args) != 1:
        return await update.message.reply_text("❌ Usage: /promote <user_id>")

    try:
        target_id = int(context.args[0])
    except ValueError:
        return await update.message.reply_text("❌ Invalid user ID.")

    await context.bot.promote_chat_member(chat.id, target_id)
    await update.message.reply_text(f"🌟 User `{target_id}` has been promoted to admin.")

async def demote_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if not await is_admin(chat.id, user.id, context):
        await update.message.reply_text("❌ This command requires admin rights.")
        return

    if not context.args or len(context.args) != 1:
        return await update.message.reply_text("❌ Usage: /demote <user_id>")

    try:
        target_id = int(context.args[0])
    except ValueError:
        return await update.message.reply_text("❌ Invalid user ID.")

    await context.bot.promote_chat_member(
        chat.id,
        target_id,
        ChatPermissions(can_manage_chat=False, can_invite_users=False, can_restrict_members=False)
    )
    await update.message.reply_text(f"🔻 User `{target_id}` has been demoted.")

# Global error handler
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    exception = context.error
    if isinstance(exception, Exception):
        print(f"Error occurred: {exception}")
    if "Conflict" in str(exception):
        print("⚠️ Conflict detected: Another instance of the bot may be running.")
        if update and getattr(update, "message", None):
            await update.message.reply_text(
                "⚠️ Conflict: Another instance of the bot is already running. "
                "Make sure only one instance is active."
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

    # Admin-only commands
    app.add_handler(CommandHandler("mute", mute_user))
    app.add_handler(CommandHandler("unmute", unmute_user))
    app.add_handler(CommandHandler("ban", ban_user))
    app.add_handler(CommandHandler("unban", unban_user))
    app.add_handler(CommandHandler("promote", promote_user))
    app.add_handler(CommandHandler("demote", demote_user))

    # Register event handlers
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, greet_new_member))
    app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, farewell_member))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, detect_username_change))

    # Register error handler
    app.add_error_handler(error_handler)

    print("✅ Bot started successfully!")
    await app.run_polling()

if __name__ == '__main__':
    asyncio.run(main())
