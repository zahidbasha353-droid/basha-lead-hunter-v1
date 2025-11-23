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

# --- 🧠 CENTRAL MEMORY ---
if "user_db" not in st.session_state:
    st.session_state["user_db"] = {
        "basha": {"password": "king", "role": "owner", "expiry": "2030-01-01", "daily_limit": 10000},
        "client1": {"password": "guest", "role": "client", "expiry": "2025-12-30", "daily_limit": 5}
    }

# Global Duplicate Checker (Link & Phone)
if "global_leads_db" not in st.session_state:
    st.session_state["global_leads_db"] = set()

# Activity Log (For Admin Report)
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
            st.error("Plan Expired!")
        else:
            st.error("Wrong ID/Password")
    st.stop()

# --- 🖥️ DASHBOARD ---
current_user = st.session_state["user"]
current_role = st.session_state["role"]
user_info = st.session_state["user_db"][current_user]
user_limit = user_info["daily_limit"]

st.sidebar.title(f"👤 {current_user.capitalize()}")
st.sidebar.badge(current_role.upper())
if st.sidebar.button("Logout", type="primary"):
    st.session_state["logged_in"] = False
    st.rerun()

# --- 👑 ADMIN PANEL (Users & Reports) ---
if current_role == "owner":
    st.title("🛠️ Admin Control Center")
    tab1, tab2, tab3 = st.tabs(["➕ Add User", "👥 User List", "📊 Download Reports"])
    
    with tab1:
        with st.form("add_user"):
            c1, c2 = st.columns(2)
            nu = c1.text_input("Username")
            np = c2.text_input("Password")
            c3, c4 = st.columns(2)
            nl = c3.number_input("Daily Limit", value=50)
            nd = c4.selectbox("Duration", ["15 Days", "30 Days", "1 Year"])
            if st.form_submit_button("Create User"):
                days = 15 if nd == "15 Days" else 30 if nd == "30 Days" else 365
                exp = (date.today() + timedelta(days=days)).strftime("%Y-%m-%d")
                st.session_state["user_db"][nu] = {"password": np, "role": "client", "expiry": exp, "daily_limit": nl}
                st.success(f"User {nu} Created!")

    with tab2:
        st.subheader("Active Users")
        # Convert DB to DataFrame for nice display
        users_data = []
        for u, data in st.session_state["user_db"].items():
            users_data.append({"Username": u, "Password": data["password"], "Expiry": data["expiry"], "Limit": data["daily_limit"]})
        st.dataframe(pd.DataFrame(users_data), use_container_width=True)

    with tab3:
        st.subheader("📥 Download Activity Report")
        if st.session_state["activity_log"]:
            df_log = pd.DataFrame(st.session_state["activity_log"])
            st.dataframe(df_log, use_container_width=True)
            
            # Download Button for Report
            csv_report = df_log.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Admin Report (Excel/CSV)", csv_report, "basha_admin_report.csv", "text/csv")
        else:
            st.info("No activity yet.")
    
    st.markdown("---")

# --- 🕵️‍♂️ STABLE SCRAPER (Crash Proof) ---
st.header("🤖 Basha Master: Stable Hunter")
c1, c2 = st.columns([2,1])
keyword = c1.text_input("Enter Business & City", "Gyms in Chennai")
count = c2.slider("Leads Needed", 5, user_limit, 5)

if st.button("🚀 Start Vettai (Stable Mode)"):
    status = st.empty()
    status.info("🌐 Starting Cloud Browser...")
    
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    
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
        
        # Step 1: Collect LINKS first (Strings don't crash)
        status.warning("🔄 Scanning List... Please Wait...")
        panel = driver.find_element(By.XPATH, '//div[contains(@aria-label, "Results for")]')
        
        links_to_visit = set()
        scrolls = 0
        while len(links_to_visit) < count and scrolls < 20:
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", panel)
            time.sleep(2)
            elements = driver.find_elements(By.CLASS_NAME, "hfpxzc")
            for elem in elements:
                l = elem.get_attribute("href")
                if l not in st.session_state["global_leads_db"]: # Check duplicate
                    links_to_visit.add(l)
            scrolls += 1
        
        status.info(f"✅ Found {len(links_to_visit)} potential targets. Visiting one by one...")
        
        # Step 2: Visit Links Directly (100% Stable)
        processed_count = 0
        unique_links = list(links_to_visit)[:count]
        
        progress_bar = st.progress(0)
        
        for i, link in enumerate(unique_links):
            try:
                driver.get(link) # Direct Navigation (No Click Error)
                time.sleep(2.5)
                
                # Extract Name
                try:
                    name = driver.find_element(By.XPATH, '//h1[contains(@class, "DUwDvf")]').text
                except:
                    name = "Unknown"
                
                # Extract Phone
                phone = "No Number"
                try:
                    p_btns = driver.find_elements(By.XPATH, '//button[contains(@data-item-id, "phone")]')
                    if p_btns:
                        phone = p_btns[0].get_attribute("aria-label").replace("Phone: ", "").strip()
                except: pass

                # Phone Duplicate Check
                if phone != "No Number" and phone in st.session_state["global_leads_db"]:
                    continue # Skip duplicate numbers
                
                # Save
                collected_data.append({"Name": name, "Phone": phone, "Link": link})
                
                # Mark as taken
                st.session_state["global_leads_db"].add(link)
                if phone != "No Number":
                    st.session_state["global_leads_db"].add(phone)
                
                processed_count += 1
                status.success(f"✅ Secured ({processed_count}/{count}): {name} | {phone}")
                progress_bar.progress((i + 1) / len(unique_links))
                
            except Exception as e:
                continue # Skip bad links
        
        # --- SAVE & LOG ---
        if collected_data:
            # Log Activity for Admin
            st.session_state["activity_log"].append({
                "User": current_user,
                "Date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "Keyword": keyword,
                "Leads_Count": len(collected_data)
            })
            
            st.success(f"🎉 Mission Success! {len(collected_data)} Leads Collected.")
            
            # Download Button for User
            csv = pd.DataFrame(collected_data).to_csv(index=False).encode('utf-8')
            st.download_button(f"📥 Download {keyword} Leads", csv, "leads.csv", "text/csv")
        else:
            st.warning("No new leads found (All might be duplicates).")

    except Exception as e:
        st.error(f"Critical Error: {e}")
    finally:
        driver.quit()