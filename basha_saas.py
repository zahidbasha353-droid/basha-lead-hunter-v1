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
    # Default Users
    st.session_state["user_db"] = {
        "basha": {"password": "king", "role": "owner", "expiry": "2030-01-01", "daily_limit": 10000},
        "client1": {"password": "guest", "role": "client", "expiry": "2025-12-30", "daily_limit": 5}
    }

# Store Generated Coupons here
if "redeem_codes" not in st.session_state:
    st.session_state["redeem_codes"] = {}

if "global_leads_db" not in st.session_state:
    st.session_state["global_leads_db"] = set()

if "activity_log" not in st.session_state:
    st.session_state["activity_log"] = []

st.set_page_config(page_title="Basha Master V7", page_icon="🦁", layout="wide")

# --- 🛠️ HELPER FUNCTIONS ---
def generate_coupon(days, limit):
    # Generate Random Code (e.g., BAS8291)
    suffix = ''.join(random.choices(string.digits, k=4))
    code = f"BAS{suffix}"
    st.session_state["redeem_codes"][code] = {"days": days, "limit": limit}
    return code

def make_whatsapp_link(phone):
    if not phone or phone == "No Number": return None
    clean_num = re.sub(r'\D', '', phone)
    if len(clean_num) == 10: clean_num = "91" + clean_num
    return f"https://wa.me/{clean_num}?text=Hi,%20saw%20your%20business%20on%20Google!"

# --- 🔐 LOGIN & REDEEM SYSTEM ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["user"] = None
    st.session_state["role"] = None

if not st.session_state["logged_in"]:
    st.markdown("## 🔐 Basha Master Access")
    
    # TABS FOR LOGIN vs REDEEM
    tab_login, tab_redeem = st.tabs(["🔑 Login", "🎟️ New User? Redeem Code"])
    
    # 1. LOGIN TAB
    with tab_login:
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.button("Login"):
            db = st.session_state["user_db"]
            if u in db and db[u]["password"] == p:
                exp = datetime.strptime(db[u]["expiry"], "%Y-%m-%d").date()
                if date.today() > exp: st.error("❌ Plan Expired!")
                else:
                    st.session_state["logged_in"] = True
                    st.session_state["user"] = u
                    st.session_state["role"] = db[u]["role"]
                    st.rerun()
            else: st.error("❌ Wrong ID/Password")

    # 2. REDEEM CODE TAB (One Time Use)
    with tab_redeem:
        st.info("Enter the One-Time Code given by Admin to register.")
        new_u = st.text_input("Choose your Username")
        new_p = st.text_input("Choose your Password", type="password")
        coupon = st.text_input("Enter Coupon Code (e.g., BAS8291)")
        
        if st.button("🚀 Redeem & Register"):
            if coupon in st.session_state["redeem_codes"]:
                if new_u in st.session_state["user_db"]:
                    st.error("⚠️ Username already taken! Choose another.")
                else:
                    # Get Plan Details from Coupon
                    details = st.session_state["redeem_codes"][coupon]
                    exp_date = (date.today() + timedelta(days=details['days'])).strftime("%Y-%m-%d")
                    
                    # Create User
                    st.session_state["user_db"][new_u] = {
                        "password": new_p,
                        "role": "client",
                        "expiry": exp_date,
                        "daily_limit": details['limit']
                    }
                    
                    # DELETE COUPON (Expire it immediately)
                    del st.session_state["redeem_codes"][coupon]
                    
                    st.success("✅ Registration Success! Please Login now.")
            else:
                st.error("❌ Invalid or Expired Code!")

    st.stop()

# --- 🖥️ DASHBOARD ---
current_user = st.session_state["user"]
role = st.session_state["role"]

# Auto-logout if user is deleted
if current_user not in st.session_state["user_db"]:
    st.session_state["logged_in"] = False
    st.rerun()

user_data = st.session_state["user_db"][current_user]

