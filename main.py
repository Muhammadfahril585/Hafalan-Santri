
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
import sqlite3
from datetime import datetime

TOKEN = "YOUR_BOT_TOKEN"  # Ganti dengan token bot Anda
bot = telebot.TeleBot(TOKEN)

# Fungsi untuk membuat database jika belum ada
def init_db():
    conn = sqlite3.connect("hafalan.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS santri (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nama_santri TEXT,
                        hafalan_baru INTEGER,
                        total_hafalan INTEGER,
                        pekan INTEGER,
                        bulan TEXT)''')
    conn.commit()
    conn.close()

# Fungsi untuk menyusun menu utama
def menu_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("➕ Tambah Hafalan"))
    markup.add(KeyboardButton("📊 Data Hafalan Santri"))
    markup.add(KeyboardButton("📅 Lihat Hafalan Berdasarkan Bulan"))
    markup.add(KeyboardButton("📜 Daftar Nama Santri"))
    return markup

# Fungsi untuk menambah hafalan santri
def tambah_hafalan(nama, hafalan_baru, total_hafalan, pekan, bulan):
    conn = sqlite3.connect("hafalan.db")
    cursor = conn.cursor()

    # Cek apakah santri sudah ada di pekan tersebut
    cursor.execute("SELECT hafalan_baru FROM santri WHERE nama_santri=? AND pekan=? AND bulan=?", (nama, pekan, bulan))
    result = cursor.fetchone()

    if result:
        total_baru = result[0] + hafalan_baru
        cursor.execute("UPDATE santri SET hafalan_baru=?, total_hafalan=? WHERE nama_santri=? AND pekan=? AND bulan=?",
                       (total_baru, total_hafalan, nama, pekan, bulan))
    else:
        cursor.execute("INSERT INTO santri (nama_santri, hafalan_baru, total_hafalan, pekan, bulan) VALUES (?, ?, ?, ?, ?)",
                       (nama, hafalan_baru, total_hafalan, pekan, bulan))

    conn.commit()
    conn.close()

# Fungsi untuk melihat hafalan selama 1 bulan
def lihat_hafalan_bulanan(nama, bulan):
    conn = sqlite3.connect("hafalan.db")
    cursor = conn.cursor()
    cursor.execute("SELECT pekan, hafalan_baru, total_hafalan FROM santri WHERE nama_santri=? AND bulan=?", (nama, bulan))
    results = cursor.fetchall()
    conn.close()

    if not results:
        return "Data tidak ditemukan."

    pesan = f"📅 Hafalan {nama} bulan {bulan}:\n"
    total_bulanan = 0
    for row in results:
        pesan += f"Pekan {row[0]}: {row[1]} halaman\n"
        total_bulanan += row[1]
    
    pesan += f"📊 Total Hafalan Baru: {total_bulanan} halaman"
    return pesan

# Fungsi untuk mendapatkan daftar santri
def daftar_santri():
    conn = sqlite3.connect("hafalan.db")
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT nama_santri FROM santri")
    results = cursor.fetchall()
    conn.close()

    if not results:
        return "Belum ada santri yang terdaftar."

    pesan = "📜 *Daftar Nama Santri Pondok Pesantren Al Itqon* 📜\n"
    for row in results:
        pesan += f"- {row[0]}\n"
    
    return pesan

# Handler untuk menu utama
@bot.message_handler(commands=['start'])
def handle_start(message):
    bot.send_message(message.chat.id, "Selamat datang! Pilih menu di bawah untuk mengelola data hafalan santri.", reply_markup=menu_keyboard())

# Handler tombol menu
@bot.message_handler(func=lambda message: message.text in ["➕ Tambah Hafalan", "📊 Data Hafalan Santri", "📅 Lihat Hafalan Berdasarkan Bulan", "📜 Daftar Nama Santri"])
def handle_menu(message):
    chat_id = message.chat.id
    if message.text == "➕ Tambah Hafalan":
        bot.send_message(chat_id, "Masukkan data hafalan dengan format:\n*Nama* - *Hafalan Baru* - *Pekan* - *Total Hafalan* (Juz)\nContoh: *Ahmad - 5 - 2 - 3*", parse_mode="Markdown")
    elif message.text == "📊 Data Hafalan Santri":
        bot.send_message(chat_id, "Masukkan nama santri untuk melihat hafalan bulanan:\nContoh: *Ahmad*", parse_mode="Markdown")
    elif message.text == "📅 Lihat Hafalan Berdasarkan Bulan":
        bot.send_message(chat_id, "Masukkan nama santri dan bulan:\nContoh: *Ahmad - Februari*", parse_mode="Markdown")
    elif message.text == "📜 Daftar Nama Santri":
        bot.send_message(chat_id, daftar_santri(), parse_mode="Markdown")

# Handler input data hafalan
@bot.message_handler(func=lambda message: "-" in message.text)
def handle_hafalan_input(message):
    try:
        chat_id = message.chat.id
        data = message.text.split(" - ")
        if len(data) == 4:  # Tambah Hafalan
            nama, hafalan_baru, pekan, total_hafalan = data
            bulan = datetime.now().strftime("%B")
            tambah_hafalan(nama, int(hafalan_baru), int(total_hafalan), int(pekan), bulan)
            bot.send_message(chat_id, f"✅ Hafalan santri *{nama}* telah ditambahkan!", parse_mode="Markdown")
        elif len(data) == 2:  # Lihat Hafalan Berdasarkan Bulan
            nama, bulan = data
            pesan = lihat_hafalan_bulanan(nama, bulan)
            bot.send_message(chat_id, pesan, parse_mode="Markdown")
    except:
        bot.send_message(chat_id, "❌ Format salah! Periksa kembali input Anda.")

# Menjalankan bot
if __name__ == "__main__":
    init_db()  # Inisialisasi database
    bot.polling()
