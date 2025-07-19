import streamlit as st
from mpesa_utils import initiate_stk_push, display_callbacks, init_db, load_callbacks
import sqlite3

st.set_page_config(page_title="MPESA STK Tester", layout="centered")
st.title("💳 MPESA STK Push Tester")

init_db()

# 🔍 Filters
st.sidebar.subheader("🔎 Filter Callbacks")
filter_txn = st.sidebar.text_input("Transaction ID")
filter_phone = st.sidebar.text_input("Phone Number")

# 📱 Input phone and amount
with st.form("mpesa_form"):
    phone = st.text_input("📞 Phone Number (Format: 2547XXXXXXXX)")
    amount = st.number_input("💵 Amount", min_value=1, step=1)
    submit = st.form_submit_button("Send STK Push")

if submit:
    result = initiate_stk_push(phone, int(amount))
    if result["status"] == "sent":
        st.success("STK Push sent! ✅")
    else:
        st.error(f"Failed to send: {result.get('error')}")

# 📬 Callback viewer
st.markdown("---")
st.subheader("📬 Callback Logs")

callbacks = load_callbacks()

# 🧠 Apply filters
if filter_txn or filter_phone:
    filtered = []
    for ts, raw in callbacks:
        try:
            data = json.loads(raw)
            txid = data.get("Body", {}).get("stkCallback", {}).get("CheckoutRequestID", "")
            number = data.get("Body", {}).get("stkCallback", {}).get("PhoneNumber", "")
            if (filter_txn and filter_txn in txid) or (filter_phone and filter_phone in str(number)):
                filtered.append((ts, raw))
        except:
            continue
    callbacks = filtered

if not callbacks:
    st.info("No matching callbacks.")
else:
    for ts, payload in callbacks:
        with st.expander(f"🕒 {ts}"):
            st.json(json.loads(payload))
