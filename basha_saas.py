import streamlit as st
import time
import pandas as pd
import re
import requests
from datetime import datetime, timedelta, date
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
from bs4 import BeautifulSoup

# --- 🧠 CENTRAL MEMORY (Temporary for now) ---
if "user_db" not in st.session_state:
    st.session_state["user_db"] = {
        "basha": {"password": "king", "role": "owner", "expiry": "2030-01-01", "daily_limit": 10000},
        "client1": {"password": "guest", "role": "client", "expiry": "2025-12-30", "daily_limit": 5}
    }

if "global_leads_db" not in st.session_state:
    st.session_state["global_leads_db"] = set()

if "activity_log" not in st.session_state:
    st.session_state["activity_log"] = []

st.set_page_config(page_title="Basha Master V6", page_icon="🦁", layout="wide")

# --- 🛠️ HELPER FUNCTIONS ---
def extract_email_from_site(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        # Regex for Email
        emails = set(re.findall(r"[a-z0-9\.\-+_]+@[a-z0-9\.\-+_]+\.[a-z]+", soup.text, re.I))
        if emails:
            return list(emails)[0] # Return first email found
    except:
        pass
    return "Not Found"

def make_whatsapp_link(phone):
    if not phone or phone == "No Number": return None
    clean_num = re.sub(r'\D', '', phone) # Remove spaces, + symbols
    if len(clean_num) == 10: clean_num = "91" + clean_num
    return f"https://wa.me/{clean_num}?text=Hi,%20saw%20your%20business%20on%20Google!"

# --- 🔐 LOGIN SYSTEM ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["user"] = None
    st.session_state["role"] = None

def check_login(username, password):
    db = st.session_state["user_db"]
    if username in db and db[username]["password"] == password:
        exp_date = datetime.strptime(db[username]["expiry"], "%Y-%m-%d").date()
        if date.today() > exp_date: return "expired", None
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
        elif status == "expired": st.error("❌ Plan Expired! Contact Admin.")
        else: st.error("❌ Wrong Credentials")
    st.stop()

# --- 🖥️ DASHBOARD & PAYMENT UI ---
current_user = st.session_state["user"]
role = st.session_state["role"]
user_data = st.session_state["user_db"][current_user]

st.sidebar.title(f"👤 {current_user.capitalize()}")
st.sidebar.badge(role.upper())
st.sidebar.write(f"⚡ Limit: {user_data['daily_limit']} / Day")
st.sidebar.write(f"📅 Valid till: {user_data['expiry']}")

# 💳 Payment Gateway (Manual QR)
with st.sidebar.expander("💳 Buy More Credits"):
    st.write("Scan to Pay & WhatsApp screenshot to Admin")
    # Replace with your own QR Code Image URL if needed
    st.image("https://upload.wikimedia.org/wikipedia/commons/d/d0/QR_code_for_mobile_English_Wikipedia.svg", caption="UPI: basha@upi")
    st.info("Plans: ₹500 for 1000 Leads")

if st.sidebar.button("Logout", type="primary"):
    st.session_state["logged_in"] = False
    st.rerun()

# --- 👑 ADMIN PANEL ---
if role == "owner":
    st.title("🛠️ Admin Empire")
    tab1, tab2 = st.tabs(["👥 Manage Users", "📊 Reports"])
    with tab1:
        with st.form("new_user"):
            c1, c2 = st.columns(2)
            nu = c1.text_input("Username")
            np = c2.text_input("Password")
            c3, c4 = st.columns(2)
            nl = c3.number_input("Limit", 50)
            nd = c4.selectbox("Duration", ["1 Month", "1 Year"])
            if st.form_submit_button("Create/Update User"):
                days = 30 if nd == "1 Month" else 365
                exp = (date.today() + timedelta(days=days)).strftime("%Y-%m-%d")
                st.session_state["user_db"][nu] = {"password": np, "role": "client", "expiry": exp, "daily_limit": nl}
                st.success(f"User {nu} updated!")
        
        st.write("### Active Users")
        st.json(st.session_state["user_db"])
    
    with tab2:
        if st.session_state["activity_log"]:
            df = pd.DataFrame(st.session_state["activity_log"])
            st.dataframe(df)
            st.download_button("📥 Download Report", df.to_csv().encode('utf-8'), "report.csv")

# --- 🕵️‍♂️ V6 SCRAPER ENGINE ---
st.header("🦁 Basha Master V6: The Beast")
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
        
        # --- SCROLL & COLLECT LINKS ---
        links_to_visit = set()
        scrolls = 0
        panel = driver.find_element(By.XPATH, '//div[contains(@aria-label, "Results for")]')
        
        while len(links_to_visit) < count and scrolls < 20:
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", panel)
            time.sleep(2)
            elements = driver.find_elements(By.CLASS_NAME, "hfpxzc")
            
            for elem in elements:
                try:
                    # ⭐ Rating Check Logic
                    parent = elem.find_element(By.XPATH, "./..") # Go to parent
                    rating_text = parent.text 
                    # Look for patterns like "4.2" or "3.5"
                    rating_match = re.search(r"(\d\.\d)", rating_text)
                    rating = float(rating_match.group(1)) if rating_match else 0.0
                    
                    link = elem.get_attribute("href")
                    
                    if rating >= min_rating and link not in st.session_state["global_leads_db"]:
                        links_to_visit.add(link)
                except:
                    pass # If rating not found, skip or add depending on logic
            scrolls += 1
            
        status.info(f"✅ Found {len(links_to_visit)} Qualified Targets. Extracting Data...")
        
        # --- VISIT & EXTRACT ---
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
                
                # Duplicate Check
                if phone != "No Number" and phone in st.session_state["global_leads_db"]: continue

                # 📧 Email Extraction (Optional)
                email = "Skipped"
                website = "Not Found"
                if enable_email:
                    try:
                        web_btn = driver.find_elements(By.XPATH, '//a[contains(@data-item-id, "authority")]')
                        if web_btn:
                            website = web_btn[0].get_attribute("href")
                            email = extract_email_from_site(website) # Call Helper Function
                    except: pass
                
                # Save Data
                whatsapp_link = make_whatsapp_link(phone)
                
                collected_data.append({
                    "Name": name, 
                    "Phone": phone,
                    "Rating": "4.0+",
                    "Email": email,
                    "Website": website,
                    "WhatsApp": whatsapp_link
                })
                
                st.session_state["global_leads_db"].add(link)
                if phone != "No Number": st.session_state["global_leads_db"].add(phone)
                
                processed_count = i + 1
                status.success(f"✅ Secured: {name} | 📞 {phone} | 📧 {email}")
                progress_bar.progress(processed_count / len(unique_links))
                
            except Exception as e: continue
            
        if collected_data:
            df = pd.DataFrame(collected_data)
            
            # 📊 DISPLAY WITH WHATSAPP LINK
            st.data_editor(
                df,
                column_config={
                    "WhatsApp": st.column_config.LinkColumn(
                        "Chat", display_text="📲 Open WhatsApp"
                    ),
                    "Website": st.column_config.LinkColumn("Visit Site")
                },
                hide_index=True
            )
            
            # Logs
            st.session_state["activity_log"].append({
                "User": current_user, "Keyword": keyword, "Count": len(collected_data), "Time": datetime.now()
            })
            
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Excel (With Emails)", csv, "basha_v6_leads.csv", "text/csv")
        else:
            st.warning("No matching leads found.")

    except Exception as e: st.error(f"Error: {e}")
    finally: driver.quit()