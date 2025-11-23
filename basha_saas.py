import streamlit as st
import time
import pandas as pd
import re
import requests
import random
import string
import json
import os
from datetime import datetime, timedelta, date
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
from bs4 import BeautifulSoup

# --- 📂 PERMANENT FILE STORAGE SYSTEM ---
DB_FILE = "basha_database.json"
LEAD_COST = 2  # 1 Lead = ₹2

def load_data():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                data = json.load(f)
                # Migration check (Old DB to New DB compatibility)
                for u in data["users"]:
                    if "credits" not in data["users"][u]:
                        data["users"][u]["credits"] = 100 # Give free credits to old users
                return data
        except: pass
    return {
        "users": {
            "basha": {"password": "king", "role": "owner", "expiry": "2030-01-01", "credits": 50000},
            "client1": {"password": "guest", "role": "client", "expiry": "2025-12-30", "credits": 50}
        },
        "coupons": {},
        "leads": [],
        "logs": []
    }

def save_data(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

if "db_data" not in st.session_state:
    st.session_state["db_data"] = load_data()

db = st.session_state["db_data"]

st.set_page_config(page_title="Basha Master V14", page_icon="🦁", layout="wide")

# --- 🛠️ HELPER FUNCTIONS ---
def generate_coupon(days, amount):
    suffix = ''.join(random.choices(string.digits, k=4))
    code = f"BAS{suffix}"
    db["coupons"][code] = {"days": days, "amount": amount}
    save_data(db)
    return code

def make_whatsapp_link(phone):
    if not phone or phone == "No Number": return None
    clean_num = re.sub(r'\D', '', phone)
    if len(clean_num) == 10: clean_num = "91" + clean_num
    return f"https://wa.me/{clean_num}?text=Hi,%20saw%20your%20business%20on%20Google!"

def make_login_share_link(phone, user, pwd):
    clean_num = re.sub(r'\D', '', phone)
    if len(clean_num) == 10: clean_num = "91" + clean_num
    msg = f"🦁 *Welcome to Basha Empire!* 🦁%0A%0AHere are your Login Details:%0A👤 *Username:* {user}%0A🔑 *Password:* {pwd}%0A%0ALogin to start hunting leads!"
    return f"https://wa.me/{clean_num}?text={msg}"

# --- 🔐 LOGIN SYSTEM ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["user"] = None
    st.session_state["role"] = None

if not st.session_state["logged_in"]:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h2 style='text-align: center;'>🔐 Basha Master Access</h2>", unsafe_allow_html=True)
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.button("🚀 Login", use_container_width=True):
            users = db["users"]
            if u in users and users[u]["password"] == p:
                st.session_state["logged_in"] = True
                st.session_state["user"] = u
                st.session_state["role"] = users[u]["role"]
                st.rerun()
            else: st.error("❌ Incorrect Username or Password")
    st.stop()

# --- 🖥️ DASHBOARD & UI ---
current_user = st.session_state["user"]
role = st.session_state["role"]
if current_user not in db["users"]:
    st.session_state["logged_in"] = False
    st.rerun()
user_data = db["users"][current_user]

# --- 💰 TOP RIGHT CREDITS DISPLAY ---
col_head1, col_head2 = st.columns([4, 1])
with col_head1:
    st.title("🦁 Basha Master V14")
with col_head2:
    st.metric(label="💰 Wallet Balance", value=f"₹{user_data.get('credits', 0)}")

# Sidebar
st.sidebar.title(f"👤 {current_user.capitalize()}")
st.sidebar.caption(f"📅 Valid till: {user_data['expiry']}")

# --- 💎 SIDEBAR RECHARGE ---
if role == "client":
    with st.sidebar.expander("💎 Wallet / Recharge", expanded=True):
        st.write(f"**Current Balance: ₹{user_data.get('credits', 0)}**")
        st.write(f"Cost per Lead: ₹{LEAD_COST}")
        
        st.markdown("---")
        st.write("Scan to pay:")
        # Replace this URL with your actual QR Code Image
        st.image("https://upload.wikimedia.org/wikipedia/commons/d/d0/QR_code_for_mobile_English_Wikipedia.svg", caption="UPI: basha@okicici")
        st.caption("Send screenshot to Admin to get Code.")
        
        st.markdown("---")
        recharge_code = st.text_input("Enter Coupon Code")
        if st.button("✅ Add Money"):
            if recharge_code in db["coupons"]:
                data = db["coupons"][recharge_code]
                
                # Update Credits & Validity
                db["users"][current_user]["credits"] += data['amount']
                new_expiry = (date.today() + timedelta(days=data['days'])).strftime("%Y-%m-%d")
                db["users"][current_user]["expiry"] = new_expiry
                
                del db["coupons"][recharge_code]
                save_data(db)
                st.balloons()
                st.success(f"🎉 Added ₹{data['amount']}!")
                time.sleep(2)
                st.rerun()
            else: st.error("❌ Invalid Code")

if st.sidebar.button("Logout", type="primary"):
    st.session_state["logged_in"] = False
    st.rerun()

# --- 👑 ADMIN EMPIRE ---
if role == "owner":
    st.title("🛠️ Admin Empire")
    tab1, tab2, tab3, tab4 = st.tabs(["➕ Add User", "🎟️ Money Coupons", "👥 Users", "📊 Reports"])
    
    with tab1:
        st.subheader("➕ Create New User")
        with st.form("manual_add"):
            c1, c2 = st.columns(2)
            mu = c1.text_input("Username")
            mp = c2.text_input("Password")
            c3, c4 = st.columns(2)
            # Replaced Daily Limit with Initial Credits
            ml = c3.number_input("Initial Credits (₹)", 100)
            md = c4.selectbox("Validity", [30, 90, 365], format_func=