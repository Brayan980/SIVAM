import sqlite3
conn = sqlite3.connect('clinica.db')
cursor = conn.cursor()
cursor.execute('SELECT name FROM sqlite_master WHERE type="table"')
print([row[0] for row in cursor.fetchall()])
conn.close()
