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
ADMIN_IDS = {5879410668}

# --- БАЗА ДАННЫХ SQLite ---
class Database:
    def __init__(self, db_name='/tmp/bot_data.db'):
        self.db_name = db_name
        self.init_database()

    def get_connection(self):
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        return conn

    def init_database(self):
        with self.get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS plan_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT UNIQUE NOT NULL,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            result = conn.execute('SELECT COUNT(*) as count FROM plan_data').fetchone()
            if result['count'] == 0:
                initial_data = {
                    "version": "1.9",
                    "creation_date": datetime.now().isoformat(),
                    "total_days": 16,
                    "tasks": {
                        "Тема": {"completed": 1, "total": 1},
                        "Дизайн": {"completed": 1, "total": 4},
                        "Ландшафт": {"completed": 0, "total": 1},
                        "Скриптинг": {"completed": 0, "total": 3},
                        "Тестировка": {"completed": 0, "total": 1},
                        "Оптимизация": {"completed": 0, "total": 3},
                        "Выпуск": {"completed": 0, "total": 2},
                        "Тесты": {"completed": 0, "total": 1}
                    }
                }
                
                for key, value in initial_data.items():
                    if isinstance(value, (dict, list)):
                        value = json.dumps(value, ensure_ascii=False)
                    conn.execute(
                        'INSERT INTO plan_data (key, value) VALUES (?, ?)',
                        (key, str(value))
                    )

    def get_plan_data(self):
        with self.get_connection() as conn:
            rows = conn.execute('SELECT key, value FROM plan_data').fetchall()
            plan_data = {}
            
            for row in rows:
                key = row['key']
                value = row['value']
                
                try:
                    value = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    pass
                
                if isinstance(value, str):
                    if value.isdigit():
                        value = int(value)
                    elif value.replace('.', '', 1).isdigit():
                        value = float(value)
                
                plan_data[key] = value
            
            return plan_data

    def update_plan_value(self, key, value):
        with self.get_connection() as conn:
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            
            conn.execute(
                'INSERT OR REPLACE INTO plan_data (key, value) VALUES (?, ?)',
                (key, str(value))
            )

    def update_task(self, task_name, completed, total):
        plan_data = self.get_plan_data()
        tasks = plan_data.get('tasks', {})
        
        if task_name in tasks:
            tasks[task_name]['completed'] = completed
            tasks[task_name]['total'] = total
            self.update_plan_value('tasks', tasks)
            return True
        return False

# Создаем экземпляр базы данных
db = Database()

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

def calculate_days_passed(creation_date) -> int:
    if isinstance(creation_date, str):
        creation_date = datetime.fromisoformat(creation_date)
    days_passed = (datetime.now() - creation_date).days
    total_days = db.get_plan_data().get('total_days', 16)
    return min(days_passed, total_days)

def generate_plan_text():
    plan_data = db.get_plan_data()
    days_passed = calculate_days_passed(plan_data.get('creation_date', datetime.now()))
    total_days = plan_data.get('total_days', 16)
    
    plan_text = f"""
📅 План работ проекта
Для обновления {plan_data.get('version', '1.9')}

--Время создания версии {days_passed}/{total_days} дней--

"""
    
    tasks = plan_data.get('tasks', {})
    for task_name, task_data in tasks.items():
        completed = task_data.get('completed', 0)
        total = task_data.get('total', 0)
        plan_text += f"• {task_name}:\n    {completed}/{total} дней\n\n"
    
    plan_text += "• Общий прогресс:\n"
    total_completed = sum(task.get('completed', 0) for task in tasks.values())
    total_tasks = sum(task.get('total', 0) for task in tasks.values())
    percentage = (total_completed / total_tasks * 100) if total_tasks > 0 else 0
    plan_text += f"    {total_completed}/{total_tasks} ({percentage:.1f}%)"
    
    return plan_text

# --- КОМАНДЫ БОТА ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = """
🤖 Я бот помощник в IT сфере разработки, главный бот в данной группе.

Доступные команды:
/plan - План работ
/admin - Инфо об администраторах
/rules - Правила группы
/Version - Данные о версиях
/Creators - Данные о создателях

/menu - Показать меню с кнопками

