import os
import json
from datetime import datetime

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv

# =====================
# LOAD ENV
# =====================
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
SHEET_ID = os.getenv("SHEET_ID")
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")

print("🔥 BOT PAKAI SHEET_ID:", SHEET_ID)

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN belum di-set")

if not SHEET_ID:
    raise ValueError("❌ SHEET_ID belum di-set")

if not GOOGLE_CREDENTIALS_JSON:
    raise ValueError("❌ GOOGLE_CREDENTIALS_JSON belum di-set")

# =====================
# GOOGLE SHEET
# =====================
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)

creds = ServiceAccountCredentials.from_json_keyfile_dict(
    creds_dict, scope
)

client = gspread.authorize(creds)
spreadsheet = client.open_by_key(SHEET_ID)

# =====================
# WORKSHEETS
# =====================
try:
    sheet = spreadsheet.worksheet("recapvisit")
except gspread.exceptions.WorksheetNotFound:
    sheet = spreadsheet.add_worksheet(
        title="recapvisit", rows=1000, cols=10
    )

try:
    user_sheet = spreadsheet.worksheet("id_telegram")
except gspread.exceptions.WorksheetNotFound:
    user_sheet = spreadsheet.add_worksheet(
        title="id_telegram", rows=100, cols=1
    )
    user_sheet.update("A1", [["user_id"]])

# =====================
# HEADER
# =====================
HEADER = [
    "No", "Hari", "Tanggal",
    "Customer", "Jenis Kegiatan",
    "Aktivitas", "Hasil",
    "SA", "ID SA", "Status"
]

if sheet.row_values(1) != HEADER:
    sheet.update("A1:J1", [HEADER])

# =====================
# AKSES USER
# =====================
def is_user_allowed(user_id: int) -> bool:
    ids = user_sheet.col_values(1)[1:]
    if not ids:
        return True
    return str(user_id) in ids

# =====================
# /recapvisit
# =====================
async def recapvisit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_user_allowed(update.effective_user.id):
        return

    text = update.message.text.replace("/recapvisit", "").strip()

    if not text:
        await update.message.reply_text(
            "Format:\n"
            "Customer | Jenis | Aktivitas | Hasil | SA | ID SA | Tanggal | Status\n\n"
            "Contoh:\n"
            "PT ABC | Visit | Survey | OK | Andi | SA001 | 29/01/2026 | -"
        )
        return

    data_existing = sheet.get_all_values()[1:]
    success, failed = 0, 0

    for line in text.split("\n"):
        parts = [p.strip() for p in line.split("|")]

        if len(parts) != 8:
            failed += 1
            continue

        customer, jenis, aktivitas, hasil, sa, id_sa, tanggal_str, status = parts

        try:
            tanggal = datetime.strptime(tanggal_str, "%d/%m/%Y")
            hari = tanggal.strftime("%A")
        except ValueError:
            failed += 1
            continue

        if not status:
            status = "-"

        found_row = None

        for idx, r in enumerate(data_existing, start=2):
            if (
                r[2] == tanggal_str and
                r[3] == customer and
                r[4] == jenis and
                r[5] == aktivitas
            ):
                found_row = idx
                break

        if found_row:
            sheet.update(
                f"G{found_row}:J{found_row}",
                [[hasil, sa, id_sa, status]]
            )
        else:
            new_no = len(sheet.get_all_values())
            sheet.append_row([
                new_no, hari, tanggal_str,
                customer, jenis, aktivitas,
                hasil, sa, id_sa, status
            ])

        success += 1

    await update.message.reply_text(
        f"✅ Berhasil: {success}\n❌ Gagal: {failed}"
    )

# =====================
# /cek DD/MM/YYYY
# =====================
async def cek(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_user_allowed(update.effective_user.id):
        return

    tanggal_str = update.message.text.replace("/cek", "").strip()

    try:
        target = datetime.strptime(tanggal_str, "%d/%m/%Y")
    except ValueError:
        await update.message.reply_text(
            "❌ Format salah.\nContoh: /cek 30/01/2026"
        )
        return

    data = sheet.get_all_values()[1:]
    unik = {}

    for r in data:
        if len(r) < 10:
            continue
        if r[2] != tanggal_str:
            continue
        key = (r[2], r[3], r[4], r[5])
        unik[key] = r

    if not unik:
        await update.message.reply_text(
            f"📅 {tanggal_str} ({target.strftime('%A')})\n\nTidak ada kegiatan."
        )
        return

    reply = f"📅 {tanggal_str} ({target.strftime('%A')})\n\n"

    for i, r in enumerate(unik.values(), start=1):
        status = r[9] if r[9].strip() else "-"
        reply += (
            f"{i}. {r[3]}\n"
            f"   {r[4]} | {r[5]}\n"
            f"   Hasil: {r[6]}\n"
            f"   Status: {status}\n\n"
        )

    await update.message.reply_text(reply)

# =====================
# START BOT
# =====================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("recapvisit", recapvisit))
    app.add_handler(CommandHandler("cek", cek))

    print("🤖 YOVI TWO BOT AKTIF")
    app.run_polling()

if __name__ == "__main__":
    main()
