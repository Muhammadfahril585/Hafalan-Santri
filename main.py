
from flask import Flask, request
import os
import sqlite3
import datetime
import logging
import asyncio
from threading import Thread
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# Konfigurasi Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ambil Token dan URL Webhook dari Environment Variables
TOKEN = os.getenv("TELEGRAM_TOKEN", "")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")

# Inisialisasi Flask App
app = Flask(__name__)

# Fungsi mendapatkan bulan dan tahun saat ini
def get_bulan_tahun():
    return datetime.datetime.now().strftime("%B %Y")

# Fungsi untuk mendapatkan pekan otomatis
def get_pekan(nama_santri, bulan):
    conn = sqlite3.connect("hafalan.db")
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(pekan) FROM santri WHERE nama=? AND bulan=?", (nama_santri, bulan))
    result = cursor.fetchone()[0]
    conn.close()
    return (result + 1) if result else 1

# Fungsi untuk menampilkan menu utama
async def show_menu(update: Update, context) -> None:
    keyboard = [
        ["➕ Tambah Hafalan", "✏️ Edit Hafalan"],
        ["📊 Lihat Data Santri", "📅 Pilih Bulan Hafalan"],
        ["📜 Daftar Santri", "🔄 Rekap Otomatis"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Pilih menu:", reply_markup=reply_markup)

# Fungsi untuk menangani perintah /start
async def start(update: Update, context) -> None:
    await update.message.reply_text("Halo! Selamat datang di bot Hafalan Santri.")
    await show_menu(update, context)

# Fungsi untuk menangani pesan teks
async def handle_message(update: Update, context) -> None:
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

            # Simpan ke database
            conn = sqlite3.connect("hafalan.db")
            cursor = conn.cursor()
            cursor.execute("INSERT INTO santri (nama, pekan, bulan, hafalan_baru, total_juz) VALUES (?, ?, ?, ?, ?)",
                           (nama, pekan, bulan, hafalan_baru, total_juz))
            conn.commit()
            conn.close()

            await update.message.reply_text(f"✅ Data hafalan pekan {pekan} untuk {nama} telah disimpan.")

        except Exception as e:
            await update.message.reply_text("⚠️ Format salah! Gunakan format yang benar.")
            logger.error(f"Error processing message: {e}")

# Fungsi untuk menampilkan daftar santri
async def daftar_santri(update: Update, context) -> None:
    conn = sqlite3.connect("hafalan.db")
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT nama FROM santri ORDER BY nama")
    hasil = cursor.fetchall()
    conn.close()

    if not hasil:
        await update.message.reply_text("⚠️ Belum ada data santri yang tersimpan.")
        return

    daftar = "\n".join(f"👤 {row[0]}" for row in hasil)
    await update.message.reply_text(f"📜 Daftar Santri yang Tersimpan:\n\n{daftar}")

# Inisialisasi bot Telegram
app_telegram = Application.builder().token(TOKEN).build()
app_telegram.add_handler(CommandHandler("start", start))
app_telegram.add_handler(MessageHandler(filters.TEXT, handle_message))

# Fungsi untuk menangani webhook dari Telegram
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    try:
        update = Update.de_json(request.get_json(), app_telegram.bot)
        asyncio.run(app_telegram.process_update(update))
        return "OK", 200
    except Exception as e:
        logger.error(f"Error in webhook: {e}")
        return "Internal Server Error", 500

# Fungsi menjaga server tetap berjalan
def run():
    app.run(host="0.0.0.0", port=8080)

# Fungsi untuk mengatur webhook saat aplikasi dijalankan
async def set_webhook():
    await app_telegram.bot.set_webhook(f"{WEBHOOK_URL}/{TOKEN}")
    logger.info("Webhook telah diatur!")

# Menjalankan bot dan server Flask
if __name__ == "__main__":
    # Buat thread Flask agar tidak mengganggu event loop utama
    thread = Thread(target=run)
    thread.start()

    # Atur webhook di event loop utama
    asyncio.run(set_webhook())
