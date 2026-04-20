import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import os
import subprocess
import threading
import time
import random
import string

# ================= CONFIG =================
BOT_TOKEN = "8669276740:AAGIwaYDmqHWcOCU2fTfHnh_k_ejZlEYHf8"
ADMIN_ID = 8004319300

bot = telebot.TeleBot(BOT_TOKEN)

# ================= STORAGE =================
HOSTED_FILE = "hosted_bot.py"
KEY_FILE = "keys.txt"

process = None
start_time = None
authorized_users = {}

# ================= LOAD KEYS =================
def load_keys():
    keys = {}
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "r") as f:
            for line in f:
                try:
                    key, expiry = line.strip().split("|")
                    keys[key] = int(expiry)
                except:
                    continue
    return keys

def save_key(key, expiry):
    with open(KEY_FILE, "a") as f:
        f.write(f"{key}|{expiry}\n")

valid_keys = load_keys()

# ================= KEY GENERATOR =================
def generate_key(length=12):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

# ================= SYSTEM =================
def is_key_valid(key):
    if key not in valid_keys:
        return False
    if time.time() > valid_keys[key]:
        return False
    return True

def is_authorized(user_id):
    if user_id == ADMIN_ID:
        return True

    if user_id in authorized_users:
        expiry = authorized_users[user_id]
        if time.time() < expiry:
            return True
        else:
            del authorized_users[user_id]
    return False

# ================= SYSTEM INFO =================
def get_system_usage():
    try:
        load = os.getloadavg()[0]
        cpu = round((load / os.cpu_count()) * 100, 2)
    except:
        cpu = "N/A"
    return cpu

def get_uptime():
    global start_time
    if not start_time:
        return "0s"

    seconds = int(time.time() - start_time)
    mins, sec = divmod(seconds, 60)
    hrs, mins = divmod(mins, 60)

    return f"{hrs}h {mins}m {sec}s"

def get_status():
    global process
    if process and process.poll() is None:
        return "🟢 Status: Bot is running"
    else:
        return "🔴 Status: No bot hosted"

# ================= UI =================
def main_text():
    return f"""
🤖 <b>BOT HOSTING BY:@Zaraki333</b>

{get_status()}

🖥 CPU: {get_system_usage()}%
⏱ Uptime: {get_uptime()}

📂 Send .py file to host
"""

def main_menu():
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("▶️ Start Bot", callback_data="start"),
        InlineKeyboardButton("⏹ Stop Bot", callback_data="stop")
    )
    markup.add(
        InlineKeyboardButton("🔄 Refresh", callback_data="refresh")
    )
    return markup

# ================= START =================
@bot.message_handler(commands=['start'])
def start(msg):
    if not is_authorized(msg.from_user.id):
        bot.send_message(msg.chat.id, "🔑 Send key using:\n/key YOUR_KEY")
        return

    bot.send_message(msg.chat.id, main_text(), reply_markup=main_menu(), parse_mode="HTML")

# ================= USE KEY =================
@bot.message_handler(commands=['key'])
def use_key(msg):
    try:
        key = msg.text.split()[1]
    except:
        bot.reply_to(msg, "❌ Usage: /key YOUR_KEY")
        return

    if is_key_valid(key):
        expiry = valid_keys[key]
        authorized_users[msg.from_user.id] = expiry

        remaining = int(expiry - time.time())
        bot.reply_to(msg, f"✅ Access granted!\n⏳ Expires in {remaining//3600}h")
    else:
        bot.reply_to(msg, "❌ Invalid or expired key")

# ================= ADMIN GENERATE =================
@bot.message_handler(commands=['genkey'])
def gen_key(msg):
    if msg.from_user.id != ADMIN_ID:
        return

    try:
        days = int(msg.text.split()[1])
    except:
        bot.reply_to(msg, "Usage: /genkey DAYS\nExample: /genkey 1")
        return

    key = generate_key()
    expiry = int(time.time() + days * 86400)

    valid_keys[key] = expiry
    save_key(key, expiry)

    bot.reply_to(
        msg,
        f"🔑 Key:\n<code>{key}</code>\n⏳ Expires in {days} day(s)",
        parse_mode="HTML"
    )

# ================= CALLBACK =================
@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    global process, start_time

    if not is_authorized(call.from_user.id):
        bot.answer_callback_query(call.id, "🔑 Unauthorized", show_alert=True)
        return

    if call.data == "start":
        if not os.path.exists(HOSTED_FILE):
            bot.answer_callback_query(call.id, "❌ No file")
            return

        if process and process.poll() is None:
            bot.answer_callback_query(call.id, "⚠️ Already running")
            return

        process = subprocess.Popen(["python", HOSTED_FILE])
        start_time = time.time()
        bot.answer_callback_query(call.id, "✅ Started")

    elif call.data == "stop":
        if process and process.poll() is None:
            process.terminate()
            process = None
            start_time = None
            bot.answer_callback_query(call.id, "⏹ Stopped")
        else:
            bot.answer_callback_query(call.id, "⚠️ Not running")

    elif call.data == "refresh":
        bot.answer_callback_query(call.id, "🔄 Refresh")

    bot.edit_message_text(
        main_text(),
        call.message.chat.id,
        call.message.message_id,
        reply_markup=main_menu(),
        parse_mode="HTML"
    )

# ================= FILE =================
@bot.message_handler(content_types=['document'])
def file_handler(msg):
    if not is_authorized(msg.from_user.id):
        return

    if not msg.document.file_name.endswith(".py"):
        bot.reply_to(msg, "❌ Only .py allowed")
        return

    file_info = bot.get_file(msg.document.file_id)
    data = bot.download_file(file_info.file_path)

    with open(HOSTED_FILE, "wb") as f:
        f.write(data)

    bot.reply_to(msg, "✅ Uploaded")

# ================= MONITOR =================
def monitor():
    global process, start_time
    while True:
        if process and process.poll() is not None:
            process = None
            start_time = None
        time.sleep(5)

threading.Thread(target=monitor, daemon=True).start()

# ================= RUN =================
print("🚀 Bot Hosting with Expiry Running...")
bot.infinity_polling()