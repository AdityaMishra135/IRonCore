import os
from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

async def auto_upgrade_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.reply_text("🔄 Auto-upgrading group...")
        await context.bot.leave_chat(update.effective_chat.id)
    except Exception as e:
        await update.message.reply_text(f"⚠️ Upgrade failed: {e}")

async def is_group_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        member = await update.effective_chat.get_member(update.effective_user.id)
        return member.status in ("administrator", "creator")
    except Exception:
        return False

async def get_target_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Robust user targeting with exact username matching"""
    try:
        # Case 1: Command with reply
        if update.message.reply_to_message:
            return update.message.reply_to_message.from_user

        # Case 2: Command with argument
        if not context.args:
            await update.message.reply_text(
                "🔍 <b>How to target users:</b>\n\n"
                "1. Reply to user's message with /command\n"
                "2. /command @username (case sensitive)\n"
                "3. /command 123456789 (user ID)\n\n"
                "<i>Note: Usernames must match exactly</i>",
                parse_mode="HTML"
            )
            return None

        target = context.args[0].strip()
        
        # Exact username matching (case sensitive)
        if target.startswith('@'):
            target = target[1:]  # Remove @
            async for member in context.bot.get_chat_members(update.effective_chat.id):
                if member.user.username and member.user.username == target:
                    return member.user
        
        # Numeric ID fallback
        if target.isdigit():
            try:
                member = await context.bot.get_chat_member(
                    chat_id=update.effective_chat.id,
                    user_id=int(target)
                )
                return member.user
            except Exception:
                pass
        
        # Final attempt with ID string match
        async for member in context.bot.get_chat_members(update.effective_chat.id):
            if str(member.user.id) == target:
                return member.user

        await update.message.reply_text(
            f"❌ <b>User not found</b>\n\n"
            f"No exact match for '@{target}'.\n"
            f"Try using:\n"
            f"1. Their exact @username\n"
            f"2. Their numeric ID\n"
            f"3. Reply to their message",
            parse_mode="HTML"
        )
        return None

    except Exception as e:
        logger.error(f"Target error: {str(e)}", exc_info=True)
        await update.message.reply_text(
            "⚠️ <b>Targeting Error</b>\n\n"
            "Please try:\n"
            "1. Replying to the user's message\n"
            "2. Using their exact @username\n"
            "3. Using their numeric ID",
            parse_mode="HTML"
        )
        return None


def setup_group_handlers(app):
    app.add_handler(MessageHandler(
        filters.StatusUpdate.NEW_CHAT_MEMBERS,
        new_chat_members
    ))
