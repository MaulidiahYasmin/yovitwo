import os
import json
import re
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
from datetime import datetime

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

creds = Credentials.from_service_account_info(
    json.loads(GOOGLE_CREDENTIALS_JSON),
    scopes=SCOPES
)

client = gspread.authorize(creds)
spreadsheet = client.open_by_key(SHEET_ID)

# =====================
# GET / CREATE SHEET
# =====================
def get_or_create(title):
    try:
        return spreadsheet.worksheet(title)
    except:
        return spreadsheet.add_worksheet(title=title, rows=1000, cols=15)

visitplan_sheet = get_or_create("visitplan")
recap_sheet = get_or_create("recapvisit")
user_sheet = get_or_create("id_telegram")

# =====================
# HEADERS
# =====================
USER_HEADER = ["telegram_id", "nama_sa", "id_sa"]

VISIT_HEADER = [
    "No","Hari","Tanggal","Datel",
    "Kegiatan","Nama Pelanggan","Plan Agenda","SA","ID SA"
]

RECAP_HEADER = [
    "No","Hari","Tanggal","Datel",
    "Customer","Hasil","SA","ID SA"
]

if user_sheet.row_values(1) != USER_HEADER:
    user_sheet.update("A1:C1", [USER_HEADER])

if visitplan_sheet.row_values(1) != VISIT_HEADER:
    visitplan_sheet.update("A1:I1", [VISIT_HEADER])

if recap_sheet.row_values(1) != RECAP_HEADER:
    recap_sheet.update("A1:H1", [RECAP_HEADER])

# =====================
# AUTO REGISTER USER
# =====================
def get_user_info(tg_id):
    for r in user_sheet.get_all_values()[1:]:
        if str(r[0]) == str(tg_id):
            return r[1], r[2]

    user_sheet.append_row([tg_id, "Guest", "000"])
    return "Guest", "000"

# =====================
# BLOCK PARSER
# =====================
def parse_blocks(text):
    blocks = re.split(r"\n\s*\d+\.\s*", "\n" + text)[1:]
    results = []

    for blk in blocks:
        data = {}
        for line in blk.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                data[k.lower().strip()] = v.strip()
        if data:
            results.append(data)

    return results

# =====================
# VISIT PLAN
# =====================
async def visitplan(update: Update, context: ContextTypes.DEFAULT_TYPE):

    try:
        blocks = parse_blocks(update.message.text.split("\n", 1)[1])
    except:
        await update.message.reply_text("⚠️ Error:\nFormat salah")
        return

    now = datetime.now()
    hari = now.strftime("%A")
    tanggal = now.strftime("%d/%m/%Y")

    nama_sa, id_sa = get_user_info(update.effective_user.id)

    no_sheet = len(visitplan_sheet.get_all_values())
    error = []
    masuk = 0

    for i, b in enumerate(blocks, start=1):

        kurang = []
        if not b.get("datel"):
            kurang.append("Datel")
        if not b.get("customer"):
            kurang.append("Customer")
        if not b.get("agenda"):
            kurang.append("Agenda")

        if kurang:
            error.append(f"No {i}: kurang {', '.join(kurang)}")
            continue

        kegiatan = b.get("kegiatan", "-")

        visitplan_sheet.append_row([
            no_sheet,
            hari,
            tanggal,
            b["datel"],
            kegiatan,
            b["customer"],
            b["agenda"],
            nama_sa,
            id_sa
        ])

        no_sheet += 1
        masuk += 1

    if error:
        pesan = "⚠️ Error:\n" + "\n".join(error)
    else:
        pesan = f"{masuk} Visit Plan tersimpan."

    await update.message.reply_text(pesan)

# =====================
# RECAP VISIT
# =====================
async def recapvisit(update: Update, context: ContextTypes.DEFAULT_TYPE):

    try:
        blocks = parse_blocks(update.message.text.split("\n", 1)[1])
    except:
        await update.message.reply_text("⚠️ Error:\nFormat salah")
        return

    now = datetime.now()
    hari = now.strftime("%A")
    tanggal = now.strftime("%d/%m/%Y")

    nama_sa, id_sa = get_user_info(update.effective_user.id)

    no_sheet = len(recap_sheet.get_all_values())
    error = []
    masuk = 0

    for i, b in enumerate(blocks, start=1):

        kurang = []
        if not b.get("datel"):
            kurang.append("Datel")
        if not b.get("customer"):
            kurang.append("Customer")
        if not b.get("hasil"):
            kurang.append("Hasil")

        if kurang:
            error.append(f"No {i}: kurang {', '.join(kurang)}")
            continue

        recap_sheet.append_row([
            no_sheet,
            hari,
            tanggal,
            b["datel"],
            b["customer"],
            b["hasil"],
            nama_sa,
            id_sa
        ])

        no_sheet += 1
        masuk += 1

    if error:
        pesan = "⚠️ Error:\n" + "\n".join(error)
    else:
        pesan = f"{masuk} Recap Visit tersimpan."

    await update.message.reply_text(pesan)

# =====================
# MYID
# =====================
async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(str(update.effective_user.id))

# =====================
# MAIN
# =====================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("visitplan", visitplan))
    app.add_handler(CommandHandler("recapvisit", recapvisit))
    app.add_handler(CommandHandler("myid", myid))

    print("BOT RUNNING...")
    app.run_polling()

if __name__ == "__main__":
    main()