st.sidebar.title(f"👤 {current_user.capitalize()}")
st.sidebar.badge(role.upper())
st.sidebar.write(f"⚡ Limit: {user_data['daily_limit']} / Day")
st.sidebar.write(f"📅 Valid till: {user_data['expiry']}")

if st.sidebar.button("Logout", type="primary"):
    st.session_state["logged_in"] = False
    st.rerun()

# --- 👑 ADMIN EMPIRE (Owner Only) ---
if role == "owner":
    st.title("🛠️ Admin Empire")
    
    # THREE MAIN TABS
    tab1, tab2, tab3 = st.tabs(["🗑️ Manage Users (Delete)", "🎟️ Generate Coupons", "📊 Reports"])
    
    # TAB 1: DELETE USERS
    with tab1:
        st.subheader("Manage Active Users")
        st.write("Tick the checkbox to remove a user.")
        
        # Prepare data for Table
        users_list = []
        for u, d in st.session_state["user_db"].items():
            users_list.append({
                "Username": u,
                "Password": d["password"],
                "Expiry": d["expiry"],
                "Limit": d["daily_limit"],
                "Delete": False # Initial Checkbox State
            })
        
        df_users = pd.DataFrame(users_list)
        
        # Editable Table
        edited_df = st.data_editor(
            df_users,
            column_config={
                "Delete": st.column_config.CheckboxColumn("Remove?", default=False)
            },
            disabled=["Username", "Password", "Expiry"], # Only allow checking Delete box
            hide_index=True,
            key="user_editor"
        )
        
        # Delete Button Logic
        if st.button("🗑️ Delete Selected Users"):
            to_delete = edited_df[edited_df["Delete"] == True]["Username"].tolist()
            
            if "basha" in to_delete:
                st.error("❌ You cannot delete the Owner (Basha)!")
            elif to_delete:
                for u in to_delete:
                    del st.session_state["user_db"][u]
                st.success(f"✅ Successfully Removed: {', '.join(to_delete)}")
                time.sleep(1)
                st.rerun()
            else:
                st.info("No users selected for deletion.")

    # TAB 2: GENERATE COUPONS
    with tab2:
        st.subheader("🎟️ Create Redeem Codes")
        c1, c2 = st.columns(2)
        days = c1.selectbox("Plan Duration", [7, 15, 30, 365], format_func=lambda x: f"{x} Days")
        limit = c2.number_input("Daily Lead Limit", value=50)
        
        if st.button("⚡ Generate New Code"):
            new_code = generate_coupon(days, limit)
            st.success(f"🔥 Code Generated: {new_code}")
            st.code(new_code, language="text")
            st.info("Copy this code. It can be used ONLY ONCE.")
            
        # Show Active Coupons
        if st.session_state["redeem_codes"]:
            st.write("### Active Unused Coupons:")
            st.json(st.session_state["redeem_codes"])
        else:
            st.write("No active coupons.")

    # TAB 3: REPORTS
    with tab3:
        if st.session_state["activity_log"]:
            df = pd.DataFrame(st.session_state["activity_log"])
            st.dataframe(df)
            st.download_button("📥 Download Report", df.to_csv().encode('utf-8'), "report.csv")
        else: st.info("No activity yet.")

# --- 🕵️‍♂️ V7 SCRAPER ENGINE ---
st.header("🦁 Basha Master V7: The Beast")
st.markdown("---")

c1, c2, c3 = st.columns([2, 1, 1])
keyword = c1.text_input("Enter Business & City", "Gyms in Chennai")
count = c2.slider("Leads Needed", 5, user_data['daily_limit'], 5)
min_rating = c3.slider("⭐ Min Rating", 0.0, 5.0, 3.5, 0.5)
enable_email = st.checkbox("📧 Enable Email Extraction (Slower but High Value)")

