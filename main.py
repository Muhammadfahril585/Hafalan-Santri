
from flask import Flask, request
from threading import Thread
import os
import sqlite3
import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "")  # Isi dengan URL webhook kamu

app = Flask(__name__)
conn = sqlite3.connect("hafalan.db", check_same_thread=False)
cursor = conn.cursor()

# Membuat tabel jika belum ada
cursor.execute('''CREATE TABLE IF NOT EXISTS santri (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nama TEXT,
                    pekan INTEGER,
                    bulan TEXT,
                    hafalan_baru INTEGER,
                    total_juz INTEGER)''')
conn.commit()

# Fungsi mendapatkan bulan dan tahun saat ini
def get_bulan_tahun():
    return datetime.datetime.now().strftime("%B %Y")

# Fungsi untuk mendapatkan pekan otomatis
def get_pekan(nama_santri, bulan):
    cursor.execute("SELECT MAX(pekan) FROM santri WHERE nama=? AND bulan=?", (nama_santri, bulan))
    result = cursor.fetchone()[0]
    return (result + 1) if result else 1

# Fungsi untuk menampilkan menu utama
async def show_menu(update: Update, context: CallbackContext) -> None:
    keyboard = [
        ["➕ Tambah Hafalan", "✏️ Edit Hafalan"],
        ["📊 Lihat Data Santri", "📅 Pilih Bulan Hafalan"],
        ["📜 Daftar Santri", "🔄 Rekap Otomatis"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Pilih menu:", reply_markup=reply_markup)

# Fungsi untuk menangani perintah /start
async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("Halo! Selamat datang di bot Hafalan Santri.")
    await show_menu(update, context)

# Fungsi untuk menangani pesan teks
async def handle_message(update: Update, context: CallbackContext) -> None:
    pesan = update.message.text

    if pesan == "➕ Tambah Hafalan":
        await update.message.reply_text("Kirim data dengan format:\nTambahHafalan; Nama Santri; Hafalan Baru (halaman); Total Hafalan (juz)")
    
    elif pesan == "✏️ Edit Hafalan":
        await update.message.reply_text("Kirim data dengan format:\nEditHafalan; Nama Santri; Pekan; Hafalan Baru (halaman); Total Hafalan (juz)")
    
    elif pesan == "📜 Daftar Santri":
        await daftar_santri(update, context)
    
    elif pesan.startswith("TambahHafalan;"):
        try:
            _, nama, hafalan_baru, total_juz = pesan.split(";")
            nama = nama.strip()
            hafalan_baru = int(hafalan_baru.strip())
            total_juz = int(total_juz.strip())

            bulan = get_bulan_tahun()
            pekan = get_pekan(nama, bulan)

            cursor.execute("INSERT INTO santri (nama, pekan, bulan, hafalan_baru, total_juz) VALUES (?, ?, ?, ?, ?)",
                           (nama, pekan, bulan, hafalan_baru, total_juz))
            conn.commit()

            await update.message.reply_text(f"✅ Data hafalan pekan {pekan} untuk {nama} telah disimpan.")

        except Exception as e:
            await update.message.reply_text("⚠️ Format salah! Gunakan format yang benar.")
            print(e)

# Fungsi untuk menampilkan daftar santri
async def daftar_santri(update: Update, context: CallbackContext) -> None:
    cursor.execute("SELECT DISTINCT nama FROM santri ORDER BY nama")
    hasil = cursor.fetchall()

    if not hasil:
        await update.message.reply_text("⚠️ Belum ada data santri yang tersimpan.")
        return

    daftar = "\n".join(f"👤 {row[0]}" for row in hasil)
    await update.message.reply_text(f"📜 Daftar Santri yang Tersimpan:\n\n{daftar}")

# Inisialisasi aplikasi bot Telegram
app_telegram = Application.builder().token(TOKEN).build()
app_telegram.add_handler(CommandHandler("start", start))
app_telegram.add_handler(MessageHandler(filters.TEXT, handle_message))

# Fungsi untuk menangani webhook dari Telegram
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(), app_telegram.bot)
    app_telegram.process_update(update)
    return "OK", 200

# Fungsi menjaga server tetap berjalan
def run():
    app.run(host="0.0.0.0", port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# Fungsi utama untuk mengatur webhook
async def set_webhook():
    await app_telegram.bot.set_webhook(f"{WEBHOOK_URL}/{TOKEN}")
    print("Webhook telah diatur!")

if __name__ == "__main__":
    keep_alive()
    app_telegram.run_webhook(
        listen="0.0.0.0",
        port=8080,
        webhook_url=f"{WEBHOOK_URL}/{TOKEN}"
          )
