
from flask import Flask
from threading import Thread
import os
import sqlite3
import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, ConversationHandler

TOKEN = os.environ.get("TELEGRAM_TOKEN", "")

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
                    total_juz REAL)''')
conn.commit()

# Variabel status untuk ConversationHandler
PILIH_BULAN, PILIH_NAMA = range(2)

# Fungsi menjaga bot tetap berjalan
def run():
    app.run(host="0.0.0.0", port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

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

# Fungsi untuk menangani tombol menu
async def menu_handler(update: Update, context: CallbackContext) -> None:
    pesan = update.message.text

    if pesan == "➕ Tambah Hafalan":
        await update.message.reply_text("Kirim data dengan format:\nTambahHafalan; Nama Santri; Hafalan Baru (halaman); Total Hafalan (juz)")

    elif pesan == "✏️ Edit Hafalan":
        await update.message.reply_text("Kirim data dengan format:\nEditHafalan; Nama Santri; Pekan; Hafalan Baru (halaman); Total Hafalan (juz)")

    elif pesan == "📊 Lihat Data Santri":
        await update.message.reply_text("Ketik nama santri untuk melihat data hafalannya.")

    elif pesan == "📅 Pilih Bulan Hafalan":
        await update.message.reply_text("Ketik nama bulan dan tahun (misal: Januari 2025) untuk melihat data hafalan.")
        return PILIH_BULAN  # Memulai percakapan

    elif pesan == "📜 Daftar Santri":
        await daftar_santri(update, context)

    elif pesan == "🔄 Rekap Otomatis":
        await update.message.reply_text("🔄 Setiap laporan baru akan disimpan otomatis sesuai pekan, dan pekan akan reset jika masuk bulan baru.")

# Fungsi menangani input bulan hafalan
async def pilih_bulan(update: Update, context: CallbackContext) -> int:
    context.user_data["bulan_hafalan"] = update.message.text
    await update.message.reply_text("Masukkan nama santri yang ingin Anda lihat hafalannya:")
    return PILIH_NAMA  # Lanjut ke tahap berikutnya

# Fungsi menangani input nama santri setelah memilih bulan
async def pilih_nama(update: Update, context: CallbackContext) -> int:
    bulan = context.user_data.get("bulan_hafalan")
    nama_santri = update.message.text

    cursor.execute("SELECT pekan, hafalan_baru, total_juz FROM santri WHERE bulan = ? AND nama = ?", (bulan, nama_santri))
    hasil = cursor.fetchall()

    if not hasil:
        await update.message.reply_text(f"⚠️ Tidak ada data hafalan untuk {nama_santri} di bulan {bulan}.")
    else:
        pesan = f"📅 Hafalan {nama_santri} di bulan {bulan}:\n"
        for pekan, hafalan_baru, total_juz in hasil:
            pesan += f"🔹 Pekan {pekan}: {hafalan_baru} halaman (Total: {total_juz} juz)\n"
        await update.message.reply_text(pesan)

    return ConversationHandler.END  # Mengakhiri percakapan

# Fungsi untuk menampilkan daftar santri yang sudah memiliki data hafalan
async def daftar_santri(update: Update, context: CallbackContext) -> None:
    cursor.execute("SELECT DISTINCT nama FROM santri ORDER BY nama")
    hasil = cursor.fetchall()

    if not hasil:
        await update.message.reply_text("⚠️ Belum ada data santri yang tersimpan.")
        return

    daftar = "\n".join(f"👤 {row[0]}" for row in hasil)
    await update.message.reply_text(f"📜 Daftar Santri yang Tersimpan:\n\n{daftar}")

# Fungsi utama menjalankan bot
def main():
    if not TOKEN:
        print("Error: Harap atur TELEGRAM_TOKEN di environment variable")
        return

    app = Application.builder().token(TOKEN).build()

    # ConversationHandler untuk memilih bulan hafalan
    pilih_bulan_hafalan = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & filters.Regex("^📅 Pilih Bulan Hafalan$"), menu_handler)],
        states={
            PILIH_BULAN: [MessageHandler(filters.TEXT & ~filters.COMMAND, pilih_bulan)],
            PILIH_NAMA: [MessageHandler(filters.TEXT & ~filters.COMMAND, pilih_nama)]
        },
        fallbacks=[]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(pilih_bulan_hafalan)
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^(➕ Tambah Hafalan|✏️ Edit Hafalan|📊 Lihat Data Santri|📜 Daftar Santri|🔄 Rekap Otomatis)$"), menu_handler))

    print("Bot berjalan...")
    app.run_polling()

if __name__ == "__main__":
    keep_alive()
    main()