Команды для админов:
/planUpdate <версия> - Обновить версию
/planDesign <прогресс> - Обновить дизайн
/planTask <задача> <прогресс> - Обновить любую задачу
"""
    await update.message.reply_text(welcome_text)

async def plan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    plan_text = generate_plan_text()
    await update.message.reply_text(plan_text)

async def plan_update_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ Эта команда только для администраторов!")
        return
    
    if not context.args:
        await update.message.reply_text("❌ Использование: /planUpdate <новая_версия>")
        return
    
    new_version = context.args[0]
    db.update_plan_value('version', new_version)
    db.update_plan_value('creation_date', datetime.now().isoformat())
    await update.message.reply_text(f"✅ Версия обновлена на {new_version}!")

async def plan_design_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ Эта команда только для администраторов!")
        return
    
    if not context.args:
        await update.message.reply_text("❌ Использование: /planDesign <выполнено>/<всего>")
        return
    
    try:
        progress = context.args[0]
        if '-' in progress:
            completed, total = map(int, progress.split('-'))
        else:
            completed, total = map(int, progress.split('/'))
        
        if db.update_task('Дизайн', completed, total):
            await update.message.reply_text(f"✅ Прогресс дизайна обновлен: {completed}/{total}")
        else:
            await update.message.reply_text("❌ Ошибка при обновлении дизайна")
        
    except (ValueError, IndexError):
        await update.message.reply_text("❌ Неверный формат. Используйте: /planDesign 2-4 или /planDesign 2/4")

async def plan_task_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ Эта команда только для администраторов!")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text("❌ Использование: /planTask <задача> <прогресс>")
        plan_data = db.get_plan_data()
        tasks = list(plan_data.get('tasks', {}).keys())
        await update.message.reply_text("📋 Доступные задачи: " + ", ".join(tasks))
        return
    
    task_name = context.args[0]
    progress = context.args[1]
    
    plan_data = db.get_plan_data()
    if task_name not in plan_data.get('tasks', {}):
        await update.message.reply_text(f"❌ Задача '{task_name}' не найдена!")
        return
    
    try:
        if '-' in progress:
            completed, total = map(int, progress.split('-'))
        else:
            completed, total = map(int, progress.split('/'))
        
        if db.update_task(task_name, completed, total):
            await update.message.reply_text(f"✅ Задача '{task_name}' обновлена: {completed}/{total}")
        else:
            await update.message.reply_text(f"❌ Ошибка при обновлении задачи '{task_name}'")
        
    except (ValueError, IndexError):
        await update.message.reply_text("❌ Неверный формат прогресса. Используйте: 2-4 или 2/4")

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_info = """
👨‍💻 Администраторы:
• @Set_ez - Создатель
• @Set_ez - Модератор

По вопросам модерации обращайтесь к ним!
"""
    await update.message.reply_text(admin_info)

async def rules_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rules_text = """
📜 Правила группы:
1. Уважайте друг друга
2. Не спамьте
3. Сообщения по теме
4. Запрещенно унижение
"""
    await update.message.reply_text(rules_text)

async def Version_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    version_text = """
Версия бота - 1.1
Версия игры - 1.8
"""
    await update.message.reply_text(version_text)

async def Creators_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    Creators_text = """
Данные о создателях:

•   @Set_ez - Админ
    Создает скрипты, делает дизайн и многое другое,
    создает большую часть работы а так же может 
    работать с чем угодно в студии.

•   @REES3421 - Второй админ
    Создает примитивные анимации, делает мелкий
    дизайн по типу раставления кустиков или 
    разноображивать локации, хорошо знает Python.
"""
    await update.message.reply_text(Creators_text)

async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ['📅 План', '👮 Админы'],
        ['📜 Правила', '❓ Помощь']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Выберите опцию:", reply_markup=reply_markup)

async def hide_menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Меню скрыто! Используйте /menu чтобы показать снова.",
        reply_markup=ReplyKeyboardRemove()
    )

async def handle_group_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type not in ['group', 'supergroup']:
        return

    user_text = update.message.text.lower()
    user_name = update.effective_user.first_name

    if user_text == '📅 план':
        await plan_command(update, context)
        return
    elif user_text == '👮 админы':
        await admin_command(update, context)
        return
    elif user_text == '📜 правила':
        await rules_command(update, context)
        return
    elif user_text == '❓ помощь':
        await start_command(update, context)
        return

    keywords_responses = {
        'привет': f'Привет, {user_name}! 👋',
        'проблема': 'Проблему может решить Giga Chat в этой группе либо @Set_ez',
        'в чем смысл': 'Данный проект имеет обширный список задач',
        'что за боты тут': 'Есть бот помощник - я а так же ИИ Giga Chat',
        'я устал': 'окак',
        '@set_ez': 'Админ группы @Set_ez',
        'python': '🐍 Python - лучший язык для ботов!',
        'ошибка': 'Если что-то сломалось, пишите админам!'
    }

    for keyword, response in keywords_responses.items():
        if keyword in user_text:
            await update.message.reply_text(response)
            break

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Ошибка в update {update}: {context.error}")

# --- ОСНОВНАЯ ФУНКЦИЯ ---
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Добавляем обработчики команд
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

    # Обработчик сообщений в группах
    app.add_handler(MessageHandler(
        filters.ChatType.GROUP & filters.TEXT & ~filters.COMMAND,
        handle_group_messages
    ))

    # Обработчик ошибок
    app.add_error_handler(error_handler)

    # ЗАПУСК ДЛЯ RENDER
    if os.environ.get('RENDER'):
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
        logger.info("Запуск в режиме Polling (разработка)...")
        app.run_polling()

if __name__ == "__main__":
    main()
