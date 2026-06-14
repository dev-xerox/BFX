import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Configuration
BOT_TOKEN = "8339587372:AAGjc-yDM6cyWjENqX1nt57v_L0ogigVUl4"
ALLOWED_USER_ID = 8584250537  # Your Telegram ID

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    if update.effective_user.id != ALLOWED_USER_ID:
        await update.message.reply_text("⛔ Access denied. You are not authorized to use this bot.")
        return
    await update.message.reply_text(
        "👋 Hello! I'm connected to Cosine AI.\n\n"
        "Send me any message and I'll respond using Cosine's capabilities.\n\n"
        "Use /help for available commands."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    if update.effective_user.id != ALLOWED_USER_ID:
        await update.message.reply_text("⛔ Access denied.")
        return
    await update.message.reply_text(
        "📚 Available commands:\n\n"
        "/start - Start the bot\n"
        "/help - Show this help message\n"
        "/status - Check bot status\n\n"
        "You can also just send any message and I'll respond!"
    )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPES):
    """Handle /status command"""
    if update.effective_user.id != ALLOWED_USER_ID:
        await update.message.reply_text("⛔ Access denied.")
        return
    await update.message.reply_text("✅ Bot is running and ready to receive messages.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all other messages"""
    user_id = update.effective_user.id
    
    if user_id != ALLOWED_USER_ID:
        await update.message.reply_text("⛔ Access denied. This bot is private.")
        logger.warning(f"Unauthorized access attempt from user ID: {user_id}")
        return
    
    user_message = update.message.text
    logger.info(f"Received message from user {user_id}: {user_message[:100]}...")
    
    # Simulate response for now - you'll integrate with Cosine API
    await update.message.reply_text(
        f"📨 Message received!\n\n"
        f"Your message: {user_message}\n\n"
        f"This bot is configured but not yet connected to Cosine API.\n"
        f"Integration code will be added here."
    )


def main():
    """Start the bot"""
    logger.info("Starting Telegram Bot...")
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Start polling
    logger.info("Bot is now running. Press Ctrl+C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()