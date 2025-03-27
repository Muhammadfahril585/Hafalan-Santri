import sqlite3

with sqlite3.connect("hafalan.db") as conn:
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS santri (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nama_santri TEXT,
                        hafalan_baru INTEGER,
                        total_hafalan INTEGER,
                        pekan INTEGER,
                        bulan TEXT)''')
    conn.commit()

print("✅ Database berhasil dibuat atau sudah ada!")
