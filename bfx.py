#!/usr/bin/env python3
"""
BFX — Мощный ИИ-агент
Интерфейс в стиле Kiro (kiro.dev)
Поддерживаемые провайдеры: ChatGPT, Claude, Gemini, Grok, OpenRouter, DeepSeek, Groq, Nvidia, HuggingFace, GitHub
Инструменты: Веб-Поиск, Терминал, Веб-Фетч, Firecrawl API
"""

import os
import sys
import json
import subprocess
import requests
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

try:
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.prompt import Prompt
    from rich.table import Table
    from rich.syntax import Syntax
    from rich import print as rprint
    from rich.theme import Theme
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

try:
    from duckduckgo_search import DDGS
    HAS_DDG = True
except ImportError:
    HAS_DDG = False

# ─── Конфигурация ───────────────────────────────────────────────
load_dotenv()

PROVIDERS = {
    "chatgpt": {
        "api_key": os.getenv("OPENAI_API_KEY", ""),
        "model": os.getenv("OPENAI_MODEL", "gpt-5.4"),
        "endpoint": "https://api.openai.com/v1/chat/completions",
    },
    "claude": {
        "api_key": os.getenv("ANTHROPIC_API_KEY", ""),
        "model": os.getenv("ANTHROPIC_MODEL", "claude-opus-4-7"),
        "endpoint": "https://api.anthropic.com/v1/messages",
    },
    "gemini": {
        "api_key": os.getenv("GOOGLE_API_KEY", ""),
        "model": os.getenv("GOOGLE_MODEL", "gemini-3-pro-preview"),
        "endpoint": "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
    },
    "grok": {
        "api_key": os.getenv("XAI_API_KEY", ""),
        "model": os.getenv("XAI_MODEL", "grok-3"),
        "endpoint": "https://api.x.ai/v1/chat/completions",
    },
    "openrouter": {
        "api_key": os.getenv("OPENROUTER_API_KEY", ""),
        "model": os.getenv("OPENROUTER_MODEL", "openai/gpt-5.4"),
        "endpoint": "https://openrouter.ai/api/v1/chat/completions",
    },
    "deepseek": {
        "api_key": os.getenv("DEEPSEEK_API_KEY", ""),
        "model": os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        "endpoint": "https://api.deepseek.com/v1/chat/completions",
    },
    "groq": {
        "api_key": os.getenv("GROQ_API_KEY", ""),
        "model": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        "endpoint": "https://api.groq.com/openai/v1/chat/completions",
    },
    "nvidia": {
        "api_key": os.getenv("NVIDIA_API_KEY", ""),
        "model": os.getenv("NVIDIA_MODEL", "meta/llama-3.1-405b-instruct"),
        "endpoint": "https://integrate.api.nvidia.com/v1/chat/completions",
    },
    "huggingface": {
        "api_key": os.getenv("HUGGINGFACE_API_KEY", ""),
        "model": os.getenv("HUGGINGFACE_MODEL", "meta-llama/Llama-3.3-70B-Instruct"),
        "endpoint": "https://api-inference.huggingface.co/models/{model}/v1/chat/completions",
    },
    "github": {
        "api_key": os.getenv("GITHUB_TOKEN", ""),
        "model": os.getenv("GITHUB_MODEL", "openai/gpt-5.4"),
        "endpoint": "https://models.inference.ai.azure.com/chat/completions",
    },
}

SYSTEM_PROMPT = """Ты — BFX, мощный ИИ-ассистент. Ты можешь:
- Искать информацию в интернете
- Выполнять команды в терминале
- Загружать и анализировать веб-страницы
- Использовать Firecrawl для глубокого поиска
Отвечай кратко и по делу. Используй markdown для форматирования."""

# ─── Утилиты ────────────────────────────────────────────────────
def get_console():
    if HAS_RICH:
        return Console()
    return None

def print_banner():
    banner = """
╔══════════════════════════════════════════╗
║          🤖  BFX AI Agent  🤖           ║
║     Мощный ИИ-агент нового поколения     ║
╚══════════════════════════════════════════╝
"""
    if HAS_RICH:
        console = get_console()
        console.print(Panel(banner.strip(), style="bold cyan", border_style="cyan"))
    else:
        print(banner)

def print_help():
    if HAS_RICH:
        table = Table(title="📖 Доступные команды")
        table.add_column("Команда", style="cyan", no_wrap=True)
        table.add_column("Описание", style="white")
        table.add_row("/help", "Показать эту справку")
        table.add_row("/clear", "Очистить историю чата")
        table.add_row("/provider <name>", "Сменить провайдера (chatgpt/claude/gemini/grok/openrouter/deepseek/groq/nvidia/huggingface/github)")
        table.add_row("/model <name>", "Сменить модель")
        table.add_row("/search <query>", "Веб-поиск")
        table.add_row("/exec <command>", "Выполнить команду в терминале")
        table.add_row("/fetch <url>", "Загрузить веб-страницу")
        table.add_row("/firecrawl <url>", "Firecrawl скрейпинг")
        table.add_row("/config", "Показать текущую конфигурацию")
        table.add_row("/quit", "Выйти")
        console = get_console()
        console.print(table)
    else:
        print("""
Доступные команды:
  /help              - Показать справку
  /clear             - Очистить историю
  /provider <name>   - Сменить провайдера
  /model <name>      - Сменить модель
  /search <query>    - Веб-поиск
  /exec <command>    - Выполнить команду
  /fetch <url>       - Загрузить страницу
  /firecrawl <url>   - Firecrawl скрейпинг
  /config            - Конфигурация
  /quit              - Выйти
""")

