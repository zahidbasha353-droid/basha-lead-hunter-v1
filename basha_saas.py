import streamlit as st
import time
import pandas as pd
from datetime import datetime, timedelta, date
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
from selenium.common.exceptions import StaleElementReferenceException, NoSuchElementException

# --- 🧠 CENTRAL MEMORY (Simulated Database) ---
if "user_db" not in st.session_state:
    st.session_state["user_db"] = {
        "basha": {"password": "king", "role": "owner", "expiry": "2030-01-01", "daily_limit": 10000},
        "client1": {"password": "guest", "role": "client", "expiry": "2025-12-30", "daily_limit": 5}
    }

if "global_leads_db" not in st.session_state:
    st.session_state["global_leads_db"] = set()

if "activity_log" not in st.session_state:
    st.session_state["activity_log"] = []

st.set_page_config(page_title="Basha Lead Hunter Pro", page_icon="📊", layout="wide")

# --- 🔐 LOGIN SYSTEM ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["user"] = None
    st.session_state["role"] = None

def check_login(username, password):
    db = st.session_state["user_db"]
    if username in db and db[username]["password"] == password:
        exp_date = datetime.strptime(db[username]["expiry"], "%Y-%m-%d").date()
        if date.today() > exp_date:
            return "expired", None
        return "success", db[username]["role"]
    return "fail", None

if not st.session_state["logged_in"]:
    st.markdown("## 🔐 Basha Master Login")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    if st.button("Login"):
        status, role = check_login(u, p)
        if status == "success":
            st.session_state["logged_in"] = True
            st.session_state["user"] = u
            st.session_state["role"] = role
            st.rerun()
        elif status == "expired":
            st.error("❌ Your Plan Expired! Pay Basha Bhai to renew.")
        else:
            st.error("❌ Wrong ID/Password")
    st.stop()

# --- 🖥️ DASHBOARD ---
current_user = st.session_state["user"]
current_role = st.session_state["role"]
user_limit = st.session_state["user_db"][current_user]["daily_limit"]

st.sidebar.title(f"👤 {current_user.capitalize()}")
st.sidebar.badge(current_role.upper())
if st.sidebar.button("Logout", type="primary"):
    st.session_state["logged_in"] = False
    st.rerun()

# --- 👑 ADMIN PANEL ---
if current_role == "owner":
    st.title("🛠️ Admin Control Center")
    tab1, tab2 = st.tabs(["➕ Add User", "📊 Analytics & Logs"])
    
    with tab1:
        with st.form("add_user_form"):
            c1, c2 = st.columns(2)
            new_user = c1.text_input("New Username")
            new_pass = c2.text_input("New Password")
            c3, c4 = st.columns(2)
            limit = c3.number_input("Daily Lead Limit", value=50)
            duration = c4.selectbox("Plan Duration", ["15 Days", "30 Days", "3 Months", "1 Year"])
            
            if st.form_submit_button("Create User"):
                days = 15
                if duration == "30 Days": days = 30
                elif duration == "3 Months": days = 90
                elif duration == "1 Year": days = 365
                expiry_date = (date.today() + timedelta(days=days)).strftime("%Y-%m-%d")
                
                st.session_state["user_db"][new_user] = {
                    "password": new_pass, "role": "client", "expiry": expiry_date, "daily_limit": limit
                }
                st.success(f"✅ User '{new_user}' Created! Valid till {expiry_date}")

    with tab2:
        st.subheader("📈 Search Trends")
        if st.session_state["activity_log"]:
            df_log = pd.DataFrame(st.session_state["activity_log"])
            st.bar_chart(df_log["keyword"].value_counts())
            st.dataframe(df_log, use_container_width=True)
        else:
            st.info("No activity yet.")
        st.write(f"🔥 **Total Unique Leads:** {len(st.session_state['global_leads_db'])}")
    st.markdown("---")

# --- 🕵️‍♂️ SCRAPING LOGIC (Fixed for Errors) ---
st.header("🤖 Basha Master: Smart Hunter (No Duplicates)")
c1, c2 = st.columns([2,1])
keyword = c1.text_input("Enter Business & City", "Gyms in Chennai")
count = c2.slider("Leads Needed", 5, user_limit, 5)

if st.button("🚀 Start Vettai"):
    st.info("🌐 Starting Cloud Browser...")
    
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()),
        options=options
    )
    
    try:
        driver.get("https://www.google.com/maps")
        time.sleep(3)
        driver.find_element(By.ID, "searchboxinput").send_keys(keyword + Keys.RETURN)
        time.sleep(5)
        
        status = st.empty()
        collected_data = []
        new_leads_count = 0
        
        # Locate the scrollable panel
        try:
            panel = driver.find_element(By.XPATH, '//div[contains(@aria-label, "Results for")]')
        except:
            status.error("❌ Could not find results. Check internet or keyword.")
            driver.quit()
            st.stop()
        
        scroll_attempts = 0
        
        while new_leads_count < count and scroll_attempts < 30:
            # Scroll Down
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", panel)
            time.sleep(2)
            
            # Re-fetch elements every loop to avoid "Stale Element" error
            listings = driver.find_elements(By.CLASS_NAME, "hfpxzc")
            
            for listing in listings:
                if new_leads_count >= count: break
                
                try:
                    # --- SAFE EXTRACTION START ---
                    link = listing.get_attribute("href")
                    
                    # Global Duplicate Check
                    if link in st.session_state["global_leads_db"]:
                        continue 

                    # Scroll to element to make it clickable
                    driver.execute_script("arguments[0].scrollIntoView();", listing)
                    listing.click()
                    time.sleep(2) # Give time for side panel to load
                    
                    # Re-fetch name from side panel (More stable)
                    try:
                        name_elem = driver.find_element(By.XPATH, '//h1[contains(@class, "DUwDvf")]')
                        name = name_elem.text
                    except:
                        name = listing.get_attribute("aria-label")

                    # Get Phone Number
                    phone = "No Number"
                    try:
                        p_btns = driver.find_elements(By.XPATH, '//button[contains(@data-item-id, "phone")]')
                        if p_btns:
                            phone = p_btns[0].get_attribute("aria-label").replace("Phone: ", "").strip()
                    except: pass
                    
                    # Phone Duplicate Check
                    if phone != "No Number" and phone in st.session_state["global_leads_db"]:
                        status.warning(f"⚠️ Taken: {name} - Skipping...")
                        continue
                    
                    # Save Data
                    if name:
                        collected_data.append({"Name": name, "Phone": phone, "Link": link})
                        
                        st.session_state["global_leads_db"].add(link)
                        if phone != "No Number":
                            st.session_state["global_leads_db"].add(phone)
                            
                        new_leads_count += 1
                        status.success(f"✅ Secured: {name} | 📞 {phone}")
                    
                    # --- SAFE EXTRACTION END ---

                except StaleElementReferenceException:
                    # If element changes, just skip and continue to next
                    continue
                except Exception as e:
                    # Ignore other minor errors
                    continue
            
            scroll_attempts += 1
            
        # Finish
        if collected_data:
            log_entry = {
                "User": current_user,
                "Date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "Keyword": keyword,
                "Leads Extracted": len(collected_data)
            }
            st.session_state["activity_log"].append(log_entry)
            
            st.success(f"🎉 Success! {len(collected_data)} Unique Leads Found.")
            csv = pd.DataFrame(collected_data).to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download CSV", csv, "basha_leads.csv", "text/csv")
        else:
            st.error("❌ No New Unique Leads found! (Or Check Connection)")

    except Exception as e:
        st.error(f"System Error: {e}")
    finally:
        driver.quit()