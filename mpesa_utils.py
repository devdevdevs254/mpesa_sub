import requests
import base64
import datetime
import sqlite3
import streamlit as st
from fastapi import FastAPI, Request
import uvicorn
import json
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# 🔐 Validate required secrets
required_keys = ["CONSUMER_KEY", "CONSUMER_SECRET", "BUSINESS_SHORTCODE", "PASSKEY", "CALLBACK_URL"]
for key in required_keys:
    if key not in st.secrets:
        raise KeyError(f"Missing secret: {key}")

# 💳 Get OAuth token
def get_token():
    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    try:
        response = requests.get(
            url,
            auth=(st.secrets["CONSUMER_KEY"], st.secrets["CONSUMER_SECRET"])
        )
        response.raise_for_status()
        return response.json()["access_token"]
    except Exception as e:
        st.error("Token request failed")
        raise e


# 💰 Initiate STK Push
def initiate_stk_push(phone: str, amount: int):
    if not phone.startswith("254") or len(phone) != 12:
        return {"status": "error", "error": "Invalid phone. Format: 2547XXXXXXXX"}

    shortcode = st.secrets["BUSINESS_SHORTCODE"]
    passkey = st.secrets["PASSKEY"]
    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    password = base64.b64encode((shortcode + passkey + timestamp).encode()).decode()

    payload = {
        "BusinessShortCode": shortcode,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount,
        "PartyA": phone,
        "PartyB": shortcode,
        "PhoneNumber": phone,
        "CallBackURL": st.secrets["CALLBACK_URL"],
        "AccountReference": "TestRef",
        "TransactionDesc": "Test Payment"
    }

    headers = {
        "Authorization": f"Bearer {get_token()}",
        "Content-Type": "application/json"
    }

    try:
        res = requests.post(
            "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest",
            headers=headers,
            json=payload
        )
        res.raise_for_status()
        return {"status": "sent", "response": res.json()}
    except requests.exceptions.RequestException as e:
        return {"status": "error", "error": str(e), "details": res.text if res else "No response"}


# 🔌 SQLite: Save callbacks
def init_db():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect("data/callbacks.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS callbacks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            received_at TEXT,
            payload TEXT
        )
    """)
    conn.commit()
    conn.close()


def save_callback_to_db(payload):
    conn = sqlite3.connect("data/callbacks.db")
    c = conn.cursor()
    c.execute("INSERT INTO callbacks (received_at, payload) VALUES (?, ?)",
              (datetime.datetime.now().isoformat(), json.dumps(payload)))
    conn.commit()
    conn.close()


def load_callbacks():
    conn = sqlite3.connect("data/callbacks.db")
    c = conn.cursor()
    c.execute("SELECT received_at, payload FROM callbacks ORDER BY id DESC LIMIT 50")
    rows = c.fetchall()
    conn.close()
    return rows


# 🔄 Mock Callback Endpoint (FastAPI)
app = FastAPI()

@app.post("/mock_callback")
async def mock_callback(request: Request):
    data = await request.json()
    save_callback_to_db(data)

    # Extract info and send alert (if successful)
    try:
        body = data.get("Body", {})
        stk_callback = body.get("stkCallback", {})
        result_code = stk_callback.get("ResultCode")
        if result_code == 0:
            meta_items = stk_callback.get("CallbackMetadata", {}).get("Item", [])
            txn = {item["Name"]: item["Value"] for item in meta_items if "Value" in item}
            send_email_alert(txn)
    except Exception as e:
        print("⚠️ Error parsing for alert:", e)

    print("📥 Callback received:", data)
    return {"ResultCode": 0, "ResultDesc": "Received"}


# 📺 Show Callbacks in Streamlit UI
def display_callbacks():
    st.subheader("📬 Recent MPESA Callbacks")
    rows = load_callbacks()
    if not rows:
        st.info("No callbacks received yet.")
    for ts, payload in rows:
        with st.expander(f"🕒 {ts}"):
            st.json(json.loads(payload))


# 👟 Run mock server locally
def start_mock_server():
    init_db()
    uvicorn.run(app, host="0.0.0.0", port=8000)
def send_email_alert(transaction):
    """Send an email notification for a successful payment."""
    try:
        smtp_server = st.secrets["email"]["EMAIL_HOST"]
        smtp_port = st.secrets["email"]["EMAIL_PORT"]
        username = st.secrets["email"]["EMAIL_USERNAME"]
        password = st.secrets["email"]["EMAIL_PASSWORD"]
        recipient = st.secrets["email"]["EMAIL_TO"]

        subject = "✅ M-PESA Payment Received"
        body = f"""
        A new M-PESA payment was received:

        Phone: {transaction.get('PhoneNumber')}
        Amount: {transaction.get('Amount')}
        Ref: {transaction.get('MpesaReceiptNumber')}
        Date: {transaction.get('TransactionDate')}
        """

        msg = MIMEMultipart()
        msg["From"] = username
        msg["To"] = recipient
        msg["Subject"] = subject

        msg.attach(MIMEText(body, "plain"))

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(username, password)
        server.send_message(msg)
        server.quit()

        print("📧 Email alert sent.")
    except Exception as e:
        print("❌ Failed to send email:", str(e))