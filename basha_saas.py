import streamlit as st
import time
import pandas as pd
import re
import requests
import random
import string
import json
import os
import base64
from datetime import datetime, timedelta, date
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
from bs4 import BeautifulSoup

# --- 📂 PERMANENT FILE STORAGE ---
DB_FILE = "basha_database.json"
LEAD_COST = 2 

def load_data():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                data = json.load(f)
                # --- AUTO-REPAIR DATABASE (CRITICAL FIX) ---
                changes_made = False
                today_str = str(date.today())
                
                for u in data["users"]:
                    user_obj = data["users"][u]
                    if "credits" not in user_obj: user_obj["credits"] = 0; changes_made = True
                    if "daily_cap" not in user_obj: user_obj["daily_cap"] = 300; changes_made = True
                    if "today_usage" not in user_obj: user_obj["today_usage"] = 0; changes_made = True
                    if "last_active_date" not in user_obj: user_obj["last_active_date"] = today_str; changes_made = True
                
                if changes_made:
                    with open(DB_FILE, "w") as f: json.dump(data, f, indent=4)
                        
                return data
        except: pass
    
    # Default New DB
    return {
        "users": {
            "basha": {"password": "king", "role": "owner", "expiry": "2030-01-01", "credits": 50000, "daily_cap": 10000, "today_usage": 0, "last_active_date": str(date.today())},
            "client1": {"password": "guest", "role": "client", "expiry": "2025-12-30", "credits": 50, "daily_cap": 300, "today_usage": 0, "last_active_date": str(date.today())}
        },
        "coupons": {}, "leads": [], "logs": [], "payment_requests": [],
        "settings": {"upi_id": "yourname@upi", "qr_image": None}
    }

def save_data(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

if "db_data" not in st.session_state:
    st.session_state["db_data"] = load_data()

if "last_scraped_data" not in st.session_state:
    st.session_state["last_scraped_data"] = None

db = st.session_state["db_data"]

st.set_page_config(page_title="Basha Master V25", page_icon="🦁", layout="wide")

# --- 🛠️ HELPER FUNCTIONS ---
def generate_coupon_code(length=8):
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choice(characters) for i in range(length))

def make_whatsapp_link(phone):
    if not phone or phone == "No Number": return None
    clean_num = re.sub(r'\D', '', phone)
    if len(clean_num) == 10: clean_num = "91" + clean_num
    return f"https://wa.me/{clean_num}?text=Hi,%20saw%20your%20business%20on%20Google!"

def make_login_share_link(phone, user, pwd):
    clean_num = re.sub(r'\D', '', phone)
    if len(clean_num) == 10: clean_num = "91" + clean_num
    msg = f"🦁 *Welcome to Basha Empire!* 🦁%0A%0AHere are your Login Details:%0A👤 *Username:* {user}%0A🔑 *Password:* {pwd}"
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
            fresh_db = load_data()
            st.session_state["db_data"] = fresh_db
            if u in fresh_db["users"] and fresh_db["users"][u]["password"] == p:
                st.session_state["logged_in"] = True
                st.session_state["user"] = u
                st.session_state["role"] = fresh_db["users"][u]["role"]
                st.rerun()
            else: st.error("❌ Incorrect Username or Password")
    st.stop()

# --- 🖥️ DASHBOARD ---
current_user = st.session_state["user"]
role = db["users"].get(current_user, {}).get("role", "client")
db = load_data()
st.session_state["db_data"] = db

if current_user not in db["users"]: st.session_state["logged_in"] = False; st.rerun()
user_data = db["users"][current_user]

# Daily Reset Logic
today_str = str(date.today())
if user_data.get("last_active_date") != today_str:
    db["users"][current_user]["today_usage"] = 0
    db["users"][current_user]["last_active_date"] = today_str
    save_data(db)
    user_data = db["users"][current_user]

# --- METRICS & SIDEBAR ---
display_balance = f"{user_data.get('credits', 0)}"
if role == "owner": display_balance = "∞"

col_head1, col_head2 = st.columns([4, 1])
with col_head1: st.title("🦁 Basha Master V25")
with col_head2: st.metric(label="🌟 Credits", value=display_balance)

st.sidebar.title(f"👤 {current_user.capitalize()}")
st.sidebar.caption(f"📅 Plan Exp: {user_data['expiry']}")

# Daily Limit Progress
if role != "owner":
    daily_cap = user_data.get('daily_cap', 300)
    today_used = user_data.get('today_usage', 0)
    remaining_daily = daily_cap - today_used
    st.sidebar.markdown("---")
    st.sidebar.write(f"📊 **Daily Quota:** {today_used}/{daily_cap}")
    st.sidebar.progress(min(today_used / daily_cap, 1.0))
    st.sidebar.markdown("---")

# --- 💎 RECHARGE (CLIENT ONLY) ---
if role == "client":
    with st.sidebar.expander("💎 Recharge Wallet", expanded=True):
        st.write("Scan to Pay:")
        settings = db.get("settings", {})
        if settings.get("qr_image"): st.image(base64.b64decode(settings["qr_image"]), caption="Scan to Pay")
        st.code(settings.get("upi_id", "basha@upi"), language="text")
        
        pay_amt = st.number_input("Paid Amount (₹)", min_value=100, step=50)
        pay_utr = st.text_input("Transaction ID / UTR")
        
        if st.button("🔔 Notify Admin"):
            if pay_utr:
                req = {"user": current_user, "amount": pay_amt, "utr": pay_utr, "time": str(datetime.now()), "status": "Pending"}
                db["payment_requests"].append(req)
                save_data(db)
                st.success("✅ Request Sent!")
            else: st.error("Enter UTR")

# --- LOGOUT ---
if st.sidebar.button("Logout", type="primary"): st.session_state["logged_in"] = False; st.rerun()

# --- 👑 ADMIN EMPIRE ---
if role == "owner":
    st.title("🛠️ Admin Empire")
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🔔 Payments", "⚙️ Settings", "➕ Add User", "👥 Manage Users", "📊 Reports"])
    
    # [TAB 1: PAYMENTS LOGIC HERE]...
    
    # [TAB 2: SETTINGS LOGIC HERE]...

    # [TAB 3: ADD USER LOGIC HERE]...

    # [TAB 4: MANAGE USERS LOGIC HERE]...

    # [TAB 5: REPORTS LOGIC HERE]...
    pass # Admin tabs logic is omitted for brevity but is necessary for full code

# --- 🕵️‍♂️ SCRAPER V2