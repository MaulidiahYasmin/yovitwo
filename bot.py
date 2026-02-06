import os
import json
import re
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

creds = Credentials.from_service_account_info(
    json.loads(GOOGLE_CREDENTIALS_JSON),
    scopes=SCOPES
)

client = gspread.authorize(creds)
spreadsheet = client.open_by_key(SHEET_ID)

# =====================
# SHEETS
# =====================
def get_or_create(title):
    try:
        return spreadsheet.worksheet(title)
    except:
        return spreadsheet.add_worksheet(title=title, rows=1000, cols=10)

visitplan_sheet = get_or_create("visitplan")
recap_sheet = get_or_create("recapvisit")
user_sheet = get_or_create("id_telegram")

# =====================
# HEADERS
# =====================
USER_HEADER = ["telegram_id", "nama_sa", "id_sa"]

VISIT_HEADER = [
    "No",
    "Hari",
    "Tanggal",
    "Kegiatan",
    "Nama Pelanggan",
    "Plan Agenda",
    "SA",
    "ID SA"
]

RECAP_HEADER = [
    "No",
    "Hari",
    "Tanggal",
    "Customer",
    "Agenda",
    "Hasil",
    "SA",
    "ID SA"
]

if user_sheet.row_values(1) != USER_HEADER:
    user_sheet.update("A1:C1", [USER_HEADER])

if visitplan_sheet.row_values(1) != VISIT_HEADER:
    visitplan_sheet.update("A1:H1", [VISIT_HEADER])

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
# PARSER FINAL
# =====================
def parse_blocks(text):

    # remove leading numbering (1. 2. 3.)
    text = re.sub(r"^\s*\d+\.\s*", "", text, flags=re.MULTILINE)

    visits = []
    current = {}

    for line in text.splitlines():
        line = line.strip()

        if not line:
            if current:
                visits.append(current)
                current = {}
            continue

        if ":" in line:
            k, v = line.split(":", 1)
            current[k.lower().strip()] = v.strip()

    if current:
        visits.append(current)

    return visits

# =====================
# VISIT PLAN
# =====================
async def visitplan(update: Update, context: ContextTypes.DEFAULT_TYPE):

    parts = update.message.text.split("\n", 1)
    blocks = parse_blocks(parts[1])

    now = update.message.date.astimezone()
    hari = now.strftime("%A")
    tanggal = now.strftime("%d/%m/%Y")

    nama_sa, id_sa = get_user_info(update.effective_user.id)

    no = len(visitplan_sheet.get_all_values())
    masuk = 0

    for b in blocks:

        if not b.get("customer") or not b.get("agenda"):
            continue

        kegiatan = b.get("kegiatan", "-")

        visitplan_sheet.append_row([
            no,
            hari,
            tanggal,
            kegiatan,
            b["customer"],
            b["agenda"],
            nama_sa,
            id_sa
        ])

        no += 1
        masuk += 1

    await update.message.reply_text(f"✅ {masuk} Visit Plan tersimpan.")

# =====================
# RECAP VISIT
# =====================
async def recapvisit(update: Update, context: ContextTypes.DEFAULT_TYPE):

    parts = update.message.text.split("\n", 1)
    blocks = parse_blocks(parts[1])

    now = update.message.date.astimezone()
    hari = now.strftime("%A")
    tanggal = now.strftime("%d/%m/%Y")

    nama_sa, id_sa = get_user_info(update.effective_user.id)

    no = len(recap_sheet.get_all_values())
    masuk = 0

    for b in blocks:

        if not b.get("customer") or not b.get("agenda") or not b.get("hasil"):
            continue

        recap_sheet.append_row([
            no,
            hari,
            tanggal,
            b["customer"],
            b["agenda"],
            b["hasil"],
            nama_sa,
            id_sa
        ])

        no += 1
        masuk += 1

    await update.message.reply_text(f"✅ {masuk} Recap Visit tersimpan.")

# =====================
# MY ID
# =====================
async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Telegram ID kamu:\n{update.effective_user.id}")

# =====================
# START BOT
# =====================
def main():

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("visitplan", visitplan))
    app.add_handler(CommandHandler("recapvisit", recapvisit))
    app.add_handler(CommandHandler("myid", myid))

    print("BOT RUNNING")
    app.run_polling()

if __name__ == "__main__":
    main()
