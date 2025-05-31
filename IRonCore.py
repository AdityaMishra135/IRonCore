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
DEFAULT_GROUP_ID = -1002685452717  # Replace with your default group ID
OWNER_TELEGRAM_ID = 911386241       # For allowgroup/demote/etc if needed later
OWNER_USERNAME = "lRonHiide"         # Optional: for messages
# =========================

# Runtime data stores
allowed_group_ids = {DEFAULT_GROUP_ID}  # Start with your default group already allowed
banned_users = {}                        # {user_id: reason}
known_usernames = {}                     # {user_id: username}

# === OWNER COMMANDS (Still restricted to owner) ===

async def allow_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != OWNER_TELEGRAM_ID:
        await update.message.reply_text("🔒 Only the owner can add groups.")
        return

    if len(context.args) != 1:
        return await update.message.reply_text("❌ Usage: /allowgroup <group_id>")

    try:
        group_id = int(context.args[0])
    except ValueError:
        return await update.message.reply_text("❌ Invalid group ID.")

    if group_id in allowed_group_ids:
        return await update.message.reply_text(f"⚠️ Group `{group_id}` is already allowed.")

    allowed_group_ids.add(group_id)
    await update.message.reply_text(f"✅ Group `{group_id}` has been added.")
    print(f"[INFO] Allowed groups: {allowed_group_ids}")

async def remove_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != OWNER_TELEGRAM_ID:
        await update.message.reply_text("🔒 Only the owner can remove groups.")
        return

    if len(context.args) != 1:
        return await update.message.reply_text("❌ Usage: /removegroup <group_id>")

    try:
        group_id = int(context.args[0])
    except ValueError:
        return await update.message.reply_text("❌ Invalid group ID.")

    if group_id == DEFAULT_GROUP_ID:
        return await update.message.reply_text("🚫 Cannot remove the default group.")

    if group_id in allowed_group_ids:
        allowed_group_ids.remove(group_id)
        await update.message.reply_text(f"✅ Group `{group_id}` has been removed.")
    else:
        await update.message.reply_text(f"⚠️ Group `{group_id}` is not in the list.")

async def list_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != OWNER_TELEGRAM_ID:
        return await update.message.reply_text("🔒 Only the owner can view group list.")

    if not allowed_group_ids:
        return await update.message.reply_text("📋 No groups are currently allowed.")

    group_list = "\n".join(str(gid) for gid in allowed_group_ids)
    await update.message.reply_text(f"📋 Allowed Groups:\n```\n{group_list}\n```", parse_mode="MarkdownV2")

# === PUBLIC ADMIN FEATURES (Any user in allowed group can use) ===

async def activate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.id not in allowed_group_ids:
        return await update.message.reply_text(
            f"🔒 This group is not authorized.\n"
            f"Please contact @{OWNER_USERNAME} to allow this group first."
        )

    await update.message.reply_text("🤖 Bot activated! Use /help to see available commands.")

async def total_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.id not in allowed_group_ids:
        return await update.message.reply_text(
            f"🔒 This group is not authorized.\n"
            f"Please contact @{OWNER_USERNAME} to allow this group first."
        )

    count = await context.bot.get_chat_member_count(chat.id)
    await update.message.reply_text(f"👥 Total users in this group: {count}")

async def user_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.id not in allowed_group_ids:
        return await update.message.reply_text(
            f"🔒 This group is not authorized.\n"
            f"Please contact @{OWNER_USERNAME} to allow this group first."
        )

    reply = update.message.reply_to_message
    if not reply:
        await update.message.reply_text("❌ Please reply to a message to get user info.")
        return

    target_user = reply.from_user
    if not target_user:
        await update.message.reply_text("❌ Unable to retrieve user info.")
        return

    if target_user.is_deleted:
        await update.message.reply_text("💀 This user has a deleted account.")
        return

    info = (
        f"👤 <b>User Info</b>\n"
        f"ID: {target_user.id}\n"
        f"First Name: {target_user.first_name}\n"
        f"Last Name: {target_user.last_name or 'N/A'}\n"
        f"Username: @{target_user.username or 'No username'}\n"
        f"Is Bot: {'Yes' if target_user.is_bot else 'No'}\n"
        f"Language Code: {target_user.language_code or 'Unknown'}"
    )
    await update.message.reply_text(info, parse_mode="HTML")

# === GROUP ADMIN FEATURES (Anyone in allowed group can use) ===

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.id not in allowed_group_ids:
        return await update.message.reply_text(
            f"🔒 This bot cannot be used here. Contact @{OWNER_USERNAME} for access."
        )

    if not context.args:
        return await update.message.reply_text("❌ Usage: /ban <user_id> [reason]")

    try:
        target_id = int(context.args[0])
        reason = " ".join(context.args[1:]) or "No reason provided"
    except ValueError:
        return await update.message.reply_text("❌ Invalid user ID.")

    banned_users[target_id] = reason
    await context.bot.ban_chat_member(chat.id, target_id)
    await update.message.reply_text(f"🚫 User `{target_id}` has been banned. Reason: {reason}")