# ─── Инструменты ────────────────────────────────────────────────
def web_search(query: str, max_results: int = 5) -> str:
    """Веб-поиск через DuckDuckGo"""
    if HAS_DDG:
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
                if not results:
                    return "Ничего не найдено."
                output = []
                for i, r in enumerate(results, 1):
                    output.append(f"{i}. {r.get('title', '')}\n   {r.get('href', '')}\n   {r.get('body', '')}")
                return "\n\n".join(output)
        except Exception as e:
            return f"Ошибка поиска: {e}"
    else:
        return "Модуль duckduckgo-search не установлен. pip install duckduckgo-search"

def terminal_exec(command: str) -> str:
    """Выполнение команды в терминале"""
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=30
        )
        output = []
        if result.stdout:
            output.append(f"STDOUT:\n{result.stdout}")
        if result.stderr:
            output.append(f"STDERR:\n{result.stderr}")
        output.append(f"Exit code: {result.returncode}")
        return "\n".join(output)
    except subprocess.TimeoutExpired:
        return "Таймаут выполнения (30с)"
    except Exception as e:
        return f"Ошибка: {e}"

def web_fetch(url: str) -> str:
    """Загрузка веб-страницы"""
    try:
        headers = {"User-Agent": "BFX-AI-Agent/1.0"}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        import re
        text = re.sub(r'<[^>]+>', ' ', response.text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text[:3000]
    except Exception as e:
        return f"Ошибка загрузки: {e}"

def firecrawl_scrape(url: str) -> str:
    """Firecrawl API для глубокого скрейпинга"""
    api_key = os.getenv("FIRECRAWL_API_KEY", "")
    if not api_key:
        return "FIRECRAWL_API_KEY не установлен в .env"
    try:
        response = requests.post(
            "https://api.firecrawl.dev/v1/scrape",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"url": url, "formats": ["markdown"]},
            timeout=30
        )
        data = response.json()
        if data.get("success"):
            return data.get("data", {}).get("markdown", "Нет данных")
        return f"Ошибка Firecrawl: {data.get('error', 'Unknown')}"
    except Exception as e:
        return f"Ошибка Firecrawl: {e}"

# ─── AI Провайдеры ─────────────────────────────────────────────
def call_openai_compat(messages: list, provider_config: dict) -> str:
    """Универсальный вызов для OpenAI-совместимых API"""
    response = requests.post(
        provider_config["endpoint"],
        headers={
            "Authorization": f"Bearer {provider_config['api_key']}",
            "Content-Type": "application/json",
        },
        json={
            "model": provider_config["model"],
            "messages": messages,
            "max_tokens": 4096,
        },
        timeout=60
    )
    data = response.json()
    return data["choices"][0]["message"]["content"]

def call_claude(messages: list, provider_config: dict) -> str:
    """Anthropic Claude"""
    system_msg = messages[0]["content"] if messages[0]["role"] == "system" else SYSTEM_PROMPT
    claude_messages = [m for m in messages if m["role"] != "system"]
    
    response = requests.post(
        provider_config["endpoint"],
        headers={
            "x-api-key": provider_config["api_key"],
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": provider_config["model"],
            "max_tokens": 4096,
            "system": system_msg,
            "messages": claude_messages,
        },
        timeout=60
    )
    data = response.json()
    return data["content"][0]["text"]

def call_gemini(messages: list, provider_config: dict) -> str:
    """Google Gemini"""
    contents = []
    for msg in messages:
        if msg["role"] == "system":
            continue
        role = "model" if msg["role"] == "assistant" else "user"
        contents.append({"role": role, "parts": [{"text": msg["content"]}]})
    
    url = provider_config["endpoint"].format(model=provider_config["model"])
    response = requests.post(
        f"{url}?key={provider_config['api_key']}",
        json={"contents": contents, "generationConfig": {"maxOutputTokens": 4096}},
        timeout=60
    )
    data = response.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]

def call_huggingface(messages: list, provider_config: dict) -> str:
    """HuggingFace Inference API"""
    endpoint = provider_config["endpoint"].format(model=provider_config["model"])
    response = requests.post(
        endpoint,
        headers={
            "Authorization": f"Bearer {provider_config['api_key']}",
            "Content-Type": "application/json",
        },
        json={
            "model": provider_config["model"],
            "messages": messages,
            "max_tokens": 4096,
        },
        timeout=60
    )
    data = response.json()
    if isinstance(data, list) and len(data) > 0:
        return data[0].get("generated_text", "")
    if "choices" in data:
        return data["choices"][0]["message"]["content"]
    return str(data)

