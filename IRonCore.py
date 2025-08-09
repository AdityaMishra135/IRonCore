import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
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

def main():
    """Start the bot."""
    # Create the Application
    application = Application.builder().token(TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    
    # Add callback query handler for buttons
    application.add_handler(CallbackQueryHandler(button))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()        await context.bot.restrict_chat_member(
            chat_id, target_id, ChatPermissions(can_send_messages=False)
        )
        await update.message.reply_text(f"🔇 User `{target_id}` has been muted.")
    except Exception as e:
        await update.message.reply_text("⚠️ Failed to mute user.")
        print(f"[ERROR] Mute failed: {e}")

async def unmute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            chat_id, target_id, ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_polls=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True
            )
        )
        await update.message.reply_text(f"🔊 User `{target_id}` has been unmuted.")
    except Exception as e:
        await update.message.reply_text("⚠️ Failed to unmute user.")
        print(f"[ERROR] Unmute failed: {e}")

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    chat_id = chat.id
    if not await is_admin_or_owner(chat_id, user.id, context):
        return await update.message.reply_text("❌ This command requires admin rights.")
    target_id = await get_target_user(update, context)
    if not target_id:
        return
    reason = " ".join(context.args[1:]) if len(context.args) > 1 else "No reason provided"
    try:
        await context.bot.ban_chat_member(chat_id, target_id)
        await update.message.reply_text(f"🚫 User `{target_id}` has been banned. Reason: {reason}")
    except Exception as e:
        await update.message.reply_text("⚠️ Failed to ban user.")
        print(f"[ERROR] Ban failed: {e}")

async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    chat_id = chat.id
    if not await is_admin_or_owner(chat_id, user.id, context):
        return await update.message.reply_text("❌ This command requires admin rights.")
    target_id = await get_target_user(update, context)
    if not target_id:
        return
    try:
        await context.bot.unban_chat_member(chat_id, target_id)
        await update.message.reply_text(f"✅ User `{target_id}` has been unbanned.")
    except Exception as e:
        await update.message.reply_text("⚠️ Failed to unban user.")
        print(f"[ERROR] Unban failed: {e}")

async def promote_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    chat_id = chat.id
    if not await is_admin_or_owner(chat_id, user.id, context):
        return await update.message.reply_text("❌ This command requires admin rights.")
    target_id = await get_target_user(update, context)
    if not target_id:
        return
    try:
        await context.bot.promote_chat_member(
            chat_id,
            target_id,
            can_manage_chat=True,
            can_delete_messages=True,
            can_manage_video_chats=True,
            can_restrict_members=True,
            can_promote_members=False,
            can_change_info=True,
            can_invite_users=True,
            can_pin_messages=True,
            is_anonymous=False
        )
        await update.message.reply_text(f"🌟 User `{target_id}` has been promoted to admin.")
    except Exception as e:
        await update.message.reply_text("⚠️ Failed to promote user.")
        print(f"[ERROR] Promote failed: {e}")

async def demote_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    chat_id = chat.id
    if not await is_admin_or_owner(chat_id, user.id, context):
        return await update.message.reply_text("❌ This command requires admin rights.")
    target_id = await get_target_user(update, context)
    if not target_id:
        return
    try:
        await context.bot.promote_chat_member(
            chat_id,
            target_id,
            can_manage_chat=False,
            can_delete_messages=False,
            can_manage_video_chats=False,
            can_restrict_members=False,
            can_promote_members=False,
            can_change_info=False,
            can_invite_users=False,
            can_pin_messages=False,
            is_anonymous=False
        )
        await update.message.reply_text(f"🔻 User `{target_id}` has been demoted.")
    except Exception as e:
        await update.message.reply_text("⚠️ Failed to demote user.")
        print(f"[ERROR] Demote failed: {e}")

# Global error handler
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    exception = context.error
    print(f"🚨 Error occurred: {exception}")
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

    # Register basic commands
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

    # Event handlers
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, greet_new_member))
    app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, farewell_member))

    # Register error handler
    app.add_error_handler(error_handler)

    print("✅ Bot started successfully!")
    await app.run_polling()

if __name__ == '__main__':
    asyncio.run(main())
