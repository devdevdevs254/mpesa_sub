#active_user.py
# check if user is active
import sqlite3
from datetime import datetime

def is_subscribed(phone):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT subscribed_until FROM users WHERE phone = ?", (phone,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return datetime.strptime(row[0], "%Y-%m-%d") >= datetime.today()
    return False
