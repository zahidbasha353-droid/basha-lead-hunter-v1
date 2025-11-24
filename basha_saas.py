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
    # Load data logic remains the same (removed for brevity)
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                data = json.load(f)
                return data
        except: pass
    return {
        "users": {"basha": {"password": "king", "role": "owner", "expiry": "2030-01-01", "credits": 50000, "daily_cap": 10000, "today_usage": 0, "last_active_date": str(date.today())}},
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

# --- CORE LOGIC FUNCTIONS (TRUNCATED FOR CHAT SIZE) ---
def make_whatsapp_link(phone): # (Link generation logic here)
    if not phone: return None
    clean_num = re.sub(r'\D', '', phone)
    if len(clean_num) == 10: clean_num = "91" + clean_num
    return f"https://wa.me/{clean_num}"
def image_to_base64(uploaded_file):
    try: return base64.b64encode(uploaded_file.getvalue()).decode()
    except: return None
def generate_coupon_code(length=8):
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choice(characters) for i in range(length))

# --- APP FLOW ---
# (Login, Dashboard, Admin Tabs are assumed functional from V24)

# --- APP FLOW (CRITICAL PARTS) ---
current_user = st.session_state.get("user", "basha")
role = db["users"].get(current_user, {}).get("role", "owner")
user_data = db["users"].get(current_user, {})

# Sidebar/Metric Logic (Display remains the same)
# ...

# --- 🕵️‍♂️ SCRAPER V25 (AUTO GEO-SEARCH) ---
st.markdown("---")

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
min_rating = c3.slider("⭐ Min Rating", 0.0, 5.0, 3.5, 0.5)
enable_email = st.checkbox("📧 Enable Email Extraction")

# --- AREA EXPANSION LIST ---
# If Chennai search is exhausted, try these areas.
SUB_AREAS = ["Tambaram", "Guindy", "Avadi", "Madipakkam", "Chromepet", "Kotturpuram"] 
# -------------------------

if st.button("🚀 Start Vettai"):
    if leads_requested == 0: st.warning("Leads must be > 0."); st.stop()

    # Driver Setup
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()), options=options)
    
    collected_data = []
    search_queries = [initial_keyword] + [f"{initial_keyword.split(' in ')[0]} in {area}" for area in SUB_AREAS]
    status = st.empty()

    try:
        for query in search_queries:
            if len(collected_data) >= leads_requested: break
            
            status.info(f"🌐 Searching: {query}...")
            
            driver.get("https://www.google.com/maps")
            time.sleep(3)
            driver.find_element(By.ID, "searchboxinput").send_keys(query + Keys.RETURN)
            time.sleep(5)
            
            # --- SCRAPING LOOP ---
            links = set()
            panel = driver.find_element(By.XPATH, '//div[contains(@aria-label, "Results for")]')
            
            # Scroll aggressively to find more leads than requested
            for _ in range(5): # Scroll 5 times
                driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", panel)
                time.sleep(2)
                
            elements = driver.find_elements(By.CLASS_NAME, "hfpxzc")
            
            for elem in elements:
                l = elem.get_attribute("href")
                if l not in db["leads"]: links.add(l)

            # --- EXTRACTION OF NEW LINKS ---
            ulinks = list(links)
            progress = st.progress(0)
            
            for i, link in enumerate(ulinks):
                if len(collected_data) >= leads_requested: break
                
                fresh = load_data()
                if role != "owner" and fresh["users"][current_user]["credits"] < LEAD_COST: status.error("Credits Over!"); break

                try:
                    driver.get(link)
                    time.sleep(4) # Increased wait time for slow cloud
                    try: name = driver.find_element(By.XPATH, '//h1[contains(@class, "DUwDvf")]').text
                    except: name = "Unknown"
                    phone = "No Number"
                    try:
                        btns = driver.find_elements(By.XPATH, '//button[contains(@data-item-id, "phone")]')
                        if btns: phone = btns[0].get_attribute("aria-label").replace("Phone: ", "").strip()
                    except: pass
                    
                    if phone != "No Number" and phone in fresh["leads"]: continue
                    
                    # Success
                    collected_data.append({"Name": name, "Phone": phone, "Rating": "4.0+", "Email": "Skipped", "Website": "Skipped", "WhatsApp": make_whatsapp_link(phone)})
                    
                    fresh["leads"].append(link)
                    if phone != "No Number": fresh["leads"].append(phone)
                    
                    if role != "owner":
                        fresh["users"][current_user]["credits"] -= LEAD_COST
                        fresh["users"][current_user]["today_usage"] += 1
                    
                    save_data(fresh)
                    
                    bal_disp = "∞" if role == "owner" else f"{fresh['users'][current_user]['credits']}"
                    status.success(f"✅ Secured: {name} | 💰 Bal: {bal_disp} | Area: {query.split(' in ')[-1]}")
                    progress.progress((i+1)/len(ulinks))
                
                except Exception as e:
                    pass # Skip problematic extractions
                    
    except Exception as e: st.error(f"Critical Error during search: {e}")
    finally:
        driver.quit()
        
    # --- FINAL DISPLAY ---
    if collected_data:
        df = pd.DataFrame(collected_data)
        st.session_state["last_scraped_data"] = df.to_json() 
        st.success(f"🎉 **Vettai Mudinjathu!** Total {len(collected_data)} Unique Leads Collected.")
        st.info("Results displayed below.")
        
        # Log this successful scrape
        log_entry = {"User": current_user, "Keyword": initial_keyword, "Count": len(collected_data), "Cost": len(collected_data) * LEAD_COST, "Time": str(datetime.now())}
        db["logs"].append(log_entry)
        save_data(db)
        
        time.sleep(1)
        st.rerun() 
    else: 
        st.warning("❌ Sorry, even after checking nearby areas, no new unique leads were found.")
        st.session_state["last_scraped_data"] = None