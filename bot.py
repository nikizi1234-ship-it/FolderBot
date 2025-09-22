import logging
import sqlite3
import os
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from datetime import datetime
import json

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфигурация
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8394383082:AAETIr-_lw61ltGEz0SfUujgbwILxErGlgw')
ADMIN_IDS = {5879410668}  # Ваш ID админа

# ... ВСТАВЬТЕ СЮДА ВЕСЬ ВАШ КОД С БАЗОЙ ДАННЫХ И ФУНКЦИЯМИ ...

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Добавляем обработчики
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("plan", plan_command))
    app.add_handler(CommandHandler("planUpdate", plan_update_command))
    app.add_handler(CommandHandler("planDesign", plan_design_command))
    app.add_handler(CommandHandler("planTask", plan_task_command))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CommandHandler("rules", rules_command))
    app.add_handler(CommandHandler("Version", Version_command))
    app.add_handler(CommandHandler("Creators", Creators_command))
    app.add_handler(CommandHandler("menu", menu_command))
    app.add_handler(CommandHandler("hide", hide_menu_command))

    app.add_handler(MessageHandler(
        filters.ChatType.GROUP & filters.TEXT & ~filters.COMMAND,
        handle_group_messages
    ))

    app.add_error_handler(error_handler)

    # ЗАПУСК ДЛЯ RENDER
    if os.environ.get('RENDER'):
        # Режим Production на Render
        port = int(os.environ.get('PORT', 8443))
        webhook_url = os.environ.get('WEBHOOK_URL', '')
        
        logger.info(f"Запуск в режиме Webhook на Render, порт: {port}")
        
        app.run_webhook(
            listen="0.0.0.0",
            port=port,
            webhook_url=webhook_url + BOT_TOKEN,
            url_path=BOT_TOKEN
        )
    else:
        # Локальная разработка
        logger.info("Запуск в режиме Polling (разработка)...")
        app.run_polling()

if __name__ == "__main__":
    main()
