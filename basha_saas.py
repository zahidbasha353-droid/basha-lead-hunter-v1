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

# --- 🔐 USER DATABASE (Session State) ---
# Default Users (App restart aana idhu mattum than irukum)
DEFAULT_USERS = {
    "basha": {"password": "king", "role": "owner", "expiry": "2030-01-01", "daily_limit": 10000},
    "client1": {"password": "guest", "role": "client", "expiry": "2025-12-30", "daily_limit": 5}
}

if "user_db" not in st.session_state:
    st.session_state["user_db"] = DEFAULT_USERS

st.set_page_config(page_title="Basha Lead Hunter Pro", page_icon="🕵️‍♂️", layout="wide")

# --- LOGIN LOGIC ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["user"] = None
    st.session_state["role"] = None

def check_login(username, password):
    db = st.session_state["user_db"]
    if username in db and db[username]["password"] == password:
        return "success", db[username]["role"]
    return "fail", None

# --- LOGIN SCREEN ---
if not st.session_state["logged_in"]:
    st.markdown("## 🔐 Basha Master Login")
    user_input = st.text_input("Username")
    pass_input = st.text_input("Password", type="password")
    
    if st.button("Login"):
        status, role = check_login(user_input, pass_input)
        if status == "success":
            st.session_state["logged_in"] = True
            st.session_state["user"] = user_input
            st.session_state["role"] = role
            st.rerun()
        else:
            st.error("❌ Wrong ID or Password")
    st.stop()

# --- DASHBOARD SETUP ---
current_user = st.session_state["user"]
current_role = st.session_state["role"]
db = st.session_state["user_db"]
user_limit = db[current_user]["daily_limit"]

# Sidebar
st.sidebar.title(f"👤 {current_user.capitalize()}")
st.sidebar.badge(f"{current_role.upper()}")
if st.sidebar.button("Logout", type="primary"):
    st.session_state["logged_in"] = False
    st.rerun()

# --- 👑 ADMIN PANEL (Only for Owner) ---
if current_role == "owner":
    with st.expander("🛠️ Admin Panel (Create New Users)", expanded=False):
        c1, c2, c3, c4 = st.columns(4)
        new_user = c1.text_input("New Username")
        new_pass = c2.text_input("New Password")
        new_limit = c3.number_input("Daily Limit", value=50)
        add_btn = c4.button("➕ Add User")
        
        if add_btn and new_user and new_pass:
            st.session_state["user_db"][new_user] = {
                "password": new_pass,
                "role": "client",
                "expiry": "2025-12-30", # Default expiry
                "daily_limit": new_limit
            }
            st.success(f"User '{new_user}' created!")
            
        st.write("### Active Users List:")
        st.json(st.session_state["user_db"])

# --- 🕵️‍♂️ MAIN SCRAPING TOOL ---
st.title("🤖 Basha Master: Phone Number Hunter")
st.markdown("---")

col1, col2 = st.columns([2, 1])
search_keyword = col1.text_input("Enter Business Type & City", "Gyms in Chennai")
target = col2.slider("Leads Count", 5, user_limit, 5)

# Stop Button Logic
if "stop_scan" not in st.session_state:
    st.session_state["stop_scan"] = False

def stop_process():
    st.session_state["stop_scan"] = True

start_btn = st.button("🚀 Start Vettai")

if start_btn:
    st.session_state["stop_scan"] = False
    status_box = st.empty()
    data_box = st.empty()
    stop_btn_placeholder = st.empty()
    
    stop_btn_placeholder.button("🛑 STOP SCANNING", on_click=stop_process)

    # Cloud Browser Setup
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")

    status_box.info("🌐 Opening Google Maps... (Wait 30s)")
    
    try:
        service = Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install())
        driver = webdriver.Chrome(service=service, options=options)
        
        driver.get("https://www.google.com/maps")
        time.sleep(4)
        
        # Search
        input_box = driver.find_element(By.ID, "searchboxinput")
        input_box.send_keys(search_keyword)
        input_box.send_keys(Keys.RETURN)
        status_box.warning("🔍 Searching... & Loading Lists...")
        time.sleep(5)
        
        scraped_data = []
        
        # Main Loop
        side_panel = driver.find_element(By.XPATH, '//div[contains(@aria-label, "Results for")]')
        
        count = 0
        while count < target:
            if st.session_state["stop_scan"]:
                status_box.error("🛑 Scanning Stopped by User!")
                break

            # Scroll
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", side_panel)
            time.sleep(2)
            
            listings = driver.find_elements(By.CLASS_NAME, "hfpxzc")
            
            if len(listings) <= count:
                status_box.warning("🔄 Scrolling for more results...")
                continue
                
            # Pick the listing
            current_listing = listings[count]
            
            try:
                # Scroll into view & Click
                driver.execute_script("arguments[0].scrollIntoView();", current_listing)
                current_listing.click()
                time.sleep(3) # Wait for details to load (Crucial for Phone Number)
                
                # Extract Data
                name = current_listing.get_attribute("aria-label")
                link = current_listing.get_attribute("href")
                
                # Try getting phone number (Tricky part)
                phone = "Not Available"
                try:
                    # Searching for button with phone icon logic
                    phone_btns = driver.find_elements(By.XPATH, '//button[contains(@data-item-id, "phone")]')
                    if phone_btns:
                        phone = phone_btns[0].get_attribute("aria-label").replace("Phone: ", "").strip()
                except:
                    pass

                # Add to list
                if name:
                    scraped_data.append({
                        "Name": name, 
                        "Phone": phone,  # Phone number second column
                        "Link": link     # Link last column
                    })
                    count += 1
                    status_box.success(f"✅ Found: {name} | 📞 {phone}")
                    
                    # Live Table Update
                    df = pd.DataFrame(scraped_data)
                    data_box.dataframe(df, use_container_width=True)
            
            except Exception as e:
                # Skip errors
                pass

    except Exception as e:
        status_box.error(f"Error: {e}")
    
    finally:
        driver.quit()
        stop_btn_placeholder.empty() # Hide stop button
        
        if scraped_data:
            status_box.success(f"🎉 Vettai Mudinjathu! Total {len(scraped_data)} Leads.")
            csv = pd.DataFrame(scraped_data).to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Excel (CSV)", csv, "basha_leads.csv", "text/csv")