if st.button("🚀 Start Vettai"):
    status = st.empty()
    status.info("🌐 Booting Cloud Browser...")
    
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()),
        options=options
    )
    
    collected_data = []
    
    try:
        driver.get("https://www.google.com/maps")
        time.sleep(3)
        driver.find_element(By.ID, "searchboxinput").send_keys(keyword + Keys.RETURN)
        time.sleep(5)
        
        status.warning("🔍 Scanning for Top Rated Shops...")
        
        # --- LINK COLLECTION ---
        links_to_visit = set()
        scrolls = 0
        panel = driver.find_element(By.XPATH, '//div[contains(@aria-label, "Results for")]')
        
        while len(links_to_visit) < count and scrolls < 20:
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", panel)
            time.sleep(2)
            elements = driver.find_elements(By.CLASS_NAME, "hfpxzc")
            
            for elem in elements:
                try:
                    # Rating Logic
                    parent = elem.find_element(By.XPATH, "./..")
                    rating_text = parent.text 
                    match = re.search(r"(\d\.\d)", rating_text)
                    rating = float(match.group(1)) if match else 0.0
                    
                    link = elem.get_attribute("href")
                    if rating >= min_rating and link not in st.session_state["global_leads_db"]:
                        links_to_visit.add(link)
                except: pass
            scrolls += 1
            
        status.info(f"✅ Found {len(links_to_visit)} Targets. Extracting...")
        
        # --- EXTRACTION ---
        unique_links = list(links_to_visit)[:count]
        progress_bar = st.progress(0)
        
        for i, link in enumerate(unique_links):
            try:
                driver.get(link)
                time.sleep(2)
                
                try: name = driver.find_element(By.XPATH, '//h1[contains(@class, "DUwDvf")]').text
                except: name = "Unknown"
                
                phone = "No Number"
                try:
                    p_btns = driver.find_elements(By.XPATH, '//button[contains(@data-item-id, "phone")]')
                    if p_btns: phone = p_btns[0].get_attribute("aria-label").replace("Phone: ", "").strip()
                except: pass
                
                if phone != "No Number" and phone in st.session_state["global_leads_db"]: continue

                # Email
                email = "Skipped"
                website = "Not Found"
                if enable_email:
                    try:
                        web_btn = driver.find_elements(By.XPATH, '//a[contains(@data-item-id, "authority")]')
                        if web_btn:
                            website = web_btn[0].get_attribute("href")
                            # Simple Email Regex
                            try:
                                headers = {'User-Agent': 'Mozilla/5.0'}
                                r = requests.get(website, headers=headers, timeout=5)
                                soup = BeautifulSoup(r.text, 'html.parser')
                                mails = set(re.findall(r"[a-z0-9\.\-+_]+@[a-z0-9\.\-+_]+\.[a-z]+", soup.text, re.I))
                                if mails: email = list(mails)[0]
                            except: pass
                    except: pass
                
                collected_data.append({
                    "Name": name, "Phone": phone, "Rating": "4.0+", "Email": email,
                    "Website": website, "WhatsApp": make_whatsapp_link(phone)
                })
                
                st.session_state["global_leads_db"].add(link)
                if phone != "No Number": st.session_state["global_leads_db"].add(phone)
                
                processed_count = i + 1
                status.success(f"✅ Secured: {name} | 📞 {phone}")
                progress_bar.progress(processed_count / len(unique_links))
                
            except Exception as e: continue
            
        if collected_data:
            df = pd.DataFrame(collected_data)
            st.data_editor(
                df,
                column_config={
                    "WhatsApp": st.column_config.LinkColumn("Chat", display_text="📲 Chat"),
                    "Website": st.column_config.LinkColumn("Site")
                },
                hide_index=True
            )
            # Log
            st.session_state["activity_log"].append({
                "User": current_user, "Keyword": keyword, "Count": len(collected_data), "Time": datetime.now()
            })
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Excel", csv, "leads.csv", "text/csv")
        else:
            st.warning("No leads found.")

    except Exception as e: st.error(f"Error: {e}")
    finally: driver.quit()