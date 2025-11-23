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

# --- 📂 PERMANENT FILE STORAGE SYSTEM ---
DB_FILE = "basha_database.json"
LEAD_COST = 2  # 1 Lead = ₹2

def load_data():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                data = json.load(f)
                # Ensure new fields exist
                if "payment_requests" not in data: data["payment_requests"] = []
                if "settings" not in data: data["settings"] = {"upi_id": "basha@upi", "qr_image": None}
                return data
        except: pass
    
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

# Load DB
if "db_data" not in st.session_state:
    st.session_state["db_data"] = load_data()

db = st.session_state["db_data"]

st.set_page_config(page_title="Basha Master V17", page_icon="🦁", layout="wide")

# --- 🛠️ HELPER FUNCTIONS ---
def image_to_base64(uploaded_file):
    try:
        return base64.b64encode(uploaded_file.getvalue()).decode()
    except: return None

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

if current_user not in db["users"]:
    st.session_state["logged_in"] = False
    st.rerun()

user_data = db["users"][current_user]

# Daily Reset Logic
today_str = str(date.today())
if user_data.get("last_active_date") != today_str:
    db["users"][current_user]["today_usage"] = 0
    db["users"][current_user]["last_active_date"] = today_str
    save_data(db)
    user_data = db["users"][current_user]

# --- TOP BAR ---
col_head1, col_head2 = st.columns([4, 1])
with col_head1:
    st.title("🦁 Basha Master V17")
with col_head2:
    st.metric(label="💰 Wallet Balance", value=f"₹{user_data.get('credits', 0)}")

# Sidebar
st.sidebar.title(f"👤 {current_user.capitalize()}")
st.sidebar.caption(f"📅 Plan Exp: {user_data['expiry']}")

# Daily Limit Progress
daily_cap = user_data.get('daily_cap', 300)
today_used = user_data.get('today_usage', 0)
remaining_daily = daily_cap - today_used
if remaining_daily < 0: remaining_daily = 0

st.sidebar.markdown("---")
st.sidebar.write(f"📊 **Daily Quota:** {today_used}/{daily_cap}")
st.sidebar.progress(min(today_used / daily_cap, 1.0))
st.sidebar.markdown("---")

# --- 💎 SIDEBAR RECHARGE (NEW REQUEST SYSTEM) ---
if role == "client":
    with st.sidebar.expander("💎 Recharge Wallet", expanded=True):
        st.write("Scan to Pay:")
        
        # DISPLAY DYNAMIC QR & UPI
        settings = db.get("settings", {})
        if settings.get("qr_image"):
            st.image(base64.b64decode(settings["qr_image"]), caption="Scan this QR")
        else:
            st.warning("Admin hasn't uploaded QR yet.")
            
        st.code(settings.get("upi_id", "basha@upi"), language="text")
        st.markdown("---")
        
        # Payment Request Form
        st.write("**Step 2: Submit Details**")
        pay_amt = st.number_input("Amount Paid (₹)", min_value=100, step=50)
        pay_utr = st.text_input("Transaction ID / UTR")
        
        if st.button("🔔 Notify Admin"):
            if pay_utr:
                req = {
                    "user": current_user,
                    "amount": pay_amt,
                    "utr": pay_utr,
                    "time": str(datetime.now().strftime("%Y-%m-%d %H:%M")),
                    "status": "Pending"
                }
                db["payment_requests"].append(req)
                save_data(db)
                st.success("✅ Request Sent! Wait for approval.")
            else:
                st.error("Enter Transaction ID")

if st.sidebar.button("Logout", type="primary"):
    st.session_state["logged_in"] = False
    st.rerun()

