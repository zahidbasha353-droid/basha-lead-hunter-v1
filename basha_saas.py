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

def load_data():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    # Default Data if file doesn't exist
    return {
        "users": {
            "basha": {"password": "king", "role": "owner", "expiry": "2030-01-01", "daily_limit": 10000},
            "client1": {"password": "guest", "role": "client", "expiry": "2025-12-30", "daily_limit": 5}
        },
        "coupons": {
            "BASHA100": {"days": 365, "limit": 100} # Master Coupon
        },
        "leads": [], # To store taken leads link to avoid duplicates
        "logs": []
    }

def save_data(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

# Load DB into Session State
if "db_data" not in st.session_state:
    st.session_state["db_data"] = load_data()

# Shortcut variables for easy access
db = st.session_state["db_data"]

st.set_page_config(page_title="Basha Master V11", page_icon="🦁", layout="wide")

# --- 🛠️ HELPER FUNCTIONS ---
def generate_coupon(days, limit):
    suffix = ''.join(random.choices(string.digits, k=4))
    code = f"BAS{suffix}"
    # Update DB
    db["coupons"][code] = {"days": days, "limit": limit}
    save_data(db) # Save to File immediately
    return code

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
    st.markdown("## 🔐 Basha Master Access (V11)")
    
    tab_login, tab_redeem = st.tabs(["🔑 Login", "🎟️ Redeem Code (New User)"])
    
    with tab_login:
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.button("Login"):
            users = db["users"]
            if u in users and users[u]["password"] == p:
                st.session_state["logged_in"] = True
                st.session_state["user"] = u
                st.session_state["role"] = users[u]["role"]
                st.rerun()
            else: st.error("❌ Wrong ID/Password")

    with tab_redeem:
        st.info("💡 Data is now saved permanently in file.")
        new_u = st.text_input("Choose Username")
        new_p = st.text_input("Choose Password", type="password")
        coupon = st.text_input("Enter Coupon Code")
        
        if st.button("🚀 Redeem & Register"):
            if coupon in db["coupons"]:
                if new_u in db["users"]:
                    st.error("⚠️ Username taken!")
                else:
                    details = db["coupons"][coupon]
                    exp_date = (date.today() + timedelta(days=details['days'])).strftime("%Y-%m-%d")
                    
                    # Create User
                    db["users"][new_u] = {
                        "password": new_p, "role": "client", "expiry": exp_date, "daily_limit": details['limit']
                    }
                    
                    # Delete Code (unless Master)
                    if coupon != "BASHA100":
                        del db["coupons"][coupon]
                    
                    save_data(db) # SAVE TO FILE
                    st.success("✅ Account Created! Login Now.")
            else: st.error("❌ Invalid Code!")
    st.stop()

# --- 🖥️ DASHBOARD ---
current_user = st.session_state["user"]
role = st.session_state["role"]
if current_user not in db["users"]:
    st.session_state["logged_in"] = False
    st.rerun()
user_data = db["users"][current_user]

# Sidebar
st.sidebar.title(f"👤 {current_user.capitalize()}")
st.sidebar.badge(role.upper())
st.sidebar.metric("⚡ Daily Limit", f"{user_data['daily_limit']}")
st.sidebar.caption(f"📅 Valid till: {user_data['expiry']}")

if role == "client":
    with st.sidebar.expander("💎 Recharge / Top-up"):
        recharge_code = st.text_input("Enter Coupon Code")
        if st.button("Apply"):
            if recharge_code in db["coupons"]:
                data = db["coupons"][recharge_code]
                new_expiry = (date.today() + timedelta(days=data['days'])).strftime("%Y-%m-%d")
                
                db["users"][current_user]["daily_limit"] = data['limit']
                db["users"][current_user]["expiry"] = new_expiry
                
                if recharge_code != "BASHA100":
                    del db["coupons"][recharge_code]
                
                save_data(db) # SAVE
                st.success("✅ Recharge Successful!")
                time.sleep(1)
                st.rerun()
            else: st.error("Invalid Code")

if st.sidebar.button("Logout", type="primary"):
    st.session_state["logged_in"] = False
    st.rerun()

# --- 👑 ADMIN EMPIRE (UPDATED) ---
if role == "owner":
    st.title("🛠️ Admin Empire")
    tab1, tab2, tab3, tab4 = st.tabs(["👥 Manage Users", "➕ Direct Add", "🎟️ Coupons", "📊 Reports"])
    
    with tab1:
        st.subheader("Active Users List")
        users_list = [{"Username": u, "Pass": d["password"], "Exp": d["expiry"], "Limit": d["daily_limit"], "Delete": False} 
                      for u, d in db["users"].items()]
        edited_df = st.data_editor(pd.DataFrame(users_list), column_config={"Delete": st.column_config.CheckboxColumn("Remove?", default=False)}, 
                                   disabled=["Username"], hide_index=True, key="user_editor")
        if st.button("🗑️ Delete Selected"):
            to_delete = edited_df[edited_df["Delete"] == True]["Username"].tolist()
            if "basha" in to_delete: st.error("❌ Can't delete Owner!")
            elif to_delete:
                for u in to_delete: del db["users"][u]
                save_data(db) # SAVE
                st.success(f"✅ Deleted: {to_delete}")
                time.sleep(1)
                st.rerun()

    with tab2:
        st.subheader("➕ Manual Add User")
        with st.form("manual_add"):
            c1, c2 = st.columns(2)
            mu = c1.text_input("New Username")
            mp = c2.text_input("New Password")
            c3, c4 = st.columns(2)
            ml = c3.number_input("Daily Limit", 50)
            md = c4.selectbox("Validity", [30, 90, 365], format_func=lambda x: f"{x} Days")
            m_phone = st.text_input("Phone (Optional)", placeholder="9876543210")
            
            if st.form_submit_button("Create User"):
                if mu in db["users"]:
                    st.error("Username exists!")
                else:
                    exp = (date.today() + timedelta(days=md)).strftime("%Y-%m-%d")
                    db["users"][mu] = {"password": mp, "role": "client", "expiry": exp, "daily_limit": ml}
                    save_data(db) # SAVE
                    st.success(f"✅ User '{mu}' Created!")
                    if m_phone:
                        wa_link = make_login_share_link(m_phone, mu, mp)
                        st.markdown(f'<a href="{wa_link}" target="_blank"><button>📲 Send WhatsApp</button></a>', unsafe_allow_html=True)

    with tab3:
        st.subheader("🎟️ Generate Codes")
        c1, c2 = st.columns(2)
        days = c1.selectbox("Validity", [7, 15, 30], key="g_days")
        limit = c2.number_input("Limit", 50, key="g_limit")
        if st.button("⚡ Generate"):
            code = generate_coupon(days, limit)
            st.success(f"Code: {code}")
            st.code(code)
        
        st.write("### Active Coupons")
        st.json(db["coupons"])

    with tab4:
        if db["logs"]:
            df = pd.DataFrame(db["logs"])
            st.dataframe(df)
            st.download_button("📥 Download", df.to_csv().encode('utf-8'), "report.csv")
        else: st.info("No data.")

# --- 🕵️‍♂️ SCRAPER V11 ---
st.header("🦁 Basha Master V11: The Beast")
st.markdown("---")

exp_date = datetime.strptime(user_data["expiry"], "%Y-%m-%d").date()
if date.today() > exp_date and role != "owner":
    st.error("⛔ PLAN EXPIRED! Recharge needed.")
    st.stop()

c1, c2, c3 = st.columns([2, 1, 1])
keyword = c1.text_input("Enter Business & City", "Gyms in Chennai")
count = c2.slider("Leads Needed", 5, user_data['daily_limit'], 5)
min_rating = c3.slider("⭐ Min Rating", 0.0, 5.0, 3.5, 0.5)
enable_email = st.checkbox("📧 Enable Email Extraction")

if st.button("🚀 Start Vettai"):
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
        while len(links_to_visit) < count and scrolls < 20:
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", panel)
            time.sleep(2)
            elements = driver.find_elements(By.CLASS_NAME, "hfpxzc")
            for elem in elements:
                try:
                    rating = 0.0
                    try: rating = float(re.search(r"(\d\.\d)", elem.find_element(By.XPATH, "./..").text).group(1))
                    except: pass
                    l = elem.get_attribute("href")
                    # Check Global Leads from DB File
                    if rating >= min_rating and l not in db["leads"]: links_to_visit.add(l)
                except: pass
            scrolls += 1
        
        status.info(f"✅ Found {len(links_to_visit)} Targets. Extracting...")
        unique_links = list(links_to_visit)[:count]
        progress = st.progress(0)
        
        for i, link in enumerate(unique_links):
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
                
                if phone != "No Number" and phone in db["leads"]: continue
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
                
                # Update DB (Leads)
                db["leads"].append(link)
                if phone != "No Number": db["leads"].append(phone)
                
                status.success(f"✅ Secured: {name} | {phone}")
                progress.progress((i+1)/len(unique_links))
            except: continue
            
        if collected_data:
            # Update DB (Logs)
            db["logs"].append({"User": current_user, "Keyword": keyword, "Count": len(collected_data), "Time": str(datetime.now())})
            save_data(db) # SAVE EVERYTHING
            
            df = pd.DataFrame(collected_data)
            st.data_editor(df, column_config={"WhatsApp": st.column_config.LinkColumn("Chat", display_text="📲 Chat"), "Website": st.column_config.LinkColumn("Site")}, hide_index=True)
            st.download_button("📥 Download Excel", df.to_csv(index=False).encode('utf-8'), "leads.csv", "text/csv")
        else: st.warning("No leads found.")
    except Exception as e: st.error(f"Error: {e}")
    finally: driver.quit()