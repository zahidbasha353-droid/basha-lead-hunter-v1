import streamlit as st
import time
import pandas as pd
from datetime import datetime, date
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType

# --- 🔐 USER CONFIGURATION ---
USERS = {
    "basha": {"password": "king", "role": "owner", "expiry": "2030-01-01", "daily_limit": 1000},
    "client1": {"password": "guest", "role": "client", "expiry": "2025-12-30", "daily_limit": 50}
}

st.set_page_config(page_title="Basha Lead Hunter Pro", page_icon="🕵️‍♂️", layout="wide")

# --- LOGIN LOGIC ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["user"] = None

def check_login(username, password):
    if username in USERS and USERS[username]["password"] == password:
        return "success"
    return "fail"

if not st.session_state["logged_in"]:
    st.title("🔐 Basha Master Login")
    user = st.text_input("Username")
    pwd = st.text_input("Password", type="password")
    if st.button("Login"):
        if check_login(user, pwd) == "success":
            st.session_state["logged_in"] = True
            st.session_state["user"] = user
            st.rerun()
        else:
            st.error("Wrong ID/Password")
    st.stop()

# --- MAIN APP ---
st.sidebar.success(f"Login: {st.session_state['user']}")
if st.sidebar.button("Logout"):
    st.session_state["logged_in"] = False
    st.rerun()

st.title("🤖 Basha Master: Cloud Lead Hunter")
search_keyword = st.text_input("Enter Business Type (e.g. Gyms in Chennai)")
target = st.slider("Leads Count", 5, 50, 10)

if st.button("🚀 Start Vettai"):
    status = st.empty()
    status.info("Starting Cloud Browser... Please wait 1 min...")
    
    # --- CLOUD CHROME SETUP (MUKKIYAM) ---
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    
    try:
        service = Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install())
        driver = webdriver.Chrome(service=service, options=options)
        
        driver.get("https://www.google.com/maps")
        time.sleep(3)
        
        input_box = driver.find_element(By.ID, "searchboxinput")
        input_box.send_keys(search_keyword)
        input_box.send_keys(Keys.RETURN)
        time.sleep(4)
        
        status.warning("⚠️ Scraping in progress... Do not close tab.")
        
        # Simple Scrape
        results = []
        listings = driver.find_elements(By.CLASS_NAME, "hfpxzc")
        for i, listing in enumerate(listings[:target]):
            try:
                name = listing.get_attribute("aria-label")
                link = listing.get_attribute("href")
                if name:
                    results.append({"Name": name, "Link": link})
            except:
                pass
        
        driver.quit()
        
        if results:
            st.success(f"✅ Found {len(results)} Leads!")
            st.dataframe(results)
            csv = pd.DataFrame(results).to_csv(index=False).encode('utf-8')
            st.download_button("Download CSV", csv, "leads.csv", "text/csv")
        else:
            st.error("No leads found. Try again.")
            
    except Exception as e:
        st.error(f"Cloud Error: {e}")