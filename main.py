
from flask import Flask
from threading import Thread
import os
import sqlite3
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

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
        await update.message.reply_text("Silakan masukkan nama santri:")
        context.user_data["mode"] = "lihat_santri"

    elif pesan == "📅 Pilih Bulan Hafalan":
        await update.message.reply_text("Ketik nama bulan dan tahun (misal: Januari 2025) untuk melihat data hafalan.")
        context.user_data["mode"] = "pilih_bulan"

    elif pesan == "📜 Daftar Santri":
        await daftar_santri(update, context)

    elif pesan == "🔄 Rekap Otomatis":
        await update.message.reply_text("🔄 Setiap laporan baru akan disimpan otomatis sesuai pekan, dan pekan akan reset jika masuk bulan baru.")

# Fungsi untuk menangani input dari pengguna
async def handle_input(update: Update, context: CallbackContext) -> None:
    pesan = update.message.text

    # Jika user sedang memilih bulan hafalan
    if "mode" in context.user_data and context.user_data["mode"] == "pilih_bulan":
        context.user_data["bulan_hafalan"] = pesan
        await update.message.reply_text("Masukkan nama santri yang ingin Anda lihat hafalannya:")
        context.user_data["mode"] = "pilih_santri"
        return

    # Jika user sudah memilih bulan, minta nama santri
    if "mode" in context.user_data and context.user_data["mode"] == "pilih_santri":
        bulan = context.user_data.get("bulan_hafalan", "")
        nama_santri = pesan

        cursor.execute("SELECT pekan, hafalan_baru, total_juz FROM santri WHERE nama=? AND bulan=?", (nama_santri, bulan))
        hasil = cursor.fetchall()

        if hasil:
            data_hafalan = "\n".join([
                f"Pekan {row[0]}: {row[1]} halaman, Total: {int(row[2]) if row[2].is_integer() else row[2]} juz"
                for row in hasil
            ])
            await update.message.reply_text(f"📅 Hafalan {nama_santri} di {bulan}:\n\n{data_hafalan}")
        else:
            await update.message.reply_text(f"⚠️ Tidak ada data hafalan untuk {nama_santri} di bulan {bulan}.")

        # Reset mode agar tidak terjadi kesalahan input berikutnya
        context.user_data.pop("mode", None)
        context.user_data.pop("bulan_hafalan", None)
        return

    # Jika user memilih "📊 Lihat Data Santri" lalu mengetik nama santri
    if "mode" in context.user_data and context.user_data["mode"] == "lihat_santri":
        nama_santri = pesan

        cursor.execute("SELECT bulan, pekan, hafalan_baru, total_juz FROM santri WHERE nama=? ORDER BY bulan, pekan", (nama_santri,))
        hasil = cursor.fetchall()

        if hasil:
            data_hafalan = "\n".join([
                f"📅 {row[0]} - Pekan {row[1]}: {row[2]} halaman, Total: {int(row[3]) if row[3].is_integer() else row[3]} juz"
                for row in hasil
            ])
            await update.message.reply_text(f"📊 Hafalan {nama_santri}:\n\n{data_hafalan}")
        else:
            await update.message.reply_text(f"⚠️ Tidak ada data hafalan untuk {nama_santri}.")

        # Reset mode agar tidak terjadi kesalahan input berikutnya
        context.user_data.pop("mode", None)
        return

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

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^(➕ Tambah Hafalan|✏️ Edit Hafalan|📊 Lihat Data Santri|📅 Pilih Bulan Hafalan|📜 Daftar Santri|🔄 Rekap Otomatis)$"), menu_handler))
    app.add_handler(MessageHandler(filters.TEXT, handle_input))

    print("Bot berjalan...")
    app.run_polling()

if __name__ == "__main__":
    keep_alive()
    main()
