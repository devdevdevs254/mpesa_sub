import streamlit as st
from mpesa_utils import initiate_stk_push

st.title("💰 Subscribe with M-Pesa")

phone = st.text_input("M-Pesa Phone (e.g., 2547XXXXXXXX)")
if st.button("Subscribe Now") and phone:
    result = initiate_stk_push(phone, 100)
    st.write(result)
