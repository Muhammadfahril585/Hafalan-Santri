import sqlite3

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
print("✅ Database berhasil dibuat atau sudah ada!")
