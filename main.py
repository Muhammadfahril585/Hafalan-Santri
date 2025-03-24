
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
                    total_juz INTEGER)''')
conn.commit()

# Fungsi menjaga bot tetap berjalan
def run():
    app.run(host="0.0.0.0", port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# Fungsi untuk mendapatkan bulan dan tahun saat ini
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
        bulan_sekarang = get_bulan_tahun()
        await rekap_otomatis(update, context, bulan_sekarang)

# Fungsi untuk menangani input dari pengguna
async def handle_input(update: Update, context: CallbackContext) -> None:
    pesan = update.message.text
    print(f"Pesan diterima: {pesan}")  # Debugging untuk melihat apakah bot menerima pesan

    # Jika user dalam mode pilih bulan hafalan
    if context.user_data.get("mode") == "pilih_bulan":
        context.user_data["bulan_hafalan"] = pesan
        await update.message.reply_text("Masukkan nama santri yang ingin Anda lihat hafalannya:")
        context.user_data["mode"] = "pilih_santri"
        return

    # Jika user sudah memilih bulan, minta nama santri
    if context.user_data.get("mode") == "pilih_santri":
        bulan = context.user_data.get("bulan_hafalan", "")
        nama_santri = pesan

        cursor.execute("SELECT pekan, hafalan_baru, total_juz FROM santri WHERE nama=? AND bulan=?", (nama_santri, bulan))
        hasil = cursor.fetchall()

        if hasil:
            data_hafalan = "\n".join([f"Pekan {row[0]}: {row[1]} halaman, Total: {row[2]} juz" for row in hasil])
            await update.message.reply_text(f"📅 Hafalan {nama_santri} di {bulan}:\n\n{data_hafalan}")
        else:
            await update.message.reply_text(f"⚠️ Tidak ada data hafalan untuk {nama_santri} di bulan {bulan}.")

        context.user_data.clear()
        return

    # Jika user memasukkan data tambah hafalan
    if pesan.startswith("TambahHafalan;"):
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

            if pekan == 4:
                await rekap_otomatis(update, context, bulan, nama)

        except Exception as e:
            await update.message.reply_text(f"⚠️ Format salah! Gunakan format:\nTambahHafalan; Nama; Halaman; Juz")
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

# Fungsi untuk merekap hafalan otomatis di akhir bulan
async def rekap_otomatis(update: Update, context: CallbackContext, bulan, nama_santri=None):
    if nama_santri:
        cursor.execute("SELECT SUM(hafalan_baru), MAX(total_juz) FROM santri WHERE nama=? AND bulan=?", (nama_santri, bulan))
    else:
        cursor.execute("SELECT nama, SUM(hafalan_baru), MAX(total_juz) FROM santri WHERE bulan=? GROUP BY nama", (bulan,))

    hasil = cursor.fetchall()

    if not hasil:
        return

    pesan = f"📅 Rekap Hafalan Bulan {bulan}\n"
    for row in hasil:
        nama = row[0]
        total_hafalan = row[1]
        total_juz = row[2]

        pesan += f"\n👤 Nama: {nama}\n📖 Total Hafalan Baru: {total_hafalan} halaman\n📚 Total Hafalan Keseluruhan: {total_juz} Juz\n"

    await update.message.reply_text(pesan)

# Fungsi utama menjalankan bot
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler))  # Menangani tombol menu
    app.add_handler(MessageHandler(filters.TEXT, handle_input))  # Menangani input teks biasa
    print("Bot berjalan...")
    app.run_polling()

if __name__ == "__main__":
    keep_alive()
    main()
