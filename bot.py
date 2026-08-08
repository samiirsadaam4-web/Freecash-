import os
import sqlite3
from datetime import datetime, date
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

POINTS_PER_DOLLAR = 1000
REFERRAL_BONUS = 100
START_BONUS = 50
DAILY_BONUS = 50
MIN_WITHDRAWAL = 5000

DB = "bot.db"

def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    con = db()
    con.execute("""CREATE TABLE IF NOT EXISTS users(
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        points INTEGER DEFAULT 0,
        referred_by INTEGER,
        referrals INTEGER DEFAULT 0,
        last_daily TEXT
    )""")
    con.execute("""CREATE TABLE IF NOT EXISTS withdraw_requests(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount_points INTEGER,
        amount_usd REAL,
        method TEXT,
        address TEXT,
        status TEXT DEFAULT 'PENDING',
        created_at TEXT
    )""")
    con.commit()
    con.close()

def ensure_user(user_id, username, referrer=None):
    con = db()
    row = con.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
    if not row:
        valid_ref = referrer if referrer and referrer != user_id else None
        con.execute(
            "INSERT INTO users (user_id, username, points, referred_by, referrals) VALUES (?, ?, ?, ?, ?)",
            (user_id, username or "", START_BONUS, valid_ref, 0)
        )
        if valid_ref:
            con.execute(
                "UPDATE users SET points=points+?, referrals=referrals+1 WHERE user_id=?",
                (REFERRAL_BONUS, valid_ref)
            )
        con.commit()
    else:
        con.execute(
            "UPDATE users SET username=? WHERE user_id=?",
            (username or "", user_id)
        )
        con.commit()
    con.close()

def get_user(user_id):
    con = db()
    row = con.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
    con.close()
    return row

def main_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💰 Balance", callback_data="balance"),
            InlineKeyboardButton("👥 Referrals", callback_data="referrals")
        ],
        [
            InlineKeyboardButton("🎁 Daily Bonus", callback_data="daily"),
            InlineKeyboardButton("📝 Tasks", callback_data="tasks")
        ],
        [
            InlineKeyboardButton("💸 Withdraw", callback_data="withdraw"),
            InlineKeyboardButton("ℹ️ Help", callback_data="help")
        ]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ref = None

    if context.args and context.args[0].startswith("ref_"):
        try:
            ref = int(context.args[0][4:])
        except ValueError:
            ref = None

    ensure_user(user.id, user.username, ref)
    row = get_user(user.id)

    await update.message.reply_text(
        f"👋 Welcome to FreeCash Earn!\n\n"
        f"🎁 Starting bonus: {START_BONUS} points\n"
        f"💰 Your balance: {row['points']} points\n"
        f"💵 Value: ${row['points']/POINTS_PER_DOLLAR:.2f}\n\n"
        f"Invite friends, collect daily bonuses and complete tasks!",
        reply_markup=main_keyboard()
    )

def main():
    init_db()
    if not TOKEN:
        print("ERROR: BOT_TOKEN is not set!")
        return

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
