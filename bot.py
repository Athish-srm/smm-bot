from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, CallbackQueryHandler, CommandHandler, filters, ContextTypes
import re
import time
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

reply_wait = {}

# 🔥 STORE ACTIVE ORDERS
pending_orders = []

# 🔥 DUPLICATE CONTROL
recent_requests = {}
COOLDOWN = 1800


# 🔹 START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to NonStopSMM Support\n\n"
        "📌 You can use ANY format:\n\n"
        "👉 speed 123456\n"
        "👉 123456 speed up\n\n"
        "⚡ Multiple:\n"
        "speed 123456,654321\n"
        "✅ Actions: speed up, refill, cancel"
    )


# 🔹 FINAL PARSER (PERFECT VERSION)
def parse_bulk(text):
    text = text.lower().strip()
    text = re.sub(r'\s+', ' ', text)

    lines = text.split("\n")
    results = []

    for line in lines:
        line = re.sub(r'[^a-z0-9,\s]', ' ', line).strip()
        if not line:
            continue

        parts = line.split()

        if len(parts) < 2:
            return "INVALID", None

        # 🔥 Detect format
        if parts[0].isdigit():
            # OLD FORMAT → 123456 speed up
            ids_part = parts[0]
            action = " ".join(parts[1:])
        else:
            # NEW FORMAT → speed 123456
            action = parts[0]
            ids_part = parts[1]

        # 🔥 Normalize action
        if action in ["speed", "speedup", "speed up"]:
            action = "speed up"
        elif action == "refill":
            action = "refill"
        elif action == "cancel":
            action = "cancel"
        else:
            return "INVALID", None

        # 🔥 FIX MULTIPLE IDS WITH SPACE
        ids = ids_part.split(",")

        for oid in ids:
            oid = oid.strip().replace(" ", "")  # 🔥 KEY FIX

            if not oid.isdigit():
                return "INVALID_ID", None

            results.append((oid, action))

    return results, None


# 🔹 HANDLE MESSAGE
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    text = update.message.text.lower()

    # 🔒 BLOCK NON-ADMIN
    if text == "done all" and user.id != ADMIN_ID:
        await update.message.reply_text("❌ You are not allowed to use this command.")
        return

    # 🔥 ADMIN BULK DONE
    if user.id == ADMIN_ID and text == "done all":
        if not pending_orders:
            await update.message.reply_text("❌ No pending orders.")
            return

        count = len(pending_orders)

        for order in pending_orders:
            try:
                await context.bot.send_message(
                    chat_id=ADMIN_ID,
                    text=f"✅ Done\n\n📦 `{order}`",
                    parse_mode="Markdown"
                )
            except:
                pass

        pending_orders.clear()

        await update.message.reply_text(f"✅ {count} orders marked as DONE!")
        return

    # 💬 ADMIN REPLY MODE
    if user.id == ADMIN_ID and user.id in reply_wait:
        order_id, target_user = reply_wait[user.id]

        await context.bot.send_message(
            chat_id=target_user,
            text=f"📩 UPDATE\n\n📦 `{order_id}`\n\n{text}",
            parse_mode="Markdown"
        )

        await update.message.reply_text("✅ Reply sent.")
        del reply_wait[user.id]
        return

    parsed, _ = parse_bulk(text)

    if parsed == "INVALID_ID":
        await update.message.reply_text("❌ Invalid Order ID or Wrong Format\n👉 Check Order ID")
        return

    if parsed == "INVALID":
        await update.message.reply_text(
            "❌ Invalid Format\n\n"
            "✅ Examples:\n\n"
            "speed 123456\n"
            "546789 speed up\n"
            "speed 438389,456888"
        )
        return

    results_text = []

    for order_id, action in parsed:

        # 🔥 DUPLICATE CHECK
        key = f"{order_id}_{action}"
        now = time.time()

        if key in recent_requests and now - recent_requests[key] < COOLDOWN:
            results_text.append(f"⏳ {order_id} already requested.")
            continue

        recent_requests[key] = now

        # 🔥 STORE ORDER
        pending_orders.append(order_id)

        # 🔥 USER RESPONSE FORMAT
        if action == "speed up":
            results_text.append(f"🚀 SPEED UP\n\n{order_id} added for speed up.")
            action_text = "🚀 SPEED UP"

        elif action == "refill":
            results_text.append(f"🔁 REFILL\n\n{order_id} will be checked and processed for refill.\n")
            action_text = "🔁 REFILL"

        else:
            results_text.append(f"❌ CANCEL\n\n{order_id} added for cancel,Will be processed shortly.")
            action_text = "❌ CANCEL"

        # 🔹 ADMIN BUTTONS
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("💬 Reply", callback_data=f"reply|{order_id}|{user.id}"),
                InlineKeyboardButton("✅ Done", callback_data=f"done|{order_id}|{action_text}")
            ]
        ])

        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"📦 `{order_id}`\n{action_text}",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )

    await update.message.reply_text("\n\n".join(results_text))


# 🔹 BUTTON HANDLER
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data.split("|")

    # 💬 REPLY
    if data[0] == "reply":
        order_id = data[1]
        user_id = int(data[2])

        reply_wait[ADMIN_ID] = (order_id, user_id)

        await query.message.reply_text(
            f"✍️ Send reply for `{order_id}`:",
            parse_mode="Markdown"
        )
        return

    # ✅ DONE
    if data[0] == "done":
        order_id = data[1]
        action = data[2]

        if order_id in pending_orders:
            pending_orders.remove(order_id)

        await query.edit_message_text(
            text=f"✅ Done\n\n📦 `{order_id}`\n{action}",
            parse_mode="Markdown"
        )


# 🔹 RUN
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT, handle_message))
app.add_handler(CallbackQueryHandler(button_click))

print("🚀 Bot running perfectly...")
app.run_polling()   