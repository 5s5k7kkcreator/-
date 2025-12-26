import os
from dotenv import load_dotenv

load_dotenv()
import json
import subprocess
import shutil
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)
import logging

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
BASE = os.environ.get("BASE", "user_bots/")
DB = os.environ.get("DB", "processes.json")

os.makedirs(BASE, exist_ok=True)

COMMON_LIBS = [
    "requests", "aiohttp", "python-telegram-bot",
    "flask", "fastapi", "beautifulsoup4",
    "pandas", "numpy", "pillow"
]

def load_db():
    if not os.path.exists(DB):
        return {}
    with open(DB, "r") as f:
        return json.load(f)

def save_db(data):
    with open(DB, "w") as f:
        json.dump(data, f, indent=4)

def get_user_bots(user_id):
    user_path = os.path.join(BASE, user_id)
    if not os.path.exists(user_path):
        return []
    return [d for d in os.listdir(user_path) if os.path.isdir(os.path.join(user_path, d))]

def get_bot_path(user_id, bot_name):
    return os.path.join(BASE, user_id, bot_name)

def get_main_keyboard(user_id, current_bot=None):
    keyboard = []
    
    if current_bot:
        keyboard.append([InlineKeyboardButton(f"🤖 البوت الحالي: {current_bot}", callback_data="current_info")])
        keyboard.append([
            InlineKeyboardButton("▶️ تشغيل", callback_data="run"),
            InlineKeyboardButton("⏹ إيقاف", callback_data="stop")
        ])
        keyboard.append([
            InlineKeyboardButton("📄 السجلات", callback_data="log"),
            InlineKeyboardButton("📦 تثبيت مكتبات", callback_data="install_menu")
        ])
        keyboard.append([
            InlineKeyboardButton("📁 إدارة الملفات", callback_data="files_menu"),
            InlineKeyboardButton("🔄 حالة البوت", callback_data="status")
        ])
        keyboard.append([InlineKeyboardButton("🔀 تغيير البوت", callback_data="bots_menu")])
    else:
        keyboard.append([InlineKeyboardButton("📋 بوتاتي", callback_data="bots_menu")])
        keyboard.append([InlineKeyboardButton("➕ إنشاء بوت جديد", callback_data="new_bot")])
    
    return InlineKeyboardMarkup(keyboard)

def get_bots_keyboard(user_id):
    keyboard = []
    bots = get_user_bots(user_id)
    db = load_db()
    
    for bot_name in bots:
        bot_key = f"{user_id}_{bot_name}"
        status = "🟢" if bot_key in db else "🔴"
        keyboard.append([
            InlineKeyboardButton(f"{status} {bot_name}", callback_data=f"select_{bot_name}"),
            InlineKeyboardButton("🗑", callback_data=f"delbot_{bot_name}")
        ])
    
    keyboard.append([InlineKeyboardButton("➕ إنشاء بوت جديد", callback_data="new_bot")])
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="back")])
    return InlineKeyboardMarkup(keyboard)

def get_files_keyboard(bot_path):
    keyboard = []
    if os.path.exists(bot_path):
        files = [f for f in os.listdir(bot_path) if os.path.isfile(os.path.join(bot_path, f))]
        py_files = [f for f in files if f.endswith('.py')]
        other_files = [f for f in files if not f.endswith('.py') and f not in ['log.txt', 'bot.zip']]
        
        for f in py_files[:5]:
            keyboard.append([
                InlineKeyboardButton(f"📄 {f}", callback_data=f"view_{f}"),
                InlineKeyboardButton("🗑", callback_data=f"del_{f}")
            ])
        for f in other_files[:3]:
            keyboard.append([
                InlineKeyboardButton(f"📎 {f}", callback_data=f"view_{f}"),
                InlineKeyboardButton("🗑", callback_data=f"del_{f}")
            ])
    
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="back")])
    return InlineKeyboardMarkup(keyboard)