# --- 👑 ADMIN EMPIRE ---
if role == "owner":
    st.title("🛠️ Admin Empire")
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🔔 Payment Requests", "⚙️ QR Settings", "➕ Add User", "👥 Users", "📊 Reports"])
    
    # TAB 1: PAYMENT APPROVALS (NEW)
    with tab1:
        st.subheader("🔔 Pending Payment Requests")
        
        # Filter Pending
        pending_reqs = [r for r in db["payment_requests"] if r["status"] == "Pending"]
        
        if pending_reqs:
            for i, req in enumerate(pending_reqs):
                with st.container(border=True):
                    c1, c2, c3, c4 = st.columns(4)
                    c1.write(f"👤 **{req['user']}**")
                    c2.write(f"💰 **₹{req['amount']}**")
                    c3.write(f"🆔 `{req['utr']}`")
                    
                    if c4.button(f"✅ Approve", key=f"app_{i}"):
                        # Add Money
                        fresh_db = load_data() # Load latest to avoid overwrite
                        fresh_db["users"][req['user']]["credits"] += req['amount']
                        
                        # Remove from pending (mark approved)
                        # We need to find exact index in main DB list
                        for item in fresh_db["payment_requests"]:
                            if item["utr"] == req["utr"]:
                                item["status"] = "Approved"
                        
                        save_data(fresh_db)
                        st.success(f"Approved! ₹{req['amount']} added to {req['user']}")
                        time.sleep(1)
                        st.rerun()
        else:
            st.info("No pending requests.")

    # TAB 2: QR SETTINGS (NEW)
    with tab2:
        st.subheader("⚙️ Setup Payment Details")
        current_upi = db["settings"].get("upi_id", "")
        new_upi = st.text_input("Your UPI ID", value=current_upi)
        
        uploaded_qr = st.file_uploader("Upload QR Code Image", type=['png', 'jpg', 'jpeg'])
        
        if st.button("💾 Save Settings"):
            db["settings"]["upi_id"] = new_upi
            if uploaded_qr:
                db["settings"]["qr_image"] = image_to_base64(uploaded_qr)
            save_data(db)
            st.success("Settings Saved!")

    # TAB 3: ADD USER
    with tab3:
        st.subheader("➕ Create New User")
        with st.form("manual_add"):
            c1, c2 = st.columns(2)
            mu = c1.text_input("Username")
            mp = c2.text_input("Password")
            c3, c4 = st.columns(2)
            ml = c3.number_input("Initial Credits (₹)", 100)
            md = c4.selectbox("Validity", [30, 90, 365], format_func=lambda x: f"{x} Days")
            daily_limit_input = st.number_input("🔒 Daily Lead Limit", value=300)
            m_phone = st.text_input("Phone (Optional)")
            
            if st.form_submit_button("Create User"):
                fresh_db = load_data()
                if mu in fresh_db["users"]: st.error("Exists!")
                else:
                    exp = (date.today() + timedelta(days=validity_days)).strftime("%Y-%m-%d")
                    fresh_db["users"][mu] = {
                        "password": mp, "role": "client", "expiry": exp, 
                        "credits": ml, "daily_cap": daily_limit_input, "today_usage": 0, "last_active_date": str(date.today())
                    }
                    save_data(fresh_db)
                    st.success(f"✅ User '{mu}' Created!")
                    if m_phone:
                        wa_link = make_login_share_link(m_phone, mu, mp)
                        st.markdown(f'<a href="{wa_link}" target="_blank"><button>📲 Send Login</button></a>', unsafe_allow_html=True)

    with tab4:
        st.subheader("Active Users")
        users_list = [{"User": u, "Balance": f"₹{d.get('credits',0)}", "Daily Cap": d.get('daily_cap', 300)} for u, d in db["users"].items()]
        st.dataframe(pd.DataFrame(users_list))

    with tab5:
        if db["logs"]:
            st.dataframe(pd.DataFrame(db["logs"]))

# --- 🕵️‍♂️ SCRAPER V17 ---
st.markdown("---")

exp_date = datetime.strptime(user_data["expiry"], "%Y-%m-%d").date()
if date.today() > exp_date and role != "owner":
    st.error("⛔ PLAN EXPIRED!")
    st.stop()

if remaining_daily <= 0 and role != "owner":
    st.error("⛔ Daily Limit Reached!")
    st.stop()

current_balance = user_data.get('credits', 0)
if current_balance < LEAD_COST and role != "owner":
    st.error(f"⛔ Low Balance! Min: ₹{LEAD_COST}")
    st.stop()

c1, c2, c3 = st.columns([2, 1, 1])
keyword = c1.text_input("Enter Business & City", "Gyms in Chennai")
max_by_money = int(current_balance / LEAD_COST)
max_allowed = min(max_by_money, remaining_daily) if role != "owner" else 1000
slider_default = 5 if max_allowed >= 5 else 1
if max_allowed == 0: slider_default = 0
leads_requested = c2.slider("Leads Needed", 0, max_allowed, slider_default)
estimated_cost = leads_requested * LEAD_COST
min_rating = c3.slider("⭐ Min Rating", 0.0, 5.0, 3.5, 0.5)
enable_email = st.checkbox("📧 Enable Email Extraction")

if role != "owner":
    st.info(f"💰 Cost: ₹{estimated_cost} | 📊 Daily Limit: {remaining_daily}")

