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
LEAD_COST = 2  # 1 Lead = ₹2

def load_data():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                data = json.load(f)
                # Ensure all necessary keys are present for stability
                for u in data["users"]:
                    if "credits" not in data["users"][u]: data["users"][u]["credits"] = 0
                    if "daily_cap" not in data["users"][u]: data["users"][u]["daily_cap"] = 300
                    if "today_usage" not in data["users"][u]: data["users"][u]["today_usage"] = 0
                if "payment_requests" not in data: data["payment_requests"] = []
                if "settings" not in data: data["settings"] = {"upi_id": "basha@upi", "qr_image": None}
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

# V26 FIX: Persistent Results Display
if "last_scraped_data" not in st.session_state:
    st.session_state["last_scraped_data"] = None

db = st.session_state["db_data"]

st.set_page_config(page_title="Basha Master V26", page_icon="🦁", layout="wide")

# --- 🛠️ HELPER FUNCTIONS (omitted for brevity) ---
# ... (All helper functions remain the same) ...

# --- 🔐 LOGIN SYSTEM ---
if "logged_in" not in st.session_state: st.session_state["logged_in"] = False; st.session_state["user"] = None; st.session_state["role"] = None
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

# --- 🖥️ DASHBOARD & UI ---
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
with col_head1: st.title("🦁 Basha Master V26")
with col_head2: st.metric(label="🌟 Credits", value=display_balance)

st.sidebar.title(f"👤 {current_user.capitalize()}")
st.sidebar.caption(f"📅 Plan Exp: {user_data['expiry']}")

# ... (Sidebar Quota/Recharge logic remains the same) ...
if st.sidebar.button("Logout", type="primary"): st.session_state["logged_in"] = False; st.rerun()

# --- 👑 ADMIN EMPIRE ---
if role == "owner":
    st.title("🛠️ Admin Empire")
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🔔 Payments", "⚙️ Settings", "➕ Add User", "👥 Manage Users", "📊 Reports"])
    
    # [TAB 5: REPORTS (WITH CLEAR BUTTON)]
    with tab5:
        st.subheader("📊 Activity Log")
        if db["logs"]: 
            df_log = pd.DataFrame(db["logs"])
            st.dataframe(df_log, use_container_width=True)
            
            c1, c2 = st.columns([1, 1])
            
            # 1. DOWNLOAD BUTTON
            csv_report = df_log.to_csv(index=False).encode('utf-8')
            c1.download_button("📥 Download Report (Excel)", csv_report, "basha_report.csv", "text/csv", use_container_width=True)

            # 2. CLEAR BUTTON (NEW FEATURE)
            if c2.button("🗑️ Clear All Reports", use_container_width=True):
                db["logs"] = []
                save_data(db)
                st.success("Reports Cleared!")
                time.sleep(1)
                st.rerun()

        else: st.info("No activity data found.")
    
    # ... (Other admin tabs logic omitted for brevity) ...


# --- 🕵️‍♂️ SCRAPER V26 (Display Fix) ---
st.markdown("---")
# Remaining logic for limits check...

c1, c2, c3 = st.columns([2, 1, 1])
keyword = c1.text_input("Enter Business & City", "Gyms in Chennai")
# ... (Slider logic remains the same) ...

if st.button("🚀 Start Vettai"):
    # ... (Scraping logic remains the same) ...
    # ... (After data collection and saving to fresh DB) ...
            
        if collected_data:
            total_cost = len(collected_data) * LEAD_COST if role != "owner" else 0
            # Save results to session state (The FIX for persistence)
            df = pd.DataFrame(collected_data)
            st.session_state["last_scraped_data"] = df.to_json() 
            
            # Log and Save DB
            fresh["logs"].append({"User": current_user, "Keyword": keyword, "Count": len(collected_data), "Cost": total_cost, "Time": str(datetime.now())})
            save_data(fresh)
            
            st.success("Completed! Displaying results...")
            time.sleep(1)
            st.rerun() # Triggers the final persistent display
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
    except Exception as e:
        st.error(f"Error displaying data. {e}")