async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.id not in allowed_group_ids:
        return await update.message.reply_text(
            f"🔒 This bot cannot be used here. Contact @{OWNER_USERNAME} for access."
        )

    if not context.args or len(context.args) != 1:
        return await update.message.reply_text("❌ Usage: /unban <user_id>")

    try:
        target_id = int(context.args[0])
    except ValueError:
        return await update.message.reply_text("❌ Invalid user ID.")

    if target_id not in banned_users:
        return await update.message.reply_text("⚠️ This user isn't in the ban list.")

    del banned_users[target_id]
    await context.bot.unban_chat_member(chat.id, target_id)
    await update.message.reply_text(f"✅ User `{target_id}` has been unbanned.")

async def list_banned(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.id not in allowed_group_ids:
        return await update.message.reply_text(
            f"🔒 This bot cannot be used here. Contact @{OWNER_USERNAME} for access."
        )

    if not banned_users:
        return await update.message.reply_text("📋 No users are currently banned.")

    banned_list = "\n".join([f"{uid}: {reason}" for uid, reason in banned_users.items()])
    await update.message.reply_text(f"🚫 Banned Users:\n```\n{banned_list}\n```", parse_mode="MarkdownV2")

async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.id not in allowed_group_ids:
        return await update.message.reply_text(
            f"🔒 This bot cannot be used here. Contact @{OWNER_USERNAME} for access."
        )

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
    if chat.id not in allowed_group_ids:
        return await update.message.reply_text(
            f"🔒 This bot cannot be used here. Contact @{OWNER_USERNAME} for access."
        )

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

async def promote_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.id not in allowed_group_ids:
        return await update.message.reply_text(
            f"🔒 This bot cannot be used here. Contact @{OWNER_USERNAME} for access."
        )

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
    if chat.id not in allowed_group_ids:
        return await update.message.reply_text(
            f"🔒 This bot cannot be used here. Contact @{OWNER_USERNAME} for access."
        )

    if not context.args or len(context.args) != 1:
        return await update.message.reply_text("❌ Usage: /demote <user_id>")

    try:
        target_id = int(context.args[0])
    except ValueError:
        return await update.message.reply_text("❌ Invalid user ID.")

    await context.bot.promote_chat_member(
        chat.id, target_id,
        ChatPermissions(can_manage_chat=False, can_change_info=False, can_invite_users=False)
    )
    await update.message.reply_text(f"🔻 User `{target_id}` has been demoted.")

# === EVENTS ===

async def greet_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in allowed_group_ids:
        return

    for new_user in update.message.new_chat_members:
        welcome_msg = (
            f"👋 Welcome, {new_user.first_name}!\n"
            f"ID: {new_user.id}\n"
            f"Username: @{new_user.username or 'No username'}\n"
            f"Account Deleted: {'Yes' if new_user.is_deleted else 'No'}"
        )
        await update.message.reply_text(welcome_msg)

async def farewell_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in allowed_group_ids:
        return

    left_user = update.message.left_chat_member
    if left_user:
        farewell_msg = (
            f"😢 {left_user.first_name} has left the group.\n"
            f"ID: {left_user.id}\n"
            f"Username: @{left_user.username or 'No username'}"
        )
        await update.message.reply_text(farewell_msg)

async def detect_username_change(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in allowed_group_ids:
        return

    user = update.effective_user
    if not user:
        return

    if known_usernames.get(user.id) != user.username:
        old = known_usernames.get(user.id, "None")
        new = user.username or "Deleted username"
        await update.message.reply_text(
            f"🔄 User @{old} has changed their username to @{new}!"
        )

    known_usernames[user.id] = user.username or ""

# Global error handler
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    exception = context.error
    if isinstance(exception, Exception):
        print(f"🚨 Error occurred: {exception}")
    if "Conflict" in str(exception):
        print("⚠️ Conflict detected: Another instance of the bot may be running.")
        if update and getattr(update, "message", None):
            await update.message.reply_text(
                "⚠️ Conflict: Another instance of the bot is already running. "
                "Make sure only one instance is active."
            )

# === MAIN ===

async def main():
    try:
        app = ApplicationBuilder().token(TOKEN).build()
    except Exception as e:
        print(f"Failed to initialize bot: {e}")
        return

    # Owner-only commands
    app.add_handler(CommandHandler("allowgroup", allow_group))
    app.add_handler(CommandHandler("removegroup", remove_group))
    app.add_handler(CommandHandler("listgroups", list_groups))

    # Public commands (anyone in allowed group can use)
    app.add_handler(CommandHandler("activate", activate))
    app.add_handler(CommandHandler("totalusers", total_users))
    app.add_handler(CommandHandler("userinfo", user_info))
    app.add_handler(CommandHandler("ban", ban_user))
    app.add_handler(CommandHandler("unban", unban_user))
    app.add_handler(CommandHandler("listbanned", list_banned))
    app.add_handler(CommandHandler("mute", mute_user))
    app.add_handler(CommandHandler("unmute", unmute_user))
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
