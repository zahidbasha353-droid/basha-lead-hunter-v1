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

st.set_page_config(page_title="Basha Master V28", page_icon="🦁", layout="wide")

# --- 🛠️ HELPER FUNCTIONS ---
def image_to_base64(uploaded_file):
    try: return base64.b64encode(uploaded_file.getvalue()).decode()
    except: return None
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
    st.session_state["logged_in"] = False; st.session_state["user"] = None; st.session_state["role"] = None
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
                st.session_state["logged_in"] = True; st.session_state["user"] = u; st.session_state["role"] = fresh_db["users"][u]["role"]
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
with col_head1: st.title("🦁 Basha Master V28")
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

# --- RECHARGE & LOGOUT ---
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

if st.sidebar.button("Logout", type="primary"): st.session_state["logged_in"] = False; st.rerun()

# --- 👑 ADMIN EMPIRE (FULL LOGIC) ---
if role == "owner":
    st.title("🛠️ Admin Empire")
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🔔 Payments", "⚙️ Settings", "➕ Add User", "👥 Manage Users", "📊 Reports"])
    
    # TAB 1: PAYMENTS (APPROVE / DECLINE)
    with tab1:
        st.subheader("🔔 Pending Requests")
        pending = [r for r in db["payment_requests"] if r["status"] == "Pending"]
        
        if pending:
            for i, req in enumerate(pending):
                with st.container(border=True):
                    c1, c2, c3, c4, c5 = st.columns([2, 1, 2, 1, 1])
                    c1.write(f"👤 **{req['user']}**"); c2.write(f"💰 ₹{req['amount']}"); c3.write(f"🆔 `{req['utr']}`")
                    
                    # APPROVE BUTTON LOGIC (Fixed indentation issue)
                    if c4.button("✅", key=f"app_{i}"):
                        fresh = load_data()
                        fresh["users"][req['user']]["credits"] += req['amount']
                        for item in fresh["payment_requests"]: 
                            if item["utr"] == req["utr"]: 
                                item["status"] = "Approved"
                        save_data(fresh); st.success("Approved!"); st.rerun()
                    
                    # DECLINE BUTTON LOGIC
                    if c5.button("❌", key=f"dec_{i}"):
                        fresh = load_data()
                        fresh["payment_requests"] = [r for r in fresh["payment_requests"] if r["utr"] != req["utr"]]
                        save_data(fresh); st.warning("Declined"); st.rerun()
        else: st.info("No pending requests.")

    # TAB 2: SETTINGS
    with tab2:
        st.subheader("⚙️ Payment Settings")
        new_upi = st.text_input("UPI ID", value=db["settings"].get("upi_id", ""))
        uploaded_qr = st.file_uploader("Upload QR", type=['png', 'jpg'])
        if st.button("💾 Save"):
            db["settings"]["upi_id"] = new_upi
            if uploaded_qr: db["settings"]["qr_image"] = image_to_base64(uploaded_qr)
            save_data(db); st.success("Saved!")
        
        st.markdown("---")
        st.error("⚠️ **Danger Zone (For Testing Only)**")
        if st.button("🗑️ Reset All Lead History (Clear Duplicates)"):
            fresh = load_data()
            fresh["leads"] = [] 
            save_data(fresh)
            st.success("History Cleared! You can search 'Gyms' again.")

    # TAB 3: ADD USER
    with tab3:
        st.subheader("➕ Add New User")
        with st.form("add"):
            c1, c2 = st.columns(2); mu = c1.text_input("Username"); mp = c2.text_input("Password")
            c3, c4 = st.columns(2); ml = c3.number_input("Wallet Balance (₹)", 100); md = c4.selectbox("Validity", [30, 90, 365])
            dlim = st.number_input("Daily Limit", 300); mph = st.text_input("Phone")
            if st.form_submit_button("Create"):
                fresh = load_data()
                if mu in fresh["users"]: st.error("Exists!")
                else:
                    exp = (date.today() + timedelta(days=md)).strftime("%Y-%m-%d")
                    fresh["users"][mu] = {"password": mp, "role": "client", "expiry": exp, "credits": ml, "daily_cap": dlim, "today_usage": 0, "last_active_date": str(date.today())}
                    save_data(fresh); st.success("Created!");
                    if mph: wa = make_login_share_link(mph, mu, mp); st.markdown(f'<a href="{wa}" target="_blank"><button>📲 Send WhatsApp</button></a>', unsafe_allow_html=True)

    # TAB 4: MANAGE USERS
    with tab4:
        st.subheader("👥 Active Users List")
        fresh = load_data()
        users_list = [{"User": u, "Password": d["password"], "Balance": f"₹{d.get('credits',0)}", "Limit": d.get('daily_cap', 300), "Role": d["role"], "Delete": False} for u, d in fresh["users"].items()]
        edited_df = st.data_editor(pd.DataFrame(users_list), column_config={"Delete": st.column_config.CheckboxColumn("Remove?", default=False), "Password": st.column_config.TextColumn("Password")}, disabled=["User", "Role", "Balance"], hide_index=True)
        if st.button("🗑️ Delete Selected"):
            to_delete = edited_df[edited_df["Delete"] == True]["User"].tolist()
            if "basha" in to_delete: st.error("Can't delete Owner!")
            elif to_delete:
                for u in to_delete: del fresh["users"][u]
                save_data(fresh); st.success("Deleted!"); st.rerun()

    # TAB 5: REPORTS
    with tab5:
        st.subheader("📊 Activity Log")
        if db["logs"]: 
            df_log = pd.DataFrame(db["logs"])
            st.dataframe(df_log, use_container_width=True)
            c1, c2 = st.columns([1, 1])
            csv_report = df_log.to_csv(index=False).encode('utf-8')
            c1.download_button("📥 Download Report (Excel)", csv_report, "basha_report.csv", "text/csv", use_container_width=True)
            if c2.button("🗑️ Clear All Reports", use_container_width=True):
                db["logs"] = []
                save_data(db); st.success("Reports Cleared!"); st.rerun()


