import os
from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

async def new_chat_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle new members including bot itself"""
    if any(member.id == context.bot.id for member in update.message.new_chat_members):
        if update.effective_chat.type == "group":
            await auto_upgrade_group(update, context)


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
    """Complete user targeting solution"""
    try:
        # Case 1: Command with reply
        if update.message.reply_to_message:
            return update.message.reply_to_message.from_user

        # Case 2: No arguments
        if not context.args:
            await update.message.reply_text(
                "🔍 <b>Usage:</b>\n"
                "1. Reply to user's message with /command\n"
                "2. /command @username\n"
                "3. /command 123456789",
                parse_mode="HTML"
            )
            return None

        target = context.args[0].strip()
        
        # Case 3: Username mention (@username)
        if target.startswith('@'):
            username = target[1:].lower()
            async for member in context.bot.get_chat_members(update.effective_chat.id):
                if member.user.username and member.user.username.lower() == username:
                    return member.user
            await update.message.reply_text(f"❌ User {target} not found in this chat")
            return None

        # Case 4: Numeric ID
        if target.isdigit():
            try:
                member = await context.bot.get_chat_member(
                    chat_id=update.effective_chat.id,
                    user_id=int(target)
                )
                return member.user
            except Exception:
                await update.message.reply_text(f"❌ User ID {target} not found")
                return None

        # Case 5: Fallback (try both username and ID)
        async for member in context.bot.get_chat_members(update.effective_chat.id):
            if (member.user.username and target.lower() in member.user.username.lower()) or str(member.user.id) == target:
                return member.user

        await update.message.reply_text(f"❌ No matches found for '{target}'")
        return None

    except Exception as e:
        logger.error(f"Target error: {e}")
        await update.message.reply_text("⚠️ Error processing your request")
        return None



def setup_group_handlers(app):
    app.add_handler(MessageHandler(
        filters.StatusUpdate.NEW_CHAT_MEMBERS,
        new_chat_members
    ))
