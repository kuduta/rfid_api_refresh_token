import sqlite3

conn = sqlite3.connect("users.db")
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL
)
''')

cursor.execute("INSERT OR IGNORE INTO users (username, password) VALUES (?, ?)", ("rpitest", "secret123"))
conn.commit()
conn.close()
print("✅ Created users.db and added user.")