PROVIDER_CALLERS = {
    "chatgpt": call_openai_compat,
    "claude": call_claude,
    "gemini": call_gemini,
    "grok": call_openai_compat,
    "openrouter": call_openai_compat,
    "deepseek": call_openai_compat,
    "groq": call_openai_compat,
    "nvidia": call_openai_compat,
    "huggingface": call_huggingface,
    "github": call_openai_compat,
}

# ─── Основной класс агента ─────────────────────────────────────
class BFXAgent:
    def __init__(self):
        self.current_provider = "chatgpt"
        self.conversation_history = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
        self.tools = {
            "search": web_search,
            "exec": terminal_exec,
            "fetch": web_fetch,
            "firecrawl": firecrawl_scrape,
        }
    
    def get_provider_config(self) -> dict:
        return PROVIDERS[self.current_provider]
    
    def switch_provider(self, name: str) -> str:
        name = name.lower()
        if name not in PROVIDERS:
            return f"❌ Неизвестный провайдер. Доступные: {', '.join(PROVIDERS.keys())}"
        if not PROVIDERS[name]["api_key"]:
            return f"❌ API ключ для {name} не установлен. Добавьте его в .env"
        self.current_provider = name
        return f"✅ Провайдер переключён на {name} ({PROVIDERS[name]['model']})"
    
    def call_ai(self, user_message: str) -> str:
        self.conversation_history.append({"role": "user", "content": user_message})
        
        caller = PROVIDER_CALLERS[self.current_provider]
        config = self.get_provider_config()
        
        try:
            response = caller(self.conversation_history, config)
            self.conversation_history.append({"role": "assistant", "content": response})
            return response
        except Exception as e:
            return f"❌ Ошибка вызова AI: {e}"
    
    def process_command(self, cmd: str) -> Optional[str]:
        """Обработка слэш-команд. Возвращает результат или None если не команда."""
        parts = cmd.split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        if command == "/help":
            print_help()
            return None
        elif command == "/clear":
            self.conversation_history = [{"role": "system", "content": SYSTEM_PROMPT}]
            return "🧹 История чата очищена"
        elif command == "/provider":
            return self.switch_provider(args)
        elif command == "/model":
            if args:
                PROVIDERS[self.current_provider]["model"] = args
                return f"✅ Модель изменена на {args}"
            return f"Текущая модель: {PROVIDERS[self.current_provider]['model']}"
        elif command == "/search":
            return web_search(args) if args else "Укажите запрос: /search <query>"
        elif command == "/exec":
            return terminal_exec(args) if args else "Укажите команду: /exec <command>"
        elif command == "/fetch":
            return web_fetch(args) if args else "Укажите URL: /fetch <url>"
        elif command == "/firecrawl":
            return firecrawl_scrape(args) if args else "Укажите URL: /firecrawl <url>"
        elif command == "/config":
            config_info = f"""📋 Конфигурация:
  Провайдер: {self.current_provider}
  Модель: {PROVIDERS[self.current_provider]['model']}
  Сообщений в истории: {len(self.conversation_history)}
  Доступные провайдеры: {', '.join(p for p in PROVIDERS if PROVIDERS[p]['api_key'])}"""
            return config_info
        elif command == "/quit" or command == "/exit":
            return "QUIT"
        else:
            return None
    
    def run(self):
        print_banner()
        print(f"🟢 Активный провайдер: {self.current_provider} ({PROVIDERS[self.current_provider]['model']})")
        print("Введите /help для списка команд\n")
        
        while True:
            try:
                user_input = input("\n❯ ").strip()
                if not user_input:
                    continue
                
                if user_input.startswith("/"):
                    result = self.process_command(user_input)
                    if result == "QUIT":
                        print("\n👋 До встречи!")
                        break
                    if result:
                        if HAS_RICH:
                            console = get_console()
                            console.print(Panel(result, style="yellow", border_style="yellow"))
                        else:
                            print(result)
                    continue
                
                if HAS_RICH:
                    console = get_console()
                    with console.status("🤔 Думаю...", spinner="dots"):
                        response = self.call_ai(user_input)
                    console.print(Panel(Markdown(response), title="🤖 BFX", border_style="green"))
                else:
                    print("\n🤔 Думаю...")
                    response = self.call_ai(user_input)
                    print(f"\n🤖 BFX:\n{response}")
                    
            except KeyboardInterrupt:
                print("\n\n👋 До встречи!")
                break
            except EOFError:
                print("\n\n👋 До встречи!")
                break

# ─── Точка входа ────────────────────────────────────────────────
def main():
    missing = []
    try:
        import requests
    except ImportError:
        missing.append("requests")
    try:
        import dotenv
    except ImportError:
        missing.append("python-dotenv")
    
    if missing:
        print(f"❌ Установите зависимости: pip install {' '.join(missing)}")
        print("💡 Для полного функционала: pip install rich duckduckgo-search")
        sys.exit(1)
    
    agent = BFXAgent()
    agent.run()

if __name__ == "__main__":
    main()
