
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

# Fungsi untuk menambah hafalan santri
async def tambah_hafalan(update: Update, context: CallbackContext, nama, hafalan_baru, total_juz):
    sekarang = datetime.datetime.now()
    bulan_ini = sekarang.strftime("%B %Y")

    # Cek pekan terakhir dari bulan ini untuk santri yang sama
    cursor.execute("SELECT MAX(pekan) FROM santri WHERE nama=? AND bulan=?", (nama, bulan_ini))
    hasil = cursor.fetchone()
    pekan_sekarang = hasil[0] + 1 if hasil[0] else 1

    # Simpan data hafalan baru
    cursor.execute("INSERT INTO santri (nama, pekan, bulan, hafalan_baru, total_juz) VALUES (?, ?, ?, ?, ?)",
                   (nama, pekan_sekarang, bulan_ini, hafalan_baru, total_juz))
    conn.commit()

    await update.message.reply_text(f"✅ Hafalan berhasil ditambahkan:\n👤 {nama}\n📅 Pekan {pekan_sekarang}: {hafalan_baru} halaman\n📚 Total Hafalan: {total_juz} juz")

    # Jika sudah pekan ke-4, buat rekap otomatis
    if pekan_sekarang == 4:
        await rekap_bulanan(update, nama, bulan_ini)

# Fungsi untuk merekap hafalan bulanan
async def rekap_bulanan(update: Update, nama, bulan):
    cursor.execute("SELECT pekan, hafalan_baru FROM santri WHERE nama=? AND bulan=?", (nama, bulan))
    hasil = cursor.fetchall()

    if hasil:
        total_hafalan_baru = sum(row[1] for row in hasil)
        cursor.execute("SELECT total_juz FROM santri WHERE nama=? ORDER BY id DESC LIMIT 1", (nama,))
        total_juz = cursor.fetchone()[0]

        rekap = f"📅 *Rekap Hafalan Bulan {bulan}*\n👤 *Nama:* {nama}\n"
        for row in hasil:
            rekap += f"\nPekan {row[0]}: {row[1]} halaman"
        
        rekap += f"\n\n📖 *Total Hafalan Baru:* {total_hafalan_baru} halaman"
        rekap += f"\n📚 *Total Hafalan Keseluruhan:* {int(total_juz) if total_juz.is_integer() else total_juz} Juz"

        await update.message.reply_text(rekap, parse_mode="Markdown")

# Fungsi untuk menangani input dari pengguna
async def handle_input(update: Update, context: CallbackContext) -> None:
    pesan = update.message.text

    # Menangani format tambah hafalan
    if pesan.startswith("TambahHafalan;"):
        try:
            _, nama, hafalan_baru, total_juz = pesan.split(";")
            nama = nama.strip()
            hafalan_baru = int(hafalan_baru.strip())
            total_juz = float(total_juz.strip())

            await tambah_hafalan(update, context, nama, hafalan_baru, total_juz)

        except ValueError:
            await update.message.reply_text("⚠️ Format salah! Gunakan format:\nTambahHafalan; Nama Santri; Hafalan Baru (halaman); Total Hafalan (juz)")
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
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^(➕ Tambah Hafalan|📊 Lihat Data Santri|📅 Pilih Bulan Hafalan|📜 Daftar Santri|🔄 Rekap Otomatis)$"), menu_handler))
    app.add_handler(MessageHandler(filters.TEXT, handle_input))

    print("Bot berjalan...")
    app.run_polling()

if __name__ == "__main__":
    keep_alive()
    main()
