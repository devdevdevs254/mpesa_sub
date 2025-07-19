# callback_server.py
from flask import Flask, request
import json, sqlite3

app = Flask(__name__)

@app.route('/mpesa-callback', methods=['POST'])
def mpesa_callback():
    data = request.get_json()
    print("M-Pesa Callback:", json.dumps(data, indent=2))

    if data['Body']['stkCallback']['ResultCode'] == 0:
        phone = data['Body']['stkCallback']['CallbackMetadata']['Item'][4]['Value']
        # save subscription status to DB
        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET subscribed_until = date('now', '+30 days') WHERE phone = ?", (phone,))
        conn.commit()
        conn.close()

    return "OK", 200
