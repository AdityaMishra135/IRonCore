import os
import asyncio
import nest_asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

nest_asyncio.apply()

TOKEN = os.getenv("TOKEN")

# === MENU HANDLERS ===

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    menu = (
        "👋 Welcome to the Bot!\n\n"
        "📌 *Main Menu*:\n"
        "1️⃣ /commands - List all available commands\n"
        "2️⃣ /ownerinfo - View Owner Info\n"
        "3️⃣ /botinfo - About This Bot\n"
        "4️⃣ /help - Help & Support\n"
    )
    await update.message.reply_text(menu, parse_mode="MarkdownV2")

async def list_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    commands = (
        "🛠 Available Commands:\n"
        "/start - Show main menu\n"
        "/commands - Show this list\n"
        "/ownerinfo - View owner details\n"
        "/botinfo - Learn about this bot\n"
        "/help - Get help with usage"
    )
    await update.message.reply_text(commands)

async def owner_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    info = (
        "🧑‍💼 Owner Info:\n"
        "Owner: Aditya Mishra\n"
        "Telegram: @lRonHiide\n"
        "Status: Verified Bot Developer"
    )
    await update.message.reply_text(info)

async def bot_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    info = (
        "🤖 Bot Info:\n"
        "Name: IRonCore Bot\n"
        "Version: 1.0\n"
        "Purpose: Group Admin Tools\n"
        "Built With: Python + python-telegram-bot"
    )
    await update.message.reply_text(info)

async def help_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "❓ Need Help?\n\n"
        "You can use the following commands:\n"
        "/start - Show main menu\n"
        "/commands - See full command list\n"
        "/help - This message\n"
        "\n"
        "If you're an admin:\n"
        "You can also use /ban, /mute, etc.\n"
        "Contact @lRonHiide if you need support."
    )
    await update.message.reply_text(help_text)

# === MAIN FUNCTION ===

async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    # Register command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("commands", list_commands))
    app.add_handler(CommandHandler("ownerinfo", owner_info))
    app.add_handler(CommandHandler("botinfo", bot_info))
    app.add_handler(CommandHandler("help", help_info))

    print("✅ Bot started successfully!")
    await app.run_polling()

if __name__ == '__main__':
    asyncio.run(main())
