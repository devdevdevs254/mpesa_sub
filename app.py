import streamlit as st
from mpesa_utils import initiate_stk_push, display_callbacks, init_db

st.set_page_config(page_title="M-PESA STK Push", page_icon="📲")

st.title("📲 M-PESA STK Push Demo")
st.markdown("Initiate a payment via M-PESA and view callback logs.")

# Initialize database
init_db()

# STK Push Form
with st.form("stk_form"):
    phone = st.text_input("Phone Number (e.g. 254712345678)")
    amount = st.number_input("Amount (KES)", min_value=1, value=10)
    submitted = st.form_submit_button("Send STK Push")

    if submitted:
        response = initiate_stk_push(phone, amount)
        st.success("STK Push Sent!" if response.get("ResponseCode") == "0" else "Failed to send STK Push")
        st.json(response)

# Display callback logs
st.divider()
display_callbacks()
