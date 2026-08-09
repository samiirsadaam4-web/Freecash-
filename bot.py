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
        self.wfile.write(b"Freecash Bot Core Active!")

def run_health_check_server():
    port = int(os.getenv("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

Thread(target=run_health_check_server, daemon=True).start()

TOKEN = os.getenv("BOT_TOKEN", "")

# ==============================================================================
# ⚙️ FREECASH STYLE CONFIGURATION
# ==============================================================================
BOT_NAME = "Freecash Rewards Bot 🟢"
POINTS_PER_DOLLAR = 1000   # 1000 Coins = $1.00 USD

ADMIN_ID = 123456789       # 👈 KU BADAL TELEGRAM USER ID-GAAGA!

# REWARDS & BONUS
START_BONUS = 50           # Welcome Coins
DAILY_BONUS = 25           # Daily Streak Coins
REFERRAL_BONUS = 100       # Invite Friends Coins
MIN_WITHDRAWAL = 5000      # $5.00 Minimum Payout

# FREECASH TASK & OFFERWALL LINKS
OFFERWALL_GAMES = "https://google.com"   # Ku xir Link-ga Games Task (CPA)
OFFERWALL_SURVEYS = "https://google.com" # Ku xir Link-ga Surveys (Monetag/CPAGrip)
OFFERWALL_APPS = "https://google.com"    # Ku xir Link-ga App Installs

MONETAG_ADS_1 = "https://google.com"
MONETAG_ADS_2 = "https://google.com"
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
            "INSERT INTO users (user_id, username, points, referred_by, referrals, last_daily, state) VALUES (?, ?, ?, ?, 0, '', 'NONE')",
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
            InlineKeyboardButton("🎯 Offerwalls (Tasks)", callback_data="offerwalls"),
            InlineKeyboardButton("🎮 Play & Earn", callback_data="games_tasks")
        ],
        [
            InlineKeyboardButton("💰 Balance", callback_data="balance"),
            InlineKeyboardButton("👥 Affiliate/Ref", callback_data="referrals")
        ],
        [
            InlineKeyboardButton("🎁 Daily Rewards", callback_data="daily"),
            InlineKeyboardButton("📺 Watch Ads", callback_data="ads_station")
        ],
        [
            InlineKeyboardButton("💸 Cashout / Withdraw", callback_data="withdraw"),
            InlineKeyboardButton("ℹ️ Support", callback_data="help")
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
        f"🟢 **Welcome to {BOT_NAME}!**\n\n"
        f"The #1 Telegram Earning Hub (Powered by Freecash Engine)!\n\n"
        f"🪙 **Coins:** {row['points']} Coins\n"
        f"💵 **USD Value:** ${row['points']/POINTS_PER_DOLLAR:.2f}\n"
        f"🎁 **Welcome Gift:** +{START_BONUS} Coins Added!\n\n"
        f"Choose an Offerwall below to start cashing out real USD:",
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

    if data == "offerwalls":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📱 App Installs & Testing", url=OFFERWALL_APPS)],
            [InlineKeyboardButton("📋 High Paying Surveys", url=OFFERWALL_SURVEYS)],
            [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_main")]
        ])
        text = "🔥 **Freecash Premium Offerwalls**\n\nComplete surveys, test new apps, and complete high-paying micro-tasks to instantly earn coins."
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)

    elif data == "games_tasks":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎮 Open Games Station", url=OFFERWALL_GAMES)],
            [InlineKeyboardButton("🔙 Back", callback_data="back_main")]
        ])
        text = "🎮 **Play Games & Reach Levels**\n\nDownload games, reach level targets, and claim up to 10,000+ Coins per game!"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)

    elif data == "ads_station":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📺 Ad Server 1 (Monetag)", url=MONETAG_ADS_1)],
            [InlineKeyboardButton("📺 Ad Server 2 (Direct Ads)", url=MONETAG_ADS_2)],
            [InlineKeyboardButton("🔙 Back", callback_data="back_main")]
        ])
        text = "📺 **Video & Banner Ads Station**\n\nWatch sponsored short ads to claim quick coins!"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)

    elif data == "balance":
        usd = row["points"] / POINTS_PER_DOLLAR
        text = f"💰 **Your Freecash Wallet**\n\n" \
               f"• Total Coins: **{row['points']} Coins**\n" \
               f"• Wallet Value: **${usd:.2f} USD**\n\n" \
               f"Keep doing offerwall tasks to unlock higher payouts!"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=main_keyboard())

    elif data == "referrals":
        bot_username = context.bot.username
        ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
        text = f"👥 **Affiliate Program**\n\n" \
               f"Earn **{REFERRAL_BONUS} Coins** for every user you invite!\n\n" \
               f"• Active Referrals: **{row['referrals']} Users**\n" \
               f"🔗 **Your Unique Referral Link:**\n`{ref_link}`"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=main_keyboard())

    elif data == "daily":
        today_str = str(date.today())
        if row["last_daily"] == today_str:
            text = "⏳ **Daily Streak**\n\nYou already claimed your daily reward today! Come back in 24 hours."
        else:
            con = db()
            con.execute("UPDATE users SET points=points+?, last_daily=? WHERE user_id=?", (DAILY_BONUS, today_str, user_id))
            con.commit()
            con.close()
            text = f"🎉 **Daily Streak Claimed!**\n\nYou earned **+{DAILY_BONUS} Coins**!"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=main_keyboard())

    elif data == "withdraw":
        usd = row["points"] / POINTS_PER_DOLLAR
        if row["points"] < MIN_WITHDRAWAL:
            text = f"🔒 **Cashout Locked**\n\n" \
                   f"• Minimum Payout: **{MIN_WITHDRAWAL} Coins** (${MIN_WITHDRAWAL/POINTS_PER_DOLLAR:.2f})\n" \
                   f"• Current Balance: **{row['points']} Coins** (${usd:.2f})\n\n" \
                   f"⚠️ Earn **{MIN_WITHDRAWAL - row['points']} more Coins** to initiate payout."
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=main_keyboard())
        else:
            update_state(user_id, "WAITING_WITHDRAW_ADDRESS")
            text = f"💸 **Freecash Payout Request**\n\n" \
                   f"Your Balance: **{row['points']} Coins** (${usd:.2f})\n\n" \
                   f"Reply with your payment details (e.g. Zaad, eDahab, USDT TRC20, PayPal):"
            await query.edit_message_text(text, parse_mode="Markdown")

    elif data == "help":
        text = f"ℹ️ **Freecash Bot Support**\n\n" \
               f"• {POINTS_PER_DOLLAR} Coins = $1.00 USD\n" \
               f"• Payout Options: Zaad, eDahab, Crypto, PayPal.\n" \
               f"• Need help? Contact Admin or join our channel."
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=main_keyboard())

    elif data == "back_main":
        await query.edit_message_text("🟢 **Freecash Dashboard**", parse_mode="Markdown", reply_markup=main_keyboard())

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

        admin_msg = f"🟢 **FREECASH CASHOUT REQUEST!** 🟢\n\n" \
                    f"👤 **User:** @{user.username or 'No Username'} (ID: `{user_id}`)\n" \
                    f"💎 **Coins:** {points} (${usd:.2f} USD)\n" \
                    f"💳 **Payout Address:** `{address}`\n" \
                    f"📅 **Date:** {date.today()}"
        
        try:
            await context.bot.send_message(chat_id=ADMIN_ID, text=admin_msg, parse_mode="Markdown")
        except Exception as e:
            print(f"Could not send notification to admin: {e}")

        await update.message.reply_text(
            f"✅ **Payout Processing!**\n\n"
            f"• Coins Deducted: **{points}** (${usd:.2f})\n"
            f"• Payment Info: `{address}`\n\n"
            f"Your request is being reviewed by the Admin team.",
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
    
    print("Freecash Bot Core Running...")
    app.run_polling()

if __name__ == "__main__":
    main()


