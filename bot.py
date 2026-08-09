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

# ==============================================================================
# ⚙️ SETTINGS - HAGAISHA BOT-KA IYO BUTEENADA CUSUB
# ==============================================================================
BOT_NAME = "FreeCash Earn Pro"
POINTS_PER_DOLLAR = 1000   # 1000 points = $1 USD

# ADMIN TELEGRAM ID (Geli ID-gaaga Telegram-ka si ay fariimaha Withdrawal-ka u soo dhacaan)
ADMIN_ID = 123456789       # 👈 KU BADAL TELEGRAM USER ID-GAAGA!

# BONUSES & LIMITS
START_BONUS = 20           
DAILY_BONUS = 15           
REFERRAL_BONUS = 30        
TASK_BONUS = 50            
MIN_WITHDRAWAL = 10000     # $10 Minimum Withdrawal (10,000 Points)

# TASK & ADS LINKS (Shirkadaha & Ads-ka)
CHANNEL_1 = "https://t.me/telegram"
CHANNEL_2 = "https://t.me/durov"
WEBSITE_TASK = "https://google.com"

# MONETAG / DIRECT ADS LINKS
AD_LINK_1 = "https://google.com" # Geli Monetag Direct Link 1
AD_LINK_2 = "https://google.com" # Geli Monetag Direct Link 2
AD_LINK_3 = "https://google.com" # Geli Monetag Direct Link 3
# ==============================================================================

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
        task1 INTEGER DEFAULT 0,
        task2 INTEGER DEFAULT 0,
        task3 INTEGER DEFAULT 0,
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
            "INSERT INTO users (user_id, username, points, referred_by, referrals, last_daily, task1, task2, task3, state) VALUES (?, ?, ?, ?, 0, '', 0, 0, 0, 'NONE')",
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
            InlineKeyboardButton("📝 Corporate Tasks", callback_data="tasks")
        ],
        [
            InlineKeyboardButton("📺 Watch Ads (Multiple)", callback_data="ads_menu"),
            InlineKeyboardButton("💸 Withdraw", callback_data="withdraw")
        ],
        [
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
        f"🔥 **Welcome to {BOT_NAME}!** 🔥\n\n"
        f"Earn money easily by watching ads, completing company tasks, and inviting friends!\n\n"
        f"🎁 **Welcome Bonus:** {START_BONUS} points\n"
        f"💰 **Your Balance:** {row['points']} points (${row['points']/POINTS_PER_DOLLAR:.2f})\n\n"
        f"Choose an option below to start earning:",
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
        text = f"💰 **Account Balance**\n\n" \
               f"• Points: **{row['points']}**\n" \
               f"• Value: **${usd:.2f} USD**\n\n" \
               f"Complete more tasks and watch ads to increase your earnings!"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=main_keyboard())

    elif data == "referrals":
        bot_username = context.bot.username
        ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
        text = f"👥 **Referral System**\n\n" \
               f"Invite friends and earn **{REFERRAL_BONUS} points** for each friend!\n\n" \
               f"• Total Invited: **{row['referrals']}**\n" \
               f"🔗 **Your Referral Link:**\n`{ref_link}`"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=main_keyboard())

    elif data == "daily":
        today_str = str(date.today())
        if row["last_daily"] == today_str:
            text = "⏳ **Daily Bonus**\n\nYou already claimed your daily bonus today. Come back tomorrow!"
        else:
            con = db()
            con.execute("UPDATE users SET points=points+?, last_daily=? WHERE user_id=?", (DAILY_BONUS, today_str, user_id))
            con.commit()
            con.close()
            text = f"🎉 **Daily Bonus Claimed!**\n\nYou received **+{DAILY_BONUS} points**!"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=main_keyboard())

    elif data == "tasks":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Task 1: Main Channel (+50)", url=CHANNEL_1), InlineKeyboardButton("✅ Claim 1", callback_data="claim_t1")],
            [InlineKeyboardButton("📢 Task 2: Partner Channel (+50)", url=CHANNEL_2), InlineKeyboardButton("✅ Claim 2", callback_data="claim_t2")],
            [InlineKeyboardButton("🌐 Task 3: Visit Sponsor Site (+50)", url=WEBSITE_TASK), InlineKeyboardButton("✅ Claim 3", callback_data="claim_t3")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_main")]
        ])
        text = "📝 **Corporate Tasks**\n\nComplete company tasks below to earn extra points:"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)

    elif data in ["claim_t1", "claim_t2", "claim_t3"]:
        t_num = data[-2:] # 't1', 't2', or 't3'
        col = f"task{t_num[1]}"
        if row[col] == 1:
            await query.answer("⚠️ You already completed this task!", show_alert=True)
        else:
            con = db()
            con.execute(f"UPDATE users SET points=points+?, {col}=1 WHERE user_id=?", (TASK_BONUS, user_id))
            con.commit()
            con.close()
            await query.answer(f"🎉 Success! +{TASK_BONUS} Points added!", show_alert=True)
            await query.edit_message_text("✅ Task completed! Select another task or go back.", reply_markup=main_keyboard())

    elif data == "ads_menu":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📺 Watch Ad 1 (+20 Points)", url=AD_LINK_1)],
            [InlineKeyboardButton("📺 Watch Ad 2 (+20 Points)", url=AD_LINK_2)],
            [InlineKeyboardButton("📺 Watch Ad 3 (+20 Points)", url=AD_LINK_3)],
            [InlineKeyboardButton("🔙 Back", callback_data="back_main")]
        ])
        text = "📺 **Sponsored Ads Station**\n\nClick any ad below to watch and support the bot!"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)

    elif data == "withdraw":
        usd = row["points"] / POINTS_PER_DOLLAR
        if row["points"] < MIN_WITHDRAWAL:
            text = f"🔒 **Withdrawal Locked**\n\n" \
                   f"• Minimum Limit: **{MIN_WITHDRAWAL} points** (${MIN_WITHDRAWAL/POINTS_PER_DOLLAR:.2f})\n" \
                   f"• Your Balance: **{row['points']} points** (${usd:.2f})\n\n" \
                   f"⚠️ Earn **{MIN_WITHDRAWAL - row['points']} more points** to cash out."
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=main_keyboard())
        else:
            update_state(user_id, "WAITING_WITHDRAW_ADDRESS")
            text = f"💸 **Withdrawal Request**\n\n" \
                   f"Your Balance: **{row['points']} points** (${usd:.2f})\n\n" \
                   f"Please send your payout number/address (e.g., Zaad, eDahab, USDT TRC20):"
            await query.edit_message_text(text, parse_mode="Markdown")

    elif data == "help":
        text = f"ℹ️ **Help Center**\n\n" \
               f"• {POINTS_PER_DOLLAR} Points = $1.00 USD\n" \
               f"• Complete tasks and watch ads daily.\n" \
               f"• Minimum payout limit: {MIN_WITHDRAWAL} points."
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=main_keyboard())

    elif data == "back_main":
        await query.edit_message_text("👋 **Main Menu**", parse_mode="Markdown", reply_markup=main_keyboard())

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
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

        # 📩 ADIGO EE ADMIN-KA AH OGEEYSIIN TOOS AH IGO SOO DHIBA
        admin_msg = f"🚨 **NEW WITHDRAWAL REQUEST!** 🚨\n\n" \
                    f"👤 **User:** @{user.username or 'No Username'} (ID: `{user_id}`)\n" \
                    f"💰 **Amount:** {points} points (${usd:.2f} USD)\n" \
                    f"📲 **Payment Address:** `{address}`\n" \
                    f"📅 **Date:** {date.today()}"
        
        try:
            await context.bot.send_message(chat_id=ADMIN_ID, text=admin_msg, parse_mode="Markdown")
        except Exception as e:
            print(f"Could not send notification to admin: {e}")

        await update.message.reply_text(
            f"✅ **Withdrawal Request Received!**\n\n"
            f"• Points Deducted: **{points}** (${usd:.2f})\n"
            f"• Address/Number: `{address}`\n\n"
            f"Your payout is being processed by the Admin.",
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


