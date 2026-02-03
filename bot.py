import os
import json
from datetime import datetime

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

# =====================
# LOAD ENV
# =====================
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
SHEET_ID = os.getenv("SHEET_ID")
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN kosong")

if not SHEET_ID:
    raise ValueError("SHEET_ID kosong")

if not GOOGLE_CREDENTIALS_JSON:
    raise ValueError("GOOGLE_CREDENTIALS_JSON kosong")

# =====================
# GOOGLE AUTH
# =====================
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)

creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
client = gspread.authorize(creds)

spreadsheet = client.open_by_key(SHEET_ID)

# =====================
# SHEETS
# =====================
def get_or_create(title, rows, cols):
    try:
        return spreadsheet.worksheet(title)
    except:
        return spreadsheet.add_worksheet(title=title, rows=rows, cols=cols)

visitplan_sheet = get_or_create("visitplan", 1000, 10)
user_sheet = get_or_create("id_telegram", 100, 3)

# =====================
# HEADERS
# =====================
USER_HEADER = ["telegram_id", "nama_sa", "id_sa"]
if user_sheet.row_values(1) != USER_HEADER:
    user_sheet.update("A1:C1", [USER_HEADER])

VISITPLAN_HEADER = [
    "No","Hari","Tanggal",
    "Customer","Plan Agenda","Hasil",
    "SA","ID SA","Status"
]

if visitplan_sheet.row_values(1) != VISITPLAN_HEADER:
    visitplan_sheet.update("A1:I1", [VISITPLAN_HEADER])

# =====================
# GET USER INFO
# =====================
def get_user_info(tg_id):
    rows = user_sheet.get_all_values()[1:]
    for r in rows:
        if len(r) >= 3 and str(tg_id).strip() == str(r[0]).strip():
            return r[1], r[2]
    return None, None

# =====================
# /visitplan
# =====================
async def visitplan(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text.replace("/visitplan", "").strip()

    if not text:
        await update.message.reply_text(
            "/visitplan\nNama Pelanggan | Plan Agenda | Hasil Visit"
        )
        return

    now = update.message.date.astimezone()
    hari = now.strftime("%A")
    tanggal = now.strftime("%d/%m/%Y")

    tg_id = update.effective_user.id
    nama_sa, id_sa = get_user_info(tg_id)

    if not nama_sa:
        await update.message.reply_text("❌ Telegram ID belum terdaftar di sheet.")
        return

    ok = fail = 0

    for line in text.split("\n"):
        parts = [p.strip() for p in line.split("|")]

        if len(parts) != 3:
            fail += 1
            continue

        customer, agenda, hasil = parts

        no = len(visitplan_sheet.get_all_values())

        visitplan_sheet.append_row([
            no,
            hari,
            tanggal,
            customer,
            agenda,
            hasil,
            nama_sa,
            id_sa,
            "PLAN"
        ])

        ok += 1

    await update.message.reply_text(
        f"📋 VISIT PLAN\n✅ Masuk: {ok}\n❌ Format salah: {fail}"
    )

# =====================
# /myid
# =====================
async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"Telegram ID kamu:\n{update.effective_user.id}"
    )

# =====================
# START BOT
# =====================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("visitplan", visitplan))
    app.add_handler(CommandHandler("myid", myid))

    print("🤖 YOVI TWO BOT RUNNING")
    app.run_polling()

if __name__ == "__main__":
    main()
