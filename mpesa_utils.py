import requests
import base64
import json
import sqlite3
import os
from datetime import datetime
from fastapi import FastAPI, Request
from dateutil import tz
import smtplib
from email.message import EmailMessage
import streamlit as st

DB_FILE = "callbacks.db"
CALLBACK_TABLE = "mpesa_callbacks"

# Load secrets from Streamlit
def get_secret(key, section=None):
    if section:
        return st.secrets[section][key]
    return st.secrets[key]

# 1. Initialize SQLite DB
def init_db():
    if not os.path.exists(DB_FILE):
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {CALLBACK_TABLE} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    phone TEXT,
                    amount TEXT,
                    status TEXT,
                    timestamp TEXT
                );
            """)
            conn.commit()

# 2. Save callback to DB
def save_callback(phone, amount, status, timestamp):
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(f"""
            INSERT INTO {CALLBACK_TABLE} (phone, amount, status, timestamp)
            VALUES (?, ?, ?, ?)
        """, (phone, amount, status, timestamp))
        conn.commit()

# 3. Display all callbacks
def display_callbacks():
    st.subheader("📋 Payment Callback Logs")
    with sqlite3.connect(DB_FILE) as conn:
        rows = conn.execute(f"SELECT * FROM {CALLBACK_TABLE} ORDER BY id DESC").fetchall()
        if rows:
            st.table(rows)
        else:
            st.info("No callbacks yet.")

# 4. Generate M-PESA access token
def get_access_token():
    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    consumer_key = get_secret("CONSUMER_KEY")
    consumer_secret = get_secret("CONSUMER_SECRET")

    auth = base64.b64encode(f"{consumer_key}:{consumer_secret}".encode()).decode()
    headers = {"Authorization": f"Basic {auth}"}
    response = requests.get(url, headers=headers).json()

    return response.get("access_token")

# 5. STK Push Logic
def initiate_stk_push(phone, amount):
    access_token = get_access_token()
    if not access_token:
        return {"error": "Failed to get access token"}

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    shortcode = get_secret("BUSINESS_SHORTCODE")
    passkey = get_secret("PASSKEY")
    password = base64.b64encode(f"{shortcode}{passkey}{timestamp}".encode()).decode()

    payload = {
        "BusinessShortCode": shortcode,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(amount),
        "PartyA": phone,
        "PartyB": shortcode,
        "PhoneNumber": phone,
        "CallBackURL": get_secret("CALLBACK_URL"),
        "AccountReference": "MpesaSub",
        "TransactionDesc": "Mpesa Subscription"
    }

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
    return requests.post(url, json=payload, headers=headers).json()

# 6. Send Email Notification
def send_email_alert(phone, amount, status, timestamp):
    msg = EmailMessage()
    msg["Subject"] = "✅ M-PESA Payment Received"
    msg["From"] = get_secret("EMAIL_USERNAME", "email")
    msg["To"] = get_secret("EMAIL_TO", "email")
    msg.set_content(f"""
M-PESA Payment Callback:

Phone: {phone}
Amount: {amount}
Status: {status}
Time: {timestamp}
""")

    with smtplib.SMTP(get_secret("EMAIL_HOST", "email"), int(get_secret("EMAIL_PORT", "email"))) as server:
        server.starttls()
        server.login(get_secret("EMAIL_USERNAME", "email"), get_secret("EMAIL_PASSWORD", "email"))
        server.send_message(msg)

# 7. FastAPI App for callbacks
app = FastAPI()

@app.post("/callback")
async def mpesa_callback(request: Request):
    body = await request.json()
    try:
        data = body["Body"]["stkCallback"]
        result_code = data["ResultCode"]
        status = "Success" if result_code == 0 else "Failed"
        metadata = data.get("CallbackMetadata", {}).get("Item", [])

        phone = next((item["Value"] for item in metadata if item["Name"] == "PhoneNumber"), None)
        amount = next((item["Value"] for item in metadata if item["Name"] == "Amount"), None)

        # Convert timestamp
        timestamp = datetime.now(tz=tz.tzlocal()).strftime("%Y-%m-%d %H:%M:%S")
        save_callback(phone, amount, status, timestamp)

        if status == "Success":
            send_email_alert(phone, amount, status, timestamp)

        return {"ResultCode": 0, "ResultDesc": "Callback received successfully"}
    except Exception as e:
        return {"ResultCode": 1, "ResultDesc": f"Error processing callback: {str(e)}"}