if st.button("🚀 Start Vettai"):
    fresh_db = load_data()
    if fresh_db["users"][current_user]["credits"] < LEAD_COST and role != "owner":
        st.error("❌ Insufficient Funds!")
        st.stop()

    status = st.empty()
    status.info("🌐 Booting Cloud Browser...")
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()), options=options)
    
    collected_data = []
    try:
        driver.get("https://www.google.com/maps")
        time.sleep(3)
        driver.find_element(By.ID, "searchboxinput").send_keys(keyword + Keys.RETURN)
        time.sleep(5)
        status.warning("🔍 Scanning...")
        
        links_to_visit = set()
        scrolls = 0
        panel = driver.find_element(By.XPATH, '//div[contains(@aria-label, "Results for")]')
        while len(links_to_visit) < leads_requested and scrolls < 20:
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", panel)
            time.sleep(2)
            elements = driver.find_elements(By.CLASS_NAME, "hfpxzc")
            for elem in elements:
                try:
                    rating = 0.0
                    try: rating = float(re.search(r"(\d\.\d)", elem.find_element(By.XPATH, "./..").text).group(1))
                    except: pass
                    l = elem.get_attribute("href")
                    if rating >= min_rating and l not in db["leads"]: links_to_visit.add(l)
                except: pass
            scrolls += 1
        
        status.info(f"✅ Found {len(links_to_visit)} Targets. Extracting...")
        unique_links = list(links_to_visit)[:leads_requested]
        progress = st.progress(0)
        
        for i, link in enumerate(unique_links):
            fresh_db = load_data()
            if role != "owner":
                if fresh_db["users"][current_user]["credits"] < LEAD_COST:
                    status.error("❌ Balance Over!")
                    break
                if fresh_db["users"][current_user]["today_usage"] >= fresh_db["users"][current_user]["daily_cap"]:
                    status.error("❌ Limit Reached!")
                    break

            try:
                driver.get(link)
                time.sleep(2)
                try: name = driver.find_element(By.XPATH, '//h1[contains(@class, "DUwDvf")]').text
                except: name = "Unknown"
                phone = "No Number"
                try:
                    btns = driver.find_elements(By.XPATH, '//button[contains(@data-item-id, "phone")]')
                    if btns: phone = btns[0].get_attribute("aria-label").replace("Phone: ", "").strip()
                except: pass
                
                if phone != "No Number" and phone in fresh_db["leads"]: continue
                
                email, website = "Skipped", "Not Found"
                if enable_email:
                    try:
                        w_btns = driver.find_elements(By.XPATH, '//a[contains(@data-item-id, "authority")]')
                        if w_btns:
                            website = w_btns[0].get_attribute("href")
                            try:
                                r = requests.get(website, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
                                mails = set(re.findall(r"[a-z0-9\.\-+_]+@[a-z0-9\.\-+_]+\.[a-z]+", r.text, re.I))
                                if mails: email = list(mails)[0]
                            except: pass
                    except: pass
                
                collected_data.append({"Name": name, "Phone": phone, "Rating": "4.0+", "Email": email, "Website": website, "WhatsApp": make_whatsapp_link(phone)})
                
                fresh_db["leads"].append(link)
                if phone != "No Number": fresh_db["leads"].append(phone)
                
                if role != "owner":
                    fresh_db["users"][current_user]["credits"] -= LEAD_COST
                    fresh_db["users"][current_user]["today_usage"] += 1
                
                save_data(fresh_db)
                status.success(f"✅ Secured: {name} | 💰 Bal: ₹{fresh_db['users'][current_user]['credits']}")
                progress.progress((i+1)/len(unique_links))
            except: continue
            
        if collected_data:
            total_cost = len(collected_data) * LEAD_COST
            fresh_db["logs"].append({"User": current_user, "Keyword": keyword, "Count": len(collected_data), "Cost": total_cost, "Time": str(datetime.now())})
            save_data(fresh_db)
            df = pd.DataFrame(collected_data)
            st.data_editor(df, column_config={"WhatsApp": st.column_config.LinkColumn("Chat", display_text="📲 Chat"), "Website": st.column_config.LinkColumn("Site")}, hide_index=True)
            st.download_button("📥 Download Excel", df.to_csv(index=False).encode('utf-8'), "leads.csv", "text/csv")
            st.success("Completed!")
            time.sleep(2)
            st.rerun()
        else: st.warning("No leads found.")
    except Exception as e: st.error(f"Error: {e}")
    finally: driver.quit()