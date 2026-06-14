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


def call_gemini(messages: list, api_key: str, tools: list = None) -> dict:
    """Call Gemini API with given messages and optional tools"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={api_key}"
    
    payload = {
        "contents": messages
    }
    
    if tools:
        payload["tools"] = tools
    
    payload["generationConfig"] = {
        "temperature": 0.9,
        "maxOutputTokens": 8192,
        "topP": 0.95,
        "topK": 40
    }
    
    headers = {"Content-Type": "application/json"}
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        return {"success": True, "data": response.json()}
    except Exception as e:
        return {"success": False, "error": str(e)}


def execute_google_search(query: str, api_key: str) -> str:
    """Execute Google Search via Gemini's built-in tool"""
    messages = [{
        "role": "user",
        "parts": [{"text": f"Найди актуальную информацию в интернете по запросу: {query}. Дай развёрнутый и точный ответ."}]
    }]
    
    tools = [{"google_search": {}}]
    
    result = call_gemini(messages, api_key, tools)
    
    if result["success"]:
        data = result["data"]
        if "candidates" in data:
            candidate = data["candidates"][0]
            
            # Check if model called a function
            if "content" in candidate:
                for part in candidate["content"]["parts"]:
                    if "functionCall" in part:
                        fc = part["functionCall"]
                        if fc["name"] == "google_search":
                            args = fc.get("args", {})
                            query_search = args.get("query", query)
                            return f"Поиск: {query_search}\n\nВыполняю поиск..."
                    elif "text" in part:
                        return part["text"]
            
            # Direct text response
            if "content" in candidate:
                for part in candidate["content"]["parts"]:
                    if "text" in part:
                        return part["text"]
        
        return "Не удалось получить результат поиска."
    else:
        return f"Ошибка поиска: {result.get('error', 'Unknown error')}"


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
        "/clear - Очистить историю разговора\n\n"
        "Просто напишите сообщение и я отвечу!"
    )


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /clear command"""
    if update.effective_user.id != ALLOWED_USER_ID:
        await update.message.reply_text("⛔ Access denied.")
        return
    
    user_conversations[update.effective_user.id] = []
    await update.message.reply_text("✅ История разговора очищена.")


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
    
    # Define tools for Gemini
    tools = [{"google_search": {}}]
    
    # Send "typing" indicator
    await update.message.reply_text("💭 Думаю...")
    
    # Try each API key
    response_text = None
    for api_key in GEMINI_API_KEYS:
        result = call_gemini(messages, api_key, tools)
        
        if result["success"]:
            data = result["data"]
            
            if "candidates" in data:
                candidate = data["candidates"][0]
                
                # Check for function calls
                if "content" in candidate:
                    for part in candidate["content"]["parts"]:
                        # Handle function call
                        if "functionCall" in part:
                            fc = part["functionCall"]
                            logger.info(f"Function call: {fc['name']}")
                            
                            if fc["name"] == "google_search":
                                query = fc.get("args", {}).get("query", "")
                                # Execute search and add to context
                                search_result = execute_google_search(query, api_key)
                                # Add search result to conversation
                                user_conversations[user_id].append({
                                    "role": "system",
                                    "content": f"[Поиск в интернете по запросу '{query}']"
                                })
                                # Add search tool result
                                messages.append({
                                    "role": "model",
                                    "parts": [{"functionCall": fc}]
                                })
                                messages.append({
                                    "role": "user",
                                    "parts": [{"text": search_result}]
                                })
                                
                                # Get final response with search context
                                result2 = call_gemini(messages, api_key, tools)
                                if result2["success"] and "candidates" in result2["data"]:
                                    candidate2 = result2["data"]["candidates"][0]
                                    for part2 in candidate2["content"]["parts"]:
                                        if "text" in part2:
                                            response_text = part2["text"]
                                            break
                                    if response_text:
                                        break
                        
                        # Handle function response
                        elif "functionResponse" in part:
                            logger.info(f"Function response received")
                        
                        # Direct text response
                        elif "text" in part:
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
    logger.info("Starting Gemini Telegram Bot with Web Search...")
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("clear", clear_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("Bot is running. Press Ctrl+C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()