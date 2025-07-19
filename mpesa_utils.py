import requests
import base64
import datetime
import streamlit as st

def get_token():
    """Fetches OAuth access token from Safaricom"""
    url = "https://api.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    response = requests.get(url, auth=(config("CONSUMER_KEY"), config("CONSUMER_SECRET")))
    response.raise_for_status()
    return response.json().get("access_token")


def initiate_stk_push(phone: str, amount: int):
    """Initiates an STK Push to the user's phone number"""
    shortcode = st.secrets["BUSINESS_SHORTCODE"]
    passkey = st.secrets["PASSKEY"]                   # from Safaricom
    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')

    # Safaricom Password: base64(Shortcode + Passkey + Timestamp)
    data_to_encode = shortcode + passkey + timestamp
    password = base64.b64encode(data_to_encode.encode()).decode()

    payload = {
        "BusinessShortCode": shortcode,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerBuyGoodsOnline",  # or "CustomerPayBillOnline"
        "Amount": amount,
        "PartyA": phone,
        "PartyB": shortcode,
        "PhoneNumber": phone,
        "CallBackURL": config("CALLBACK_URL"),
        "AccountReference": "Subscription",
        "TransactionDesc": "Monthly Premium"
    }

    headers = {
        "Authorization": f"Bearer {get_token()}",
        "Content-Type": "application/json"
    }

    response = requests.post(
        "https://api.safaricom.co.ke/mpesa/stkpush/v1/processrequest",
        json=payload,
        headers=headers
    )

    if response.status_code == 200:
        return {"status": "sent", "response": response.json()}
    else:
        return {
            "status": "error",
            "error_code": response.status_code,
            "error_message": response.text
        }