def get_libs_keyboard():
    keyboard = []
    row = []
    for lib in COMMON_LIBS:
        row.append(InlineKeyboardButton(lib, callback_data=f"lib_{lib}"))
        if len(row) == 3:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("✍️ كتابة مكتبات يدوياً", callback_data="custom_libs")])
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="back")])
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    current_bot = context.user_data.get("current_bot")
    bots = get_user_bots(user_id)
    
    if not bots:
        await update.message.reply_text(
            "أهلاً! 👋\n\n"
            "مرحباً بك في مدير البوتات!\n\n"
            "يمكنك إنشاء عدة بوتات، كل بوت منفصل بملفاته ومكتباته الخاصة.\n\n"
            "اضغط على 'إنشاء بوت جديد' للبدء:",
            reply_markup=get_main_keyboard(user_id, None)
        )
    else:
        await update.message.reply_text(
            f"أهلاً! 👋\n\n"
            f"لديك {len(bots)} بوت(ات)\n\n"
            f"{'البوت الحالي: ' + current_bot if current_bot else 'اختر بوت للتحكم فيه'}",
            reply_markup=get_main_keyboard(user_id, current_bot)
        )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    user_path = os.path.join(BASE, user_id)
    current_bot = context.user_data.get("current_bot")
    bot_path = get_bot_path(user_id, current_bot) if current_bot else None
    
    if query.data == "bots_menu":
        bots = get_user_bots(user_id)
        if not bots:
            await query.edit_message_text(
                "📋 لا يوجد بوتات بعد.\n\nاضغط 'إنشاء بوت جديد' لإنشاء أول بوت:",
                reply_markup=get_bots_keyboard(user_id)
            )
        else:
            await query.edit_message_text(
                f"📋 بوتاتك ({len(bots)}):\n\n🟢 = شغال | 🔴 = متوقف\n\nاختر بوت للتحكم فيه:",
                reply_markup=get_bots_keyboard(user_id)
            )
    
    elif query.data == "new_bot":
        await query.edit_message_text(
            "➕ إنشاء بوت جديد\n\n"
            "أرسل اسم البوت الجديد (بدون مسافات):\n\n"
            "مثال: MyBot أو bot1"
        )
        context.user_data["waiting_for_bot_name"] = True
    
    elif query.data.startswith("select_"):
        bot_name = query.data.replace("select_", "")
        context.user_data["current_bot"] = bot_name
        
        await query.edit_message_text(
            f"✅ تم اختيار البوت: {bot_name}\n\n"
            "استخدم الأزرار للتحكم في البوت:",
            reply_markup=get_main_keyboard(user_id, bot_name)
        )
    
    elif query.data.startswith("delbot_"):
        bot_name = query.data.replace("delbot_", "")
        bot_to_delete = get_bot_path(user_id, bot_name)
        
        db = load_db()
        bot_key = f"{user_id}_{bot_name}"
        if bot_key in db:
            try:
                os.kill(db[bot_key], 9)
            except ProcessLookupError:
                pass
            del db[bot_key]
            save_db(db)
        
        if os.path.exists(bot_to_delete):
            shutil.rmtree(bot_to_delete)
        
        if context.user_data.get("current_bot") == bot_name:
            context.user_data["current_bot"] = None
        
        await query.edit_message_text(
            f"✅ تم حذف البوت: {bot_name}",
            reply_markup=get_bots_keyboard(user_id)
        )
    
    elif query.data == "run":
        if not current_bot:
            await query.edit_message_text(
                "❌ اختر بوت أولاً!",
                reply_markup=get_main_keyboard(user_id, None)
            )
            return
        
        app_path = os.path.join(bot_path, "app.py")
        if not os.path.exists(app_path):
            await query.edit_message_text(
                "❌ لم أجد app.py في مجلد البوت.\n\nأرسل ملف .py أو ZIP أولاً.",
                reply_markup=get_main_keyboard(user_id, current_bot)
            )
            return
        
        log_path = os.path.join(bot_path, "log.txt")
        env = os.environ.copy()
        env["PYTHONPATH"] = bot_path
        
        with open(log_path, "w") as log_file:
            p = subprocess.Popen(
                ["python3", "app.py"],
                stdout=log_file,
                stderr=subprocess.STDOUT,
                cwd=bot_path,
                env=env
            )
        
        db = load_db()
        bot_key = f"{user_id}_{current_bot}"
        db[bot_key] = p.pid
        save_db(db)
        
        await query.edit_message_text(
            f"✅ تم تشغيل {current_bot}!\n\nPID = {p.pid}",
            reply_markup=get_main_keyboard(user_id, current_bot)
        )
    
    elif query.data == "stop":
        if not current_bot:
            await query.edit_message_text(
                "❌ اختر بوت أولاً!",
                reply_markup=get_main_keyboard(user_id, None)
            )
            return
        
        db = load_db()
        bot_key = f"{user_id}_{current_bot}"
        
        if bot_key not in db:
            await query.edit_message_text(
                "❌ البوت غير شغال.",
                reply_markup=get_main_keyboard(user_id, current_bot)
            )
            return
        
        try:
            os.kill(db[bot_key], 9)
        except ProcessLookupError:
            pass
        
        del db[bot_key]
        save_db(db)
        
        await query.edit_message_text(
            f"⛔ تم إيقاف {current_bot}.",
            reply_markup=get_main_keyboard(user_id, current_bot)
        )
    
    elif query.data == "log":
        if not current_bot:
            await query.edit_message_text(
                "❌ اختر بوت أولاً!",
                reply_markup=get_main_keyboard(user_id, None)
            )
            return
        
        log_path = os.path.join(bot_path, "log.txt")
        if not os.path.exists(log_path):
            await query.edit_message_text(
                "❌ لا يوجد سجلات بعد.",
                reply_markup=get_main_keyboard(user_id, current_bot)
            )
            return
        
        with open(log_path, "r") as f:
            content = f.read()[-2000:]
        
        if not content:
            content = "السجلات فارغة"
        
        await query.edit_message_text(
            f"📄 سجلات {current_bot}:\n\n{content}",
            reply_markup=get_main_keyboard(user_id, current_bot)
        )
    
    elif query.data == "status":
        if not current_bot:
            await query.edit_message_text(
                "❌ اختر بوت أولاً!",
                reply_markup=get_main_keyboard(user_id, None)
            )
            return
        
        db = load_db()
        bot_key = f"{user_id}_{current_bot}"
        app_path = os.path.join(bot_path, "app.py")
        
        has_bot = os.path.exists(app_path)
        is_running = bot_key in db
        
        files_count = 0
        if os.path.exists(bot_path):
            files_count = len([f for f in os.listdir(bot_path) if os.path.isfile(os.path.join(bot_path, f))])
        
        status_text = f"🔄 حالة {current_bot}:\n\n"
        status_text += f"📁 ملف app.py: {'✅ موجود' if has_bot else '❌ غير موجود'}\n"
        status_text += f"📂 عدد الملفات: {files_count}\n"
        status_text += f"⚡ الحالة: {'🟢 شغال' if is_running else '🔴 متوقف'}\n"
        
        if is_running:
            status_text += f"🔢 PID: {db[bot_key]}"
        
        await query.edit_message_text(
            status_text,
            reply_markup=get_main_keyboard(user_id, current_bot)
        )
    
    elif query.data == "install_menu":
        if not current_bot:
            await query.edit_message_text(
                "❌ اختر بوت أولاً!",
                reply_markup=get_main_keyboard(user_id, None)
            )
            return
        
        await query.edit_message_text(
            f"📦 تثبيت مكتبات لـ {current_bot}:\n\n"
            "اختر مكتبة أو اكتب اسمها يدوياً:",
            reply_markup=get_libs_keyboard()
        )
    
    elif query.data.startswith("lib_"):
        if not current_bot:
            return
        
        lib_name = query.data.replace("lib_", "")
        
        await query.edit_message_text(f"⏳ جاري تثبيت {lib_name} في {current_bot}...")
        
        result = subprocess.run(
            ["pip", "install", lib_name, "--target", bot_path],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            await query.edit_message_text(
                f"✅ تم تثبيت {lib_name} في {current_bot}!",
                reply_markup=get_main_keyboard(user_id, current_bot)
            )
        else:
            await query.edit_message_text(
                f"❌ فشل تثبيت {lib_name}\n\n{result.stderr[:500]}",
                reply_markup=get_main_keyboard(user_id, current_bot)
            )
    
    elif query.data == "custom_libs":
        await query.edit_message_text(
            "✍️ أرسل أسماء المكتبات مفصولة بمسافات:\n\n"
            "مثال: requests flask aiohttp"
        )
        context.user_data["waiting_for_libs"] = True
    
    elif query.data == "files_menu":
        if not current_bot:
            await query.edit_message_text(
                "❌ اختر بوت أولاً!",
                reply_markup=get_main_keyboard(user_id, None)
            )
            return
        
        files = []
        if os.path.exists(bot_path):
            files = [f for f in os.listdir(bot_path) if os.path.isfile(os.path.join(bot_path, f))]
            files = [f for f in files if f not in ['log.txt', 'bot.zip']]
        
        if not files:
            await query.edit_message_text(
                f"📁 لا توجد ملفات في {current_bot}.\n\nأرسل ملف .py أو ZIP.",
                reply_markup=get_main_keyboard(user_id, current_bot)
            )
        else:
            await query.edit_message_text(
                f"📁 ملفات {current_bot} ({len(files)}):",
                reply_markup=get_files_keyboard(bot_path)
            )
    
    elif query.data.startswith("view_"):
        if not current_bot:
            return
        
        filename = query.data.replace("view_", "")
        file_path = os.path.join(bot_path, filename)
        
        if not os.path.exists(file_path):
            await query.edit_message_text(
                "❌ الملف غير موجود.",
                reply_markup=get_files_keyboard(bot_path)
            )
            return
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()[:1500]
            
            await query.edit_message_text(
                f"📄 {filename}:\n\n{content}",
                reply_markup=get_files_keyboard(bot_path)
            )
        except Exception:
            await query.edit_message_text(
                f"❌ لا يمكن قراءة {filename}",
                reply_markup=get_files_keyboard(bot_path)
            )
    
    elif query.data.startswith("del_"):
        if not current_bot:
            return
        
        filename = query.data.replace("del_", "")
        file_path = os.path.join(bot_path, filename)
        
        if os.path.exists(file_path):
            os.remove(file_path)
            await query.edit_message_text(
                f"✅ تم حذف {filename}",
                reply_markup=get_files_keyboard(bot_path)
            )
        else:
            await query.edit_message_text(
                "❌ الملف غير موجود.",
                reply_markup=get_files_keyboard(bot_path)
            )
    
    elif query.data == "current_info":
        if current_bot:
            await query.edit_message_text(
                f"🤖 البوت الحالي: {current_bot}\n\n"
                "استخدم الأزرار للتحكم أو اضغط 'تغيير البوت' لاختيار بوت آخر.",
                reply_markup=get_main_keyboard(user_id, current_bot)
            )
    
    elif query.data == "back":
        await query.edit_message_text(
            "🏠 القائمة الرئيسية",
            reply_markup=get_main_keyboard(user_id, current_bot)
        )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    current_bot = context.user_data.get("current_bot")
    
    if context.user_data.get("waiting_for_bot_name"):
        bot_name = update.message.text.strip().replace(" ", "_")
        bot_path = get_bot_path(user_id, bot_name)
        
        if os.path.exists(bot_path):
            await update.message.reply_text(
                f"❌ البوت '{bot_name}' موجود بالفعل!\n\nاختر اسم آخر:",
                reply_markup=get_bots_keyboard(user_id)
            )
            context.user_data["waiting_for_bot_name"] = False
            return
        
        os.makedirs(bot_path, exist_ok=True)
        context.user_data["current_bot"] = bot_name
        context.user_data["waiting_for_bot_name"] = False
        
        await update.message.reply_text(
            f"✅ تم إنشاء البوت: {bot_name}\n\n"
            "الآن أرسل ملف .py أو ZIP لرفع كود البوت:",
            reply_markup=get_main_keyboard(user_id, bot_name)
        )
    
    elif context.user_data.get("waiting_for_libs"):
        if not current_bot:
            context.user_data["waiting_for_libs"] = False
            await update.message.reply_text(
                "❌ اختر بوت أولاً!",
                reply_markup=get_main_keyboard(user_id, None)
            )
            return
        
        bot_path = get_bot_path(user_id, current_bot)
        packages = update.message.text.strip()
        
        await update.message.reply_text(f"⏳ جاري تثبيت: {packages}")
        
        result = subprocess.run(
            ["pip", "install"] + packages.split() + ["--target", bot_path],
            capture_output=True,
            text=True
        )
        
        context.user_data["waiting_for_libs"] = False
        
        if result.returncode == 0:
            await update.message.reply_text(
                f"✅ تم تثبيت المكتبات في {current_bot}!",
                reply_markup=get_main_keyboard(user_id, current_bot)
            )
        else:
            await update.message.reply_text(
                f"❌ فشل التثبيت\n\n{result.stderr[:500]}",
                reply_markup=get_main_keyboard(user_id, current_bot)
            )

async def auto_install_libs(bot_path, update):
    req_file = os.path.join(bot_path, "requirements.txt")
    if os.path.exists(req_file):
        await update.message.reply_text("⏳ يتم تثبيت المكتبات من requirements.txt ...")
        subprocess.run(["pip", "install", "-r", req_file, "--target", bot_path])
        await update.message.reply_text("✅ تم تثبيت المكتبات!")

async def handle_zip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    current_bot = context.user_data.get("current_bot")
    
    if not current_bot:
        await update.message.reply_text(
            "❌ أنشئ أو اختر بوت أولاً!",
            reply_markup=get_main_keyboard(user_id, None)
        )
        return
    
    bot_path = get_bot_path(user_id, current_bot)
    os.makedirs(bot_path, exist_ok=True)

    file = await update.message.document.get_file()
    zip_path = os.path.join(bot_path, "bot.zip")
    await file.download_to_drive(zip_path)

    subprocess.run(["unzip", "-o", zip_path, "-d", bot_path])

    await auto_install_libs(bot_path, update)

    await update.message.reply_text(
        f"✅ تم رفع الملفات إلى {current_bot}!",
        reply_markup=get_main_keyboard(user_id, current_bot)
    )

async def handle_py(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    current_bot = context.user_data.get("current_bot")
    
    if not current_bot:
        await update.message.reply_text(
            "❌ أنشئ أو اختر بوت أولاً!",
            reply_markup=get_main_keyboard(user_id, None)
        )
        return
    
    bot_path = get_bot_path(user_id, current_bot)
    os.makedirs(bot_path, exist_ok=True)

    file = await update.message.document.get_file()
    py_path = os.path.join(bot_path, "app.py")

    await file.download_to_drive(py_path)

    await auto_install_libs(bot_path, update)

    await update.message.reply_text(
        f"✅ تم رفع الملف إلى {current_bot}!",
        reply_markup=get_main_keyboard(user_id, current_bot)
    )

def main():
    if not TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN غير موجود!")
        print("خطأ: يرجى تعيين TELEGRAM_BOT_TOKEN")
        return

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.Document.ZIP, handle_zip))
    app.add_handler(MessageHandler(filters.Document.FileExtension("py"), handle_py))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("البوت يعمل الآن...")
    print("البوت شغال! اضغط Ctrl+C للإيقاف.")
    app.run_polling()

if __name__ == "__main__":
    main()