# --- 🕵️‍♂️ SCRAPER V28 (FINAL LOGIC) ---
st.markdown("---")

exp_date = datetime.strptime(user_data["expiry"], "%Y-%m-%d").date()
if date.today() > exp_date and role != "owner": st.error("⛔ PLAN EXPIRED!"); st.stop()

if role != "owner":
    remaining_daily = user_data.get('daily_cap', 300) - user_data.get('today_usage', 0)
    if remaining_daily <= 0: st.error("⛔ Daily Limit Reached!"); st.stop()
    if user_data.get('credits', 0) < LEAD_COST: st.error(f"⛔ Low Credits! Min: {LEAD_COST}"); st.stop()
else: remaining_daily = 999999

c1, c2, c3 = st.columns([2, 1, 1])
initial_keyword = c1.text_input("Enter Business & City", "Gyms in Chennai")
current_bal = user_data.get('credits', 0)
max_by_money = int(current_bal / LEAD_COST)
max_allowed = min(max_by_money, remaining_daily) if role != "owner" else 10000
slider_def = 5 if max_allowed >= 5 else 1
if max_allowed == 0 and role != "owner": slider_def = 0

leads_requested = c2.slider("Leads Needed", 0, max_allowed, slider_def)
estimated_cost = leads_requested * LEAD_COST
min_rating = c3.slider("⭐ Min Rating", 0.0, 5.0, 3.5, 0.5)
enable_email = st.checkbox("📧 Enable Email Extraction")

if role != "owner": st.info(f"💰 Cost: {estimated_cost} Credits | 📊 Limit Left: {remaining_daily}")

if st.button("🚀 Start Vettai"):
    fresh = load_data()
    if role != "owner" and fresh["users"][current_user]["credits"] < LEAD_COST: st.error("Low Credits!"); st.stop()

    status = st.empty()
    status.info("🌐 Booting Cloud Browser...")
    
    options = webdriver.ChromeOptions()
    options.add_argument("--headless"); options.add_argument("--no-sandbox"); options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()), options=options)
    
    collected_data = []
    try:
        # --- GEO-SEARCH SETUP ---
        SUB_AREAS = ["Tambaram", "Guindy", "Avadi", "Madipakkam", "Chromepet", "Ambattur", "Pallavaram"] 
        search_queries = [initial_keyword] + [f"{initial_keyword.split(' in ')[0]} in {area}" for area in SUB_AREAS]

        for query in search_queries:
            if len(collected_data) >= leads_requested: break
            
            status.info(f"🌐 Searching: {query}...")
            
            driver.get("https://www.google.com/maps")
            time.sleep(3)
            driver.find_element(By.ID, "searchboxinput").send_keys(query + Keys.RETURN)
            time.sleep(5)
            
            # --- LINK COLLECTION ---
            links = set()
            panel = driver.find_element(By.XPATH, '//div[contains(@aria-label, "Results for")]')
            for _ in range(5): 
                driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", panel)
                time.sleep(2)
            elements = driver.find_elements(By.CLASS_NAME, "hfpxzc")
            for elem in elements:
                try:
                    l = elem.get_attribute("href")
                    if l not in db["leads"]: links.add(l)
                except: pass
            
            ulinks = list(links)[:leads_requested - len(collected_data)]
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
                    
                    email, website = "Skipped", "Not Found"
                    # Email Logic (omitted)
                    
                    collected_data.append({"Name": name, "Phone": phone, "Rating": "4.0+", "Email": email, "Website": website, "WhatsApp": make_whatsapp_link(phone)})
                    
                    fresh["leads"].append(link)
                    if phone != "No Number": fresh["leads"].append(phone)
                    
                    if role != "owner":
                        fresh["users"][current_user]["credits"] -= LEAD_COST
                        fresh["users"][current_user]["today_usage"] += 1
                    
                    save_data(fresh)
                    bal_disp = "∞" if role == "owner" else f"{fresh['users'][current_user]['credits']}"
                    status.success(f"✅ Secured: {name} | 🌟 Credits Left: {bal_disp}")
                    progress.progress((i+1)/len(ulinks))
                except: pass
            
        if collected_data:
            total_cost = len(collected_data) * LEAD_COST if role != "owner" else 0
            df = pd.DataFrame(collected_data)
            st.session_state["last_scraped_data"] = df.to_json() 
            fresh["logs"].append({"User": current_user, "Keyword": initial_keyword, "Count": len(collected_data), "Cost": total_cost, "Time": str(datetime.now())})
            save_data(fresh)
            st.success("Completed! Displaying results...")
            time.sleep(1)
            st.rerun()
        else: st.warning("No new unique leads found.")
    except Exception as e: st.error(f"Error: {e}")
    finally: driver.quit()

# --- 📊 FINAL PERSISTENT DATA DISPLAY ---
if st.session_state["last_scraped_data"]:
    st.markdown("---")
    st.subheader("Results (Scrape Complete)")
    try:
        df_display = pd.read_json(st.session_state["last_scraped_data"])
        st.data_editor(df_display, column_config={"WhatsApp": st.column_config.LinkColumn("Chat", display_text="📲 Chat"), "Website": st.column_config.LinkColumn("Site")}, hide_index=True)
        csv = df_display.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Excel", csv, "leads.csv", "text/csv")
    except:
        st.error("Error displaying data.")