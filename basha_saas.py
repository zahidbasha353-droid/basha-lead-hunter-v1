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
                # Auto-Fix: Ensure all users have 'credits' key
                for u in data["users"]:
                    if "credits" not in data["users"][u]:
                        data["users"][u]["credits"] = 0 
                return data
        except: pass
    return {
        "users": {
            "basha": {"password": "king", "role": "owner", "expiry": "2030-01-01", "credits": 50000},
            "client1": {"password": "guest", "role": "client", "expiry": "2025-12-30", "credits": 50}
        },
        "coupons": {
            "BASHA100": {"days": 365, "amount": 1000} # Master Coupon
        },
        "leads": [],
        "logs": []
    }

def save_data(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

# Load Data initially
if "db_data" not in st.session_state:
    st.session_state["db_data"] = load_data()

# Shortcut
db = st.session_state["db_data"]

st.set_page_config(page_title="Basha Master V15", page_icon="🦁", layout="wide")

# --- 🛠️ HELPER FUNCTIONS ---
def generate_coupon(days, amount):
    suffix = ''.join(random.choices(string.digits, k=4))
    code = f"BAS{suffix}"
    # MUKKIYAM: Load fresh DB before saving to avoid overwriting
    current_db = load_data()
    current_db["coupons"][code] = {"days": days, "amount": amount}
    save_data(current_db)
    # Sync session state
    st.session_state["db_data"] = current_db
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
            # Always load fresh data on login
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

# Reload DB to get latest balance
db = load_data()
st.session_state["db_data"] = db

if current_user not in db["users"]:
    st.session_state["logged_in"] = False
    st.rerun()
user_data = db["users"][current_user]

# --- 💰 TOP RIGHT CREDITS ---
col_head1, col_head2 = st.columns([4, 1])
with col_head1:
    st.title("🦁 Basha Master V15")
with col_head2:
    st.metric(label="💰 Wallet Balance", value=f"₹{user_data.get('credits', 0)}")

# Sidebar
st.sidebar.title(f"👤 {current_user.capitalize()}")
st.sidebar.caption(f"📅 Valid till: {user_data['expiry']}")

# --- 💎 RECHARGE SYSTEM (FIXED SYNC ISSUE) ---
if role == "client":
    with st.sidebar.expander("💎 Wallet / Recharge", expanded=True):
        st.write(f"**Balance: ₹{user_data.get('credits', 0)}**")
        st.write(f"Cost: ₹{LEAD_COST}/lead")
        st.markdown("---")
        st.write("Scan to Pay:")
        st.image("https://upload.wikimedia.org/wikipedia/commons/d/d0/QR_code_for_mobile_English_Wikipedia.svg", caption="UPI: basha@okicici")
        st.markdown("---")
        
        recharge_code = st.text_input("Enter Coupon Code")
        if st.button("✅ Add Money"):
            # 🔥 CRITICAL FIX: Load DB from file AGAIN to see new codes
            fresh_db = load_data()
            
            if recharge_code in fresh_db["coupons"]:
                data = fresh_db["coupons"][recharge_code]
                
                # Check if it's amount or limit (Backward compatibility)
                add_amount = data.get('amount', 0)
                if add_amount == 0 and 'limit' in data:
                     add_amount = data['limit'] # Fallback for old codes
                
                # Update User
                fresh_db["users"][current_user]["credits"] += add_amount
                new_expiry = (date.today() + timedelta(days=data['days'])).strftime("%Y-%m-%d")
                fresh_db["users"][current_user]["expiry"] = new_expiry
                
                # Delete Code (Unless Master)
                if recharge_code != "BASHA100":
                    del fresh_db["coupons"][recharge_code]
                
                save_data(fresh_db)
                st.session_state["db_data"] = fresh_db # Update Session
                
                st.balloons()
                st.success(f"🎉 Success! Added ₹{add_amount}")
                time.sleep(2)
                st.rerun()
            else:
                st.error("❌ Invalid Code (Try refreshing page)")

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
            ml = c3.number_input("Initial Credits (₹)", 100)
            md = c4.selectbox("Validity", [30, 90, 365], format_func=lambda x: f"{x} Days")
            m_phone = st.text_input("Phone (Optional)")
            
            if st.form_submit_button("Create User"):
                fresh_db = load_data() # Always load fresh
                if mu in fresh_db["users"]: st.error("Exists!")
                else:
                    exp = (date.today() + timedelta(days=md)).strftime("%Y-%m-%d")
                    fresh_db["users"][mu] = {"password": mp, "role": "client", "expiry": exp, "credits": ml}
                    save_data(fresh_db)
                    st.success(f"✅ User '{mu}' Created!")
                    if m_phone:
                        wa_link = make_login_share_link(m_phone, mu, mp)
                        st.markdown(f'<a href="{wa_link}" target="_blank"><button>📲 Send Login</button></a>', unsafe_allow_html=True)

    with tab2:
        st.subheader("🎟️ Generate Money Codes")
        c1, c2 = st.columns(2)
        days = c1.selectbox("Validity Extension", [0, 15, 30], key="g_days")
        amount = c2.number_input("Amount (₹)", 100, step=50, key="g_amt")
        if st.button("⚡ Generate"):
            code = generate_coupon(days, amount)
            st.success(f"Code: {code}")
            st.code(code)
            st.info(f"Value: ₹{amount}")
        
        # Load fresh to show list
        fresh_db = load_data()
        if fresh_db["coupons"]: st.json(fresh_db["coupons"])

    with tab3:
        st.subheader("Active Users")
        fresh_db = load_data()
        users_list = [{"User": u, "Pass": d["password"], "Exp": d["expiry"], "Balance": f"₹{d.get('credits',0)}", "Delete": False} 
                      for u, d in fresh_db["users"].items()]
        edited_df = st.data_editor(pd.DataFrame(users_list), column_config={"Delete": st.column_config.CheckboxColumn("Remove?", default=False)}, hide_index=True)
        if st.button("🗑️ Delete Selected"):
            to_delete = edited_df[edited_df["Delete"] == True]["User"].tolist()
            if "basha" in to_delete: st.error("Cannot delete Owner!")
            elif to_delete:
                for u in to_delete: del fresh_db["users"][u]
                save_data(fresh_db)
                st.success("Deleted!")
                time.sleep(1)
                st.rerun()

    with tab4:
        if db["logs"]:
            df = pd.DataFrame(db["logs"])
            st.dataframe(df)
            st.download_button("📥 Download", df.to_csv().encode('utf-8'), "report.csv")
        else: st.info("No data.")

# --- 🕵️‍♂️ SCRAPER V15 ---
st.markdown("---")

# Balance Check Logic
current_balance = user_data.get('credits', 0)
max_leads_possible = int(current_balance / LEAD_COST) if role != "owner" else 1000

# UI
c1, c2, c3 = st.columns([2, 1, 1])
keyword = c1.text_input("Enter Business & City", "Gyms in Chennai")

slider_default = 5 if max_leads_possible >= 5 else 1
if max_leads_possible == 0: slider_default = 0

leads_requested = c2.slider("Leads Needed", 0, max_leads_possible, slider_default)
estimated_cost = leads_requested * LEAD_COST
min_rating = c3.slider("⭐ Min Rating", 0.0, 5.0, 3.5, 0.5)
enable_email = st.checkbox("📧 Enable Email Extraction")

if role != "owner":
    if current_balance < LEAD_COST:
        st.error(f"⛔ Low Balance! Min required: ₹{LEAD_COST}")
    else:
        st.info(f"💰 Cost: ₹{estimated_cost}")

if st.button("🚀 Start Vettai"):
    fresh_db = load_data() # Critical Reload
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
                    if rating >= min_rating and l not in fresh_db["leads"]: links_to_visit.add(l)
                except: pass
            scrolls += 1
        
        status.info(f"✅ Found {len(links_to_visit)} Targets. Extracting...")
        unique_links = list(links_to_visit)[:leads_requested]
        progress = st.progress(0)
        
        for i, link in enumerate(unique_links):
            # LIVE BALANCE CHECK from FILE
            fresh_db = load_data()
            if fresh_db["users"][current_user]["credits"] < LEAD_COST and role != "owner":
                status.error("❌ Balance Over! Stopping...")
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
                
                # UPDATE DB
                fresh_db["leads"].append(link)
                if phone != "No Number": fresh_db["leads"].append(phone)
                
                if role != "owner":
                    fresh_db["users"][current_user]["credits"] -= LEAD_COST
                
                save_data(fresh_db) # Save constantly
                
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
            st.success(f"Done! Spent: ₹{total_cost}")
            time.sleep(2)
            st.rerun()
        else: st.warning("No leads found.")
    except Exception as e: st.error(f"Error: {e}")
    finally: driver.quit()