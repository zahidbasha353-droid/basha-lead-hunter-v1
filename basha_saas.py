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
                
                # Ensure all users have tracking keys
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
        "coupons": {},
        "leads": [],
        "logs": [],
        "payment_requests": [],
        "settings": {"upi_id": "yourname@upi", "qr_image": None}
    }

def save_data(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

if "db_data" not in st.session_state:
    st.session_state["db_data"] = load_data()

# Initialize Persistent Results Display
if "last_scraped_data" not in st.session_state:
    st.session_state["last_scraped_data"] = None

db = st.session_state["db_data"]

st.set_page_config(page_title="Basha Master V24", page_icon="🦁", layout="wide")

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
role = st.session_state["role"]
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

# --- OWNER UNLIMITED LOGIC & METRIC UPDATE ---
display_balance = f"{user_data.get('credits', 0)}"
if role == "owner": display_balance = "∞"

col_head1, col_head2 = st.columns([4, 1])
with col_head1: st.title("🦁 Basha Master V24")
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

# --- 🎁 REDEEM CODE (CLIENT ONLY) ---
if role == "client":
    with st.sidebar.expander("🎁 Redeem Code", expanded=True):
        redeem_code = st.text_input("Enter Coupon Code").strip().upper()
        if st.button("✅ Redeem"):
            fresh = load_data()
            if redeem_code in fresh["coupons"]:
                coupon = fresh["coupons"][redeem_code]
                if coupon.get("used", False): # Check if 'used' key exists and is True
                    st.error("❌ Code already used!")
                else:
                    credits_to_add = coupon["credits"]
                    fresh["users"][current_user]["credits"] += credits_to_add
                    coupon["used"] = True
                    coupon["used_by"] = current_user
                    coupon["used_on"] = str(datetime.now())
                    fresh["coupons"][redeem_code] = coupon
                    save_data(fresh)
                    st.success(f"🎉 Success! {credits_to_add} Credits added!")
                    time.sleep(1)
                    st.rerun()
            else:
                st.error("❌ Invalid Code!")

if st.sidebar.button("Logout", type="primary"): st.session_state["logged_in"] = False; st.rerun()

# --- 👑 ADMIN EMPIRE ---
if role == "owner":
    st.title("🛠️ Admin Empire")
    tab1, tab2, tab3, tab4 = st.tabs(["🎟️ Generate Coupon", "👥 Manage Users", "📊 Reports", "⚙️ Settings"]) # New tabs arrangement
    
    with tab1:
        st.subheader("🎟️ Generate New Coupon")
        credits_to_add = st.number_input("Credits to Add", min_value=10, step=10)
        num_codes = st.number_input("Number of Codes to Generate", min_value=1, max_value=20, step=1)
        
        if st.button("✨ Generate Codes"):
            fresh = load_data()
            generated_codes = []
            for _ in range(num_codes):
                code = generate_coupon_code()
                fresh["coupons"][code] = {"credits": credits_to_add, "used": False, "used_by": None, "used_on": None}
                generated_codes.append(code)
            
            save_data(fresh)
            st.success(f"✅ {num_codes} codes generated!")
            st.code("\n".join(generated_codes), language="text")

        st.markdown("---")
        st.subheader("📋 View All Coupons")
        
        # --- FIX APPLIED HERE: Safely accessing keys with .get() ---
        coupon_list = [{
            "Code": k, 
            "Credits": v.get("credits", 0), 
            "Used": v.get("used", False), 
            "Used By": v.get("used_by", "N/A"), 
            "Used On": v.get("used_on", "N/A")
        } for k, v in db["coupons"].items()]
        st.dataframe(pd.DataFrame(coupon_list))


    with tab2: # Manage Users
        st.subheader("👥 Users")
        fresh = load_data()
        users_list = [{"User": u, "Pass": d["password"], "Credits": d.get('credits',0), "Limit": d.get('daily_cap', 300), "Role": d["role"], "Delete": False} for u, d in fresh["users"].items()]
        
        edited_df = st.data_editor(
            pd.DataFrame(users_list), 
            column_config={"Delete": st.column_config.CheckboxColumn("Remove?", default=False), "Credits": st.column_config.NumberColumn("Credits", format="%d")}, 
            disabled=["User", "Role"], hide_index=True
        )

        if st.button("💾 Update Users / Delete Selected"):
            for index, row in edited_df.iterrows():
                user_key = row['User']
                if row['Delete']:
                    if user_key != "basha": del fresh["users"][user_key]
                    else: st.error("Can't delete Owner!")
                else:
                    fresh["users"][user_key]["credits"] = row['Credits']
                    fresh["users"][user_key]["daily_cap"] = row['Limit']
            
            save_data(fresh)
            st.success("Users Updated!")
            time.sleep(1)
            st.rerun()

    with tab3: # Reports (Logs)
        if db["logs"]: st.dataframe(pd.DataFrame(db["logs"]))
        else: st.info("No logs yet.")

    with tab4: # Settings
        st.subheader("⚙️ General Settings")
        # --- ADD USER Logic ---
        with st.expander("➕ Add New User"):
            with st.form("add"):
                c1, c2 = st.columns(2)
                mu = c1.text_input("Username")
                mp = c2.text_input("Password")
                c3, c4 = st.columns(2)
                ml = c3.number_input("Initial Credits", 100)
                md = c4.selectbox("Validity (Days)", [30, 90, 365])
                dlim = st.number_input("Daily Limit", 300)
                mph = st.text_input("Phone (Optional)")
                if st.form_submit_button("Create User"):
                    fresh = load_data()
                    if mu in fresh["users"]: st.error("Exists!")
                    else:
                        exp = (date.today() + timedelta(days=md)).strftime("%Y-%m-%d")
                        fresh["users"][mu] = {"password": mp, "role": "client", "expiry": exp, "credits": ml, "daily_cap": dlim, "today_usage": 0, "last_active_date": str(date.today())}
                        save_data(fresh)
                        st.success("Created!")
                        if mph:
                            wa = make_login_share_link(mph, mu, mp)
                            st.markdown(f'<a href="{wa}" target="_blank"><button>📲 WhatsApp Share</button></a>', unsafe_allow_html=True)
                        time.sleep(1)
                        st.rerun()

        st.markdown("---")
        st.error("⚠️ **Danger Zone (For Testing Only)**")
        if st.button("🗑️ Reset All Lead History (Clear Duplicates)"):
            fresh = load_data()
            fresh["leads"] = [] # Clear used leads
            save_data(fresh)
            st.success("History Cleared! You can search 'Gyms' again.")


# --- 🕵️‍♂️ SCRAPER V24 ---
st.markdown("---")

exp_date = datetime.strptime(user_data["expiry"], "%Y-%m-%d").date()
if date.today() > exp_date and role != "owner": st.error("⛔ PLAN EXPIRED!"); st.stop()

# Credit and Limit Checks
if role != "owner":
    remaining_daily = user_data.get('daily_cap', 300) - user_data.get('today_usage', 0)
    if remaining_daily <= 0: st.error("⛔ Daily Limit Reached!"); st.stop()
    if user_data.get('credits', 0) < LEAD_COST: st.error(f"⛔ Low Credits! Min: {LEAD_COST}"); st.stop()
else: remaining_daily = 999999

c1, c2, c3 = st.columns([2, 1, 1])
keyword = c1.text_input("Enter Business & City", "Gyms in Chennai")
current_bal = user_data.get('credits', 0)
max_by_money = int(current_bal / LEAD_COST)
max_allowed = min(max_by_money, remaining_daily) if role != "owner" else 10000
slider_def = 5 if max_allowed >= 5 else 1
if max_allowed == 0 and role != "owner": slider_def = 0

leads_requested = c2.slider("Leads Needed", 0, max_allowed, slider_def)
estimated_cost = leads_requested * LEAD_COST
min_rating = c3.slider("⭐ Min Rating", 0.0, 5.0, 3.5, 0.5)
enable_email = st.checkbox("📧 Enable Email Extraction")

if role != "owner":
    st.info(f"✨ **Cost:** {estimated_cost} Credits | 📊 **Limit Left:** {remaining_daily}")

if st.button("🚀 Start Vettai"):
    fresh = load_data()
    if role != "owner" and fresh["users"][current_user]["credits"] < LEAD_COST: st.error("Low Credits!"); st.stop()

    status = st.empty()
    status.info("🌐 Booting Cloud Browser...")
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()), options=options)
    
    collected_data = []
    try:
        driver.get("https://www.google.com/maps")
        time.sleep(4)
        driver.find_element(By.ID, "searchboxinput").send_keys(keyword + Keys.RETURN)
        time.sleep(5)
        status.warning("🔍 Scanning...")
        
        links = set()
        scrolls = 0
        panel = driver.find_element(By.XPATH, '//div[contains(@aria-label, "Results for")]')
        while len(links) < leads_requested and scrolls < 20:
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", panel)
            time.sleep(2)
            elements = driver.find_elements(By.CLASS_NAME, "hfpxzc")
            for elem in elements:
                try:
                    l = elem.get_attribute("href")
                    if l not in db["leads"]: links.add(l)
                except: pass
            scrolls += 1
        
        if not links:
            status.error("❌ No new leads found! (Maybe duplicates? Try clearing history in Admin Settings)")
            driver.quit()
            st.session_state["last_scraped_data"] = None 
            st.stop()

        status.info(f"✅ Found {len(links)} Targets. Extracting...")
        ulinks = list(links)[:leads_requested]
        progress = st.progress(0)
        
        for i, link in enumerate(ulinks):
            fresh = load_data()
            if role != "owner" and fresh["users"][current_user]["credits"] < LEAD_COST: status.error("Credits Over!"); break 

            try:
                driver.get(link)
                time.sleep(3)
                try: name = driver.find_element(By.XPATH, '//h1[contains(@class, "DUwDvf")]').text
                except: name = "Unknown"
                phone = "No Number"
                try:
                    btns = driver.find_elements(By.XPATH, '//button[contains(@data-item-id, "phone")]')
                    if btns: phone = btns[0].get_attribute("aria-label").replace("Phone: ", "").strip()
                except: pass
                
                if phone != "No Number" and phone in fresh["leads"]: continue