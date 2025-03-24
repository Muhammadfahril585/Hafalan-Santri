
from flask import Flask
from threading import Thread
import os
import sqlite3
import datetime
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
        ["📊 Lihat Data Santri", "📅 Hafalan Bulan Lalu"],
        ["📜 Daftar Santri", "🔄 Rekap Otomatis"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Pilih menu:", reply_markup=reply_markup)

# Fungsi untuk menangani tombol menu
async def menu_handler(update: Update, context: CallbackContext) -> None:
    pesan = update.message.text

    if pesan == "➕ Tambah Hafalan":
        await update.message.reply_text("Kirim data dengan format:\nTambahHafalan; Nama Santri; Hafalan Baru (halaman); Total Hafalan (juz)")

    elif pesan == "✏️ Edit Hafalan":
        await update.message.reply_text("Kirim data dengan format:\nEditHafalan; Nama Santri; Pekan; Hafalan Baru (halaman); Total Hafalan (juz)")

    elif pesan == "📊 Lihat Data Santri":
        await update.message.reply_text("Ketik nama santri untuk melihat data hafalannya.")

    elif pesan == "📅 Hafalan Bulan Lalu":
        bulan_lalu = (datetime.datetime.now().replace(day=1) - datetime.timedelta(days=1)).strftime("%B %Y")
        cursor.execute("SELECT nama, pekan, hafalan_baru, total_juz FROM santri WHERE bulan=? ORDER BY pekan", (bulan_lalu,))
        hasil = cursor.fetchall()

        if not hasil:
            await update.message.reply_text(f"⚠️ Tidak ada data hafalan pada {bulan_lalu}.")
        else:
            pesan = f"📅 Data hafalan bulan {bulan_lalu}:\n"
            for nama, pekan, hafalan_baru, total_juz in hasil:
                total_juz_str = int(total_juz) if total_juz.is_integer() else total_juz
                pesan += f"\n👤 {nama} - Pekan {pekan}\n📖 Hafalan Baru: {hafalan_baru} Halaman\n📚 Total Hafalan: {total_juz_str} Juz\n"
            await update.message.reply_text(pesan)

    elif pesan == "📜 Daftar Santri":
        await daftar_santri(update, context)

    elif pesan == "🔄 Rekap Otomatis":
        await update.message.reply_text("🔄 Setiap laporan baru akan disimpan otomatis sesuai pekan, dan pekan akan reset jika masuk bulan baru.")

# Fungsi untuk menampilkan daftar santri yang sudah memiliki data hafalan
async def daftar_santri(update: Update, context: CallbackContext) -> None:
    cursor.execute("SELECT DISTINCT nama FROM santri ORDER BY nama")
    hasil = cursor.fetchall()

    if not hasil:
        await update.message.reply_text("⚠️ Belum ada data santri yang tersimpan.")
        return

    daftar = "\n".join(f"👤 {row[0]}" for row in hasil)
    await update.message.reply_text(f"📜 Daftar Santri yang Tersimpan:\n\n{daftar}")

# Fungsi untuk menambah hafalan
async def tambah_hafalan(update: Update, context: CallbackContext) -> None:
    try:
        pesan = update.message.text
        if not pesan.startswith("TambahHafalan;"):
            return

        parts = pesan.split(";")
        if len(parts) != 4:
            await update.message.reply_text("⚠️ Format salah! Gunakan format:\nTambahHafalan; Nama Santri; Hafalan Baru (halaman); Total Hafalan (juz)")
            return

        nama = parts[1].strip()
        hafalan_baru = int(parts[2].strip())
        total_juz = float(parts[3].strip())
        bulan_sekarang = datetime.datetime.now().strftime("%B %Y")

        cursor.execute("SELECT pekan, bulan FROM santri WHERE nama=? ORDER BY pekan DESC LIMIT 1", (nama,))
        hasil = cursor.fetchone()

        if hasil:
            last_pekan, last_bulan = hasil
            if last_bulan != bulan_sekarang:
                pekan = 1
            else:
                pekan = last_pekan + 1
        else:
            pekan = 1

        cursor.execute("INSERT INTO santri (nama, pekan, bulan, hafalan_baru, total_juz) VALUES (?, ?, ?, ?, ?)", 
                       (nama, pekan, bulan_sekarang, hafalan_baru, total_juz))
        conn.commit()

        total_juz_str = int(total_juz) if total_juz.is_integer() else total_juz

        if pekan == 4:
            cursor.execute("SELECT SUM(hafalan_baru) FROM santri WHERE nama=? AND bulan=?", (nama, bulan_sekarang))
            total_hafalan_baru = cursor.fetchone()[0]
            await update.message.reply_text(f"✅ Data lengkap 4 pekan!\nNama: {nama}\nTotal Hafalan Baru (4 pekan): {total_hafalan_baru} Halaman")
        else:
            await update.message.reply_text(f"✅ Data disimpan!\nNama: {nama}\nPekan: {pekan}\nBulan: {bulan_sekarang}\nHafalan Baru: {hafalan_baru} Halaman\nTotal Hafalan: {total_juz_str} Juz")

    except Exception as e:
        await update.message.reply_text(f"⚠️ Terjadi kesalahan: {str(e)}")

# Fungsi untuk melihat data santri
async def lihat_santri(update: Update, context: CallbackContext) -> None:
    nama = update.message.text.strip()

    cursor.execute("SELECT pekan, bulan, hafalan_baru, total_juz FROM santri WHERE nama=? ORDER BY bulan DESC, pekan DESC", (nama,))
    hasil = cursor.fetchall()

    if not hasil:
        await update.message.reply_text("⚠️ Data tidak ditemukan!")
        return

    pesan = f"📌 Data hafalan {nama}:\n"
    for pekan, bulan, hafalan_baru, total_juz in hasil:
        total_juz_str = int(total_juz) if total_juz.is_integer() else total_juz
        pesan += f"\n📅 Pekan {pekan} - {bulan}\n📖 Hafalan Baru: {hafalan_baru} Halaman\n📚 Total Hafalan: {total_juz_str} Juz\n"

    await update.message.reply_text(pesan)

# Fungsi untuk menangani perintah /start
async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("Halo! Selamat datang di bot Hafalan Santri.")
    await show_menu(update, context)

# Fungsi utama menjalankan bot
def main():
    if not TOKEN:
        print("Error: Harap atur TELEGRAM_TOKEN di environment variable")
        return

    app = Application.builder().token(TOKEN).build()

    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^(➕ Tambah Hafalan|✏️ Edit Hafalan|📊 Lihat Data Santri|📅 Hafalan Bulan Lalu|📜 Daftar Santri|🔄 Rekap Otomatis)$"), menu_handler))

    app.add_handler(CommandHandler("start", start))

    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^TambahHafalan;"), tambah_hafalan))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, lihat_santri))

    print("Bot berjalan...")
    app.run_polling()

if __name__ == "__main__":
    keep_alive()
    main()
