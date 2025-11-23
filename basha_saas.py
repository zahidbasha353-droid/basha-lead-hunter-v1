import streamlit as st
import time
import pandas as pd
import re
import requests
import random
import string
from datetime import datetime, timedelta, date
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
from bs4 import BeautifulSoup

# --- 🧠 CENTRAL MEMORY ---
if "user_db" not in st.session_state:
    st.session_state["user_db"] = {
        "basha": {"password": "king", "role": "owner", "expiry": "2030-01-01", "daily_limit": 10000},
        "client1": {"password": "guest", "role": "client", "expiry": "2025-12-30", "daily_limit": 5}
    }

if "redeem_codes" not in st.session_state:
    st.session_state["redeem_codes"] = {}

if "global_leads_db" not in st.session_state:
    st.session_state["global_leads_db"] = set()

if "activity_log" not in st.session_state:
    st.session_state["activity_log"] = []

st.set_page_config(page_title="Basha Master V8", page_icon="🦁", layout="wide")

# --- 🛠️ HELPER FUNCTIONS ---
def generate_coupon(days, limit):
    suffix = ''.join(random.choices(string.digits, k=4))
    code = f"BAS{suffix}"
    st.session_state["redeem_codes"][code] = {"days": days, "limit": limit}
    return code

def make_whatsapp_link(phone):
    if not phone or phone == "No Number": return None
    clean_num = re.sub(r'\D', '', phone)
    if len(clean_num) == 10: clean_num = "91" + clean_num
    return f"https://wa.me/{clean_num}?text=Hi,%20saw%20your%20business%20on%20Google!"

# --- 🔐 LOGIN SYSTEM ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["user"] = None
    st.session_state["role"] = None

if not st.session_state["logged_in"]:
    st.markdown("## 🔐 Basha Master Access")
    
    tab_login, tab_redeem = st.tabs(["🔑 Login", "🎟️ New User Register"])
    
    with tab_login:
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.button("Login"):
            db = st.session_state["user_db"]
            if u in db and db[u]["password"] == p:
                # Expired users can login but limited access logic can be added
                st.session_state["logged_in"] = True
                st.session_state["user"] = u
                st.session_state["role"] = db[u]["role"]
                st.rerun()
            else: st.error("❌ Wrong ID/Password")

    with tab_redeem:
        st.info("Use this to create a NEW account.")
        new_u = st.text_input("Choose Username")
        new_p = st.text_input("Choose Password", type="password")
        coupon = st.text_input("Enter Coupon Code (e.g., BAS8291)")
        
        if st.button("🚀 Redeem & Register"):
            if coupon in st.session_state["redeem_codes"]:
                if new_u in st.session_state["user_db"]:
                    st.error("⚠️ Username taken!")
                else:
                    details = st.session_state["redeem_codes"][coupon]
                    exp_date = (date.today() + timedelta(days=details['days'])).strftime("%Y-%m-%d")
                    st.session_state["user_db"][new_u] = {
                        "password": new_p, "role": "client", "expiry": exp_date, "daily_limit": details['limit']
                    }
                    del st.session_state["redeem_codes"][coupon]
                    st.success("✅ Account Created! Please Login.")
            else: st.error("❌ Invalid Code!")
    st.stop()

# --- 🖥️ DASHBOARD & RECHARGE SYSTEM ---
current_user = st.session_state["user"]
role = st.session_state["role"]

if current_user not in st.session_state["user_db"]:
    st.session_state["logged_in"] = False
    st.rerun()

user_data = st.session_state["user_db"][current_user]

# SIDEBAR INFO
st.sidebar.title(f"👤 {current_user.capitalize()}")
st.sidebar.badge(role.upper())
st.sidebar.metric("⚡ Daily Limit", f"{user_data['daily_limit']}")
st.sidebar.caption(f"📅 Valid till: {user_data['expiry']}")

