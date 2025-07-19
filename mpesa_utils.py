import requests
import base64
import datetime
import streamlit as st

def get_token():
    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    response = requests.get(
        url,
        auth=(st.secrets["CONSUMER_KEY"], st.secrets["CONSUMER_SECRET"])
    )
    return response.json()["access_token"]

def initiate_stk_push(phone: str, amount: int):
    shortcode = st.secrets["BUSINESS_SHORTCODE"]  # e.g., 174379
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
        "AccountReference": "TestSubscription",
        "TransactionDesc": "Sandbox Payment"
    }

    headers = {
        "Authorization": f"Bearer {get_token()}",
        "Content-Type": "application/json"
    }

    response = requests.post(
        "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest",
        json=payload,
        headers=headers
    )

    if response.status_code == 200:
        return {"status": "sent", "response": response.json()}
    else:
        return {"status": "error", "error": response.text}
