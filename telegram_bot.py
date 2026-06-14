import os
import logging
import json
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Configuration
BOT_TOKEN = "8339587372:AAGjc-yDM6cyWjENqX1nt57v_L0ogigVUl4"
ALLOWED_USER_ID = 8584250537
GEMINI_API_KEYS = [
    "AIzaSyAoKZdSuIoGk8DvGYA-PPkpYqrR9k8AxaY",
    "AIzaSyDBCrkfefaNWSTislpi9_6s_TwUTyTidxU"
]
MODEL_NAME = "gemini-2.5-flash"

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Conversation history per user
user_conversations = {}


def call_gemini(messages: list, api_key: str) -> dict:
    """Call Gemini API with given messages"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={api_key}"
    
    payload = {
        "contents": messages,
        "tools": [
            {"google_search": {}},
            {"google_search_retrieval": {}}
        ],
        "generationConfig": {
            "temperature": 0.9,
            "maxOutputTokens": 8192,
            "topP": 0.95,
            "topK": 40
        }
    }
    
    headers = {"Content-Type": "application/json"}
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        result = response.json()
        
        if "candidates" in result:
            return {"success": True, "data": result}
        elif "error" in result:
            return {"success": False, "error": result["error"].get("message", "Unknown error")}
        else:
            return {"success": False, "error": str(result)}
            
    except Exception as e:
        return {"success": False, "error": str(e)}


def format_messages(conversation_history: list) -> list:
    """Format conversation history for Gemini API"""
    formatted = []
    for msg in conversation_history:
        role = "user" if msg["role"] == "user" else "model"
        formatted.append({
            "role": role,
            "parts": [{"text": msg["content"]}]
        })
    return formatted


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    if update.effective_user.id != ALLOWED_USER_ID:
        await update.message.reply_text("⛔ Access denied.")
        return
    
    user_conversations[update.effective_user.id] = []
    
    await update.message.reply_text(
        "👋 Привет! Я Gemini Agent.\n\n"
        "Могу искать информацию в интернете 🔍 и отвечать на ваши вопросы.\n\n"
        "Просто напишите сообщение!"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    if update.effective_user.id != ALLOWED_USER_ID:
        await update.message.reply_text("⛔ Access denied.")
        return
    
    await update.message.reply_text(
        "📚 Команды:\n\n"
        "/start - Перезапустить бота\n"
        "/clear - Очистить историю разговора\n"
        "/search <запрос> - Поиск в интернете\n\n"
        "Просто напишите сообщение и я отвечу!"
    )


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /clear command"""
    if update.effective_user.id != ALLOWED_USER_ID:
        await update.message.reply_text("⛔ Access denied.")
        return
    
    user_conversations[update.effective_user.id] = []
    await update.message.reply_text("✅ История разговора очищена.")


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /search command"""
    if update.effective_user.id != ALLOWED_USER_ID:
        await update.message.reply_text("⛔ Access denied.")
        return
    
    query = " ".join(context.args) if context.args else ""
    
    if not query:
        await update.message.reply_text("⚠️ Укажите поисковый запрос: /search <ваш запрос>")
        return
    
    await update.message.reply_text(f"🔍 Ищу: {query}...")
    
    messages = [{
        "role": "user",
        "parts": [{"text": f"Найди информацию в интернете по запросу: {query}. Дай развёрнутый ответ."}]
    }]
    
    for api_key in GEMINI_API_KEYS:
        result = call_gemini(messages, api_key)
        if result["success"]:
            candidate = result["data"]["candidates"][0]
            response_text = candidate["content"]["parts"][0]["text"]
            await update.message.reply_text(response_text[:4096])
            return
        else:
            logger.warning(f"API key failed: {result.get('error', 'Unknown error')}")
    
    await update.message.reply_text("❌ Не удалось выполнить поиск. Попробуйте позже.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all messages"""
    user_id = update.effective_user.id
    
    if user_id != ALLOWED_USER_ID:
        await update.message.reply_text("⛔ Access denied.")
        return
    
    user_message = update.message.text
    logger.info(f"Message from user {user_id}: {user_message[:50]}...")
    
    # Initialize conversation if needed
    if user_id not in user_conversations:
        user_conversations[user_id] = []
    
    # Add user message to history
    user_conversations[user_id].append({
        "role": "user",
        "content": user_message
    })
    
    # Format messages for API
    messages = format_messages(user_conversations[user_id])
    
    # Send "typing" indicator
    await update.message.reply_text("💭 Думаю...")
    
    # Try each API key
    response_text = None
    for api_key in GEMINI_API_KEYS:
        result = call_gemini(messages, api_key)
        
        if result["success"]:
            candidate = result["data"]["candidates"][0]
            
            # Check if model wants to use tools
            if "content" in candidate and "parts" in candidate["content"]:
                for part in candidate["content"]["parts"]:
                    if "text" in part:
                        response_text = part["text"]
                        break
            
            if response_text:
                break
        else:
            logger.warning(f"API key failed: {result.get('error', 'Unknown error')}")
    
    if response_text:
        # Add assistant response to history
        user_conversations[user_id].append({
            "role": "assistant",
            "content": response_text
        })
        
        # Send response (split if too long)
        if len(response_text) > 4096:
            for i in range(0, len(response_text), 4096):
                await update.message.reply_text(response_text[i:i+4096])
        else:
            await update.message.reply_text(response_text)
    else:
        await update.message.reply_text(
            "❌ Произошла ошибка при генерации ответа.\n"
            "Попробуйте ещё раз или используйте /clear для сброса истории."
        )


def main():
    """Start the bot"""
    logger.info("Starting Gemini Telegram Bot...")
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("clear", clear_command))
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("Bot is running. Press Ctrl+C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()