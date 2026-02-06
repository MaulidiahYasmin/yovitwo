import os
import json
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

if user_sheet.row_values(1) != USER_HEADER:
    user_sheet.update("A1:C1", [USER_HEADER])

if visitplan_sheet.row_values(1) != VISIT_HEADER:
    visitplan_sheet.update("A1:H1", [VISIT_HEADER])

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
# PIPE PARSER
# =====================
def parse_pipe_lines(text):
    visits = []

    for line in text.splitlines():
        line = line.strip()

        if not line or "|" not in line:
            continue

        if "." in line:
            line = line.split(".", 1)[1].strip()

        parts = line.split("|")

        kegiatan = parts[0].strip()
        pelanggan = parts[1].strip() if len(parts) > 1 else ""
        agenda = parts[2].strip() if len(parts) > 2 else ""

        visits.append({
            "kegiatan": kegiatan,
            "pelanggan": pelanggan,
            "agenda": agenda
        })

    return visits

# =====================
# VISIT PLAN
# =====================
async def visitplan(update: Update, context: ContextTypes.DEFAULT_TYPE):

    parts = update.message.text.split("\n", 1)

    if len(parts) < 2:
        await update.message.reply_text(
            "Format:\n/visitplan\n1. Kegiatan|Nama Pelanggan|Plan Agenda"
        )
        return

    rows = parse_pipe_lines(parts[1])

    now = update.message.date.astimezone()
    hari = now.strftime("%A")
    tanggal = now.strftime("%d/%m/%Y")

    nama_sa, id_sa = get_user_info(update.effective_user.id)

    no = len(visitplan_sheet.get_all_values())

    for r in rows:
        if not r["pelanggan"] or not r["agenda"]:
            continue

        visitplan_sheet.append_row([
            no,
            hari,
            tanggal,
            r["kegiatan"],
            r["pelanggan"],
            r["agenda"],
            nama_sa,
            id_sa
        ])

        no += 1

    await update.message.reply_text("✅ Visit plan tersimpan.")

# =====================
# MY ID
# =====================
async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Telegram ID kamu:\n{update.effective_user.id}")

# =====================
# START
# =====================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("visitplan", visitplan))
    app.add_handler(CommandHandler("myid", myid))

    print("BOT RUNNING")
    app.run_polling()

if __name__ == "__main__":
    main()
