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
recap_sheet = get_or_create("recapvisit")
user_sheet = get_or_create("id_telegram")

# =====================
# HEADERS
# =====================
USER_HEADER = ["telegram_id", "nama_sa", "id_sa"]
if user_sheet.row_values(1) != USER_HEADER:
    user_sheet.update("A1:C1", [USER_HEADER])

MAIN_HEADER = ["No", "Hari", "Tanggal", "Customer", "Plan Agenda", "Hasil", "SA", "ID SA"]

for s in [visitplan_sheet, recap_sheet]:
    if s.row_values(1) != MAIN_HEADER:
        s.update("A1:H1", [MAIN_HEADER])

# =====================
# USER INFO
# =====================
def get_user_info(tg_id):
    rows = user_sheet.get_all_values()[1:]
    for r in rows:
        if len(r) >= 3 and str(r[0]).strip() == str(tg_id).strip():
            return r[1], r[2]
    return None, None

# =====================
# CORE SAVE
# =====================
async def save(sheet, update: Update, success_text):

    parts = update.message.text.split("\n", 1)

    if len(parts) < 2:
        await update.message.reply_text(
            "Format:\nNama Pelanggan | Plan Agenda | Hasil"
        )
        return

    text = parts[1].strip()

    if not text:
        await update.message.reply_text(
            "Format:\nNama Pelanggan | Plan Agenda | Hasil"
        )
        return

    now = update.message.date.astimezone()
    hari = now.strftime("%A")
    tanggal = now.strftime("%d/%m/%Y")

    nama_sa, id_sa = get_user_info(update.effective_user.id)

    if not nama_sa:
        await update.message.reply_text("❌ Telegram ID belum terdaftar.")
        return

    no = len(sheet.get_all_values())
    inserted = 0

    for line in text.split("\n"):
        if not line.strip():
            continue

        cols = [x.strip() for x in line.split("|")]

        if len(cols) != 3:
            continue

        customer, agenda, hasil = cols

        sheet.append_row([
            no,
            hari,
            tanggal,
            customer,
            agenda,
            hasil,
            nama_sa,
            id_sa
        ])

        no += 1
        inserted += 1

    if inserted > 0:
        await update.message.reply_text(success_text)
    else:
        await update.message.reply_text("❌ Format salah.")

# =====================
# COMMANDS
# =====================
async def visitplan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await save(visitplan_sheet, update, "✅ Visit plan tersimpan.")

async def recapvisit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await save(recap_sheet, update, "✅ Recap visit tersimpan.")

async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Telegram ID kamu:\n{update.effective_user.id}")

# =====================
# START
# =====================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("visitplan", visitplan))
    app.add_handler(CommandHandler("recapvisit", recapvisit))
    app.add_handler(CommandHandler("myid", myid))

    print("🤖 BOT RUNNING")
    app.run_polling()

if __name__ == "__main__":
    main()
