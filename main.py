
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
        await update.message.reply_text("Ketik nama santri untuk melihat data hafalannya.")

    elif pesan == "📅 Pilih Bulan Hafalan":
        await update.message.reply_text("Masukkan nama santri yang ingin dicek hafalannya:")
        context.user_data["pilih_bulan_hafalan"] = True  # Tandai bahwa pengguna sedang memilih bulan hafalan

    elif pesan == "📜 Daftar Santri":
        await daftar_santri(update, context)

    elif pesan == "🔄 Rekap Otomatis":
        await update.message.reply_text("🔄 Setiap laporan baru akan disimpan otomatis sesuai pekan, dan pekan akan reset jika masuk bulan baru.")

# Fungsi untuk menangani input nama santri dan bulan hafalan
async def input_handler(update: Update, context: CallbackContext) -> None:
    if context.user_data.get("pilih_bulan_hafalan"):
        context.user_data["nama_santri"] = update.message.text.strip()
        await update.message.reply_text("Masukkan bulan dan tahun (misal: Januari 2025):")
        context.user_data["tunggu_bulan"] = True  # Tandai bahwa selanjutnya pengguna harus memasukkan bulan
        return

    if context.user_data.get("tunggu_bulan"):
        nama_santri = context.user_data.get("nama_santri")
        bulan_dicari = update.message.text.strip()

        # Cari data hafalan berdasarkan nama santri dan bulan
        cursor.execute("SELECT pekan, hafalan_baru, total_juz FROM santri WHERE nama=? AND bulan=? ORDER BY pekan", 
                       (nama_santri, bulan_dicari))
        hasil = cursor.fetchall()

        if not hasil:
            await update.message.reply_text(f"⚠️ Tidak ada data hafalan untuk {nama_santri} di {bulan_dicari}.")
        else:
            pesan = f"📅 Data hafalan {nama_santri} pada {bulan_dicari}:\n"
            for pekan, hafalan_baru, total_juz in hasil:
                total_juz_str = int(total_juz) if total_juz.is_integer() else total_juz
                pesan += f"\n📅 Pekan {pekan}\n📖 Hafalan Baru: {hafalan_baru} Halaman\n📚 Total Hafalan: {total_juz_str} Juz\n"
            
            await update.message.reply_text(pesan)

        # Reset state agar bot tidak terus menunggu input
        context.user_data["pilih_bulan_hafalan"] = False
        context.user_data["tunggu_bulan"] = False

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
    app.add_handler(MessageHandler(filters.TEXT, input_handler))  # Handler untuk input nama santri dan bulan

    print("Bot berjalan...")
    app.run_polling()

if __name__ == "__main__":
    keep_alive()
    main()