# --- 💎 RECHARGE SYSTEM (NEW) ---
if role == "client":
    with st.sidebar.expander("💎 Recharge / Top-up", expanded=True):
        st.write("Enter coupon to increase limit/validity.")
        recharge_code = st.text_input("Enter Coupon Code")
        
        if st.button("Apply Recharge"):
            if recharge_code in st.session_state["redeem_codes"]:
                data = st.session_state["redeem_codes"][recharge_code]
                
                # Update User Data
                new_limit = data['limit']
                new_expiry = (date.today() + timedelta(days=data['days'])).strftime("%Y-%m-%d")
                
                st.session_state["user_db"][current_user]["daily_limit"] = new_limit
                st.session_state["user_db"][current_user]["expiry"] = new_expiry
                
                # Burn Coupon
                del st.session_state["redeem_codes"][recharge_code]
                
                st.success(f"✅ Upgraded! Limit: {new_limit}, Valid: {new_expiry}")
                time.sleep(2)
                st.rerun()
            else:
                st.error("❌ Invalid Code")

if st.sidebar.button("Logout", type="primary"):
    st.session_state["logged_in"] = False
    st.rerun()

# --- 👑 ADMIN EMPIRE ---
if role == "owner":
    st.title("🛠️ Admin Empire")
    tab1, tab2, tab3 = st.tabs(["🗑️ Manage Users", "🎟️ Generate Codes", "📊 Reports"])
    
    with tab1:
        st.subheader("Manage Users")
        users_list = [{"Username": u, "Pass": d["password"], "Exp": d["expiry"], "Limit": d["daily_limit"], "Delete": False} 
                      for u, d in st.session_state["user_db"].items()]
        
        edited_df = st.data_editor(pd.DataFrame(users_list), column_config={"Delete": st.column_config.CheckboxColumn("Remove?", default=False)}, 
                                   disabled=["Username"], hide_index=True, key="user_editor")
        
        if st.button("🗑️ Delete Selected"):
            to_delete = edited_df[edited_df["Delete"] == True]["Username"].tolist()
            if "basha" in to_delete: st.error("❌ Can't delete Owner!")
            elif to_delete:
                for u in to_delete: del st.session_state["user_db"][u]
                st.success(f"✅ Deleted: {to_delete}")
                time.sleep(1)
                st.rerun()

    with tab2:
        st.subheader("🎟️ Create Recharge/Register Codes")
        c1, c2 = st.columns(2)
        days = c1.selectbox("Validity", [7, 15, 30, 365], format_func=lambda x: f"{x} Days")
        limit = c2.number_input("Daily Limit", value=50)
        if st.button("⚡ Generate Code"):
            code = generate_coupon(days, limit)
            st.success(f"🔥 Code: {code}")
            st.code(code, language="text")
            st.info("Share this for New Register OR Existing User Recharge.")
            
        if st.session_state["redeem_codes"]:
            st.write("### Active Coupons:")
            st.json(st.session_state["redeem_codes"])

    with tab3:
        if st.session_state["activity_log"]:
            df = pd.DataFrame(st.session_state["activity_log"])
            st.dataframe(df)
            st.download_button("📥 Download Report", df.to_csv().encode('utf-8'), "report.csv")
        else: st.info("No data.")

# --- 🕵️‍♂️ SCRAPER ENGINE V8 ---
st.header("🦁 Basha Master V8: The Beast")
st.markdown("---")

# Expired User Check
exp_date = datetime.strptime(user_data["expiry"], "%Y-%m-%d").date()
if date.today() > exp_date and role != "owner":
    st.error("⛔ YOUR PLAN EXPIRED! Please buy a Recharge Code from Admin and enter it in Sidebar.")
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
                    if rating >= min_rating and l not in st.session_state["global_leads_db"]: links_to_visit.add(l)
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
                
                if phone != "No Number" and phone in st.session_state["global_leads_db"]: continue

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
                st.session_state["global_leads_db"].add(link)
                if phone != "No Number": st.session_state["global_leads_db"].add(phone)
                
                status.success(f"✅ Secured: {name} | {phone}")
                progress.progress((i+1)/len(unique_links))
            except: continue
            
        if collected_data:
            df = pd.DataFrame(collected_data)
            st.data_editor(df, column_config={"WhatsApp": st.column_config.LinkColumn("Chat", display_text="📲 Chat"), "Website": st.column_config.LinkColumn("Site")}, hide_index=True)
            st.session_state["activity_log"].append({"User": current_user, "Keyword": keyword, "Count": len(collected_data), "Time": datetime.now()})
            st.download_button("📥 Download Excel", df.to_csv(index=False).encode('utf-8'), "leads.csv", "text/csv")
        else: st.warning("No leads found.")
    except Exception as e: st.error(f"Error: {e}")
    finally: driver.quit()