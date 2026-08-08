import os
import sqlite3
from datetime import date
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# Render Port Fix (Health Check Server)
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

def run_health_check_server():
    port = int(os.getenv("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

Thread(target=run_health_check_server, daemon=True).start()

TOKEN = os.getenv("BOT_TOKEN", "")

# 🔒 BADALADDA QAABKA LACAG QAADASHADA (XADDIDAAD)
POINTS_PER_DOLLAR = 1000
REFERRAL_BONUS = 20      # La hoos u dhigay (Ahaay 100)
START_BONUS = 10         # La hoos u dhigay (Ahaay 50)
DAILY_BONUS = 10         # La hoos u dhigay (Ahaay 50)
TASK_BONUS = 50          # La hoos u dhigay (Ahaay 500)
MIN_WITHDRAWAL = 20000   # 🔒 Loo kordhiyay $20 (20,000 Points) si aan lacag laga dhacaan ahayn looga qaadan!

CHANNEL_LINK = "https://t.me/telegram"
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
        last_daily TEXT,
        task_completed INTEGER DEFAULT 0,
        state TEXT DEFAULT 'NONE'
    )""")
    con.execute("""CREATE TABLE IF NOT EXISTS withdraw_requests(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount_points INTEGER,
        address TEXT,
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
            "INSERT INTO users (user_id, username, points, referred_by, referrals, last_daily, task_completed, state) VALUES (?, ?, ?, ?, 0, '', 0, 'NONE')",
            (user_id, username or "", START_BONUS, valid_ref)
        )
        if valid_ref:
            con.execute(
                "UPDATE users SET points=points+?, referrals=referrals+1 WHERE user_id=?",
                (REFERRAL_BONUS, valid_ref)
            )
        con.commit()
    else:
        con.execute("UPDATE users SET username=? WHERE user_id=?", (username or "", user_id))
        con.commit()
    con.close()

def get_user(user_id):
    con = db()
    row = con.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
    con.close()
    return row

def update_state(user_id, state):
    con = db()
    con.execute("UPDATE users SET state=? WHERE user_id=?", (state, user_id))
    con.commit()
    con.close()

def main_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💰 Balance", callback_data="balance"),
            InlineKeyboardButton("👥 Referrals", callback_data="referrals")
        ],
        [
            InlineKeyboardButton("🎁 Daily Bonus", callback_data="daily"),
            InlineKeyboardButton("📝 Tasks (+50)", callback_data="tasks")
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
        f"👋 **Welcome to FreeCash Earn!**\n\n"
        f"🎁 Starting bonus: {START_BONUS} points\n"
        f"💰 Your balance: {row['points']} points\n"
        f"💵 Value: ${row['points']/POINTS_PER_DOLLAR:.2f}\n\n"
        f"Complete tasks, invite friends, and claim daily bonuses!",
        parse_mode="Markdown",
        reply_markup=main_keyboard()
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    row = get_user(user_id)

    if not row:
        ensure_user(user_id, query.from_user.username)
        row = get_user(user_id)

    data = query.data

    if data == "balance":
        usd = row["points"] / POINTS_PER_DOLLAR
        text = f"💰 **Your Balance Details**\n\n" \
               f"• Points: **{row['points']}**\n" \
               f"• Value: **${usd:.2f}** USD\n\n" \
               f"Keep completing tasks and inviting friends to earn more!"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=main_keyboard())

    elif data == "referrals":
        bot_username = context.bot.username
        ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
        text = f"👥 **Referral System**\n\n" \
               f"Earn **{REFERRAL_BONUS} points** for every friend you invite!\n\n" \
               f"• Total Invited: **{row['referrals']}** friends\n" \
               f"🔗 **Your Referral Link:**\n`{ref_link}`"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=main_keyboard())

    elif data == "daily":
        today_str = str(date.today())
        if row["last_daily"] == today_str:
            text = "⏳ **Daily Bonus**\n\nYou have already claimed your daily bonus today! Come back tomorrow."
        else:
            con = db()
            con.execute("UPDATE users SET points=points+?, last_daily=? WHERE user_id=?", (DAILY_BONUS, today_str, user_id))
            con.commit()
            con.close()
            text = f"🎉 **Daily Bonus Claimed!**\n\nYou received **+{DAILY_BONUS} points**!"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=main_keyboard())

    elif data == "tasks":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK)],
            [InlineKeyboardButton("✅ Claim +50 Points", callback_data="claim_task")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_main")]
        ])
        text = "📝 **Official Channel Task (+50 Points)**\n\n" \
               "1. Click **Join Channel** button below and join the channel.\n" \
               "2. Come back and click **Claim +50 Points** to get your reward!"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)

    elif data == "claim_task":
        if row["task_completed"] == 1:
            text = "⚠️ **Task Already Completed!**\n\nYou have already claimed the reward for this channel."
            keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_main")]])
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)
        else:
            con = db()
            con.execute("UPDATE users SET points=points+?, task_completed=1 WHERE user_id=?", (TASK_BONUS, user_id))
            con.commit()
            con.close()
            text = f"🎉 **Task Completed Successfully!**\n\nYou received **+{TASK_BONUS} points**!"
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=main_keyboard())

    elif data == "withdraw":
        usd = row["points"] / POINTS_PER_DOLLAR
        # 🔒 MINIMUM WITHDRAWAL CHECK
        if row["points"] < MIN_WITHDRAWAL:
            text = f"🔒 **Withdrawal Locked**\n\n" \
                   f"• Minimum Limit: **{MIN_WITHDRAWAL} points** (${MIN_WITHDRAWAL/POINTS_PER_DOLLAR:.2f})\n" \
                   f"• Your Balance: **{row['points']} points** (${usd:.2f})\n\n" \
                   f"⚠️ You need **{MIN_WITHDRAWAL - row['points']} more points** to request a payout."
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=main_keyboard())
        else:
            update_state(user_id, "WAITING_WITHDRAW_ADDRESS")
            text = f"💸 **Withdrawal Request**\n\n" \
                   f"Your Balance: **{row['points']} points** (${usd:.2f})\n\n" \
                   f"Please reply with your payment address (e.g., USDT TRC20, Zaad, or eDahab number):"
            await query.edit_message_text(text, parse_mode="Markdown")

    elif data == "help":
        text = "ℹ️ **Help & Support**\n\n" \
               "• Earn points by completing tasks and inviting friends.\n" \
               "• 1,000 points = $1.00 USD.\n" \
               "• Minimum withdrawal limit is 20,000 points ($20.00)."
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=main_keyboard())

    elif data == "back_main":
        await query.edit_message_text("👋 **Main Menu**", parse_mode="Markdown", reply_markup=main_keyboard())

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    row = get_user(user_id)

    if row and row["state"] == "WAITING_WITHDRAW_ADDRESS":
        address = update.message.text
        points = row["points"]
        usd = points / POINTS_PER_DOLLAR

        con = db()
        con.execute(
            "INSERT INTO withdraw_requests (user_id, amount_points, address, created_at) VALUES (?, ?, ?, ?)",
            (user_id, points, address, str(date.today()))
        )
        con.execute("UPDATE users SET points=0, state='NONE' WHERE user_id=?", (user_id,))
        con.commit()
        con.close()

        await update.message.reply_text(
            f"✅ **Withdrawal Submitted!**\n\n"
            f"• Points Deducted: **{points}** (${usd:.2f})\n"
            f"• Address/Number: `{address}`\n\n"
            f"Your request is being reviewed by the admin team.",
            parse_mode="Markdown",
            reply_markup=main_keyboard()
        )

def main():
    init_db()
    if not TOKEN:
        print("ERROR: BOT_TOKEN is not set!")
        return

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()

