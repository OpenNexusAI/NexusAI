import streamlit as st
import requests
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import uuid
import random

# --- 1. FIREBASE SETUP (ULTIMATE SURVIVAL VERSION) ---
if not firebase_admin._apps:
    try:
        s = st.secrets["firebase"]
        
        # Čišćenje ključa od duplih kosa crta i razmaka
        # Ovo rešava "ASN.1 parsing error" jednom zauvek
        raw_key = s["private_key"].replace("\\\\n", "\n").replace("\\n", "\n").strip()
        
        fb_creds = {
            "type": "service_account",
            "project_id": s["project_id"],
            "private_key_id": "eecd76124b0bb41c6c43d72db01c47203a29cc7d",
            "private_key": raw_key,
            "client_email": s["client_email"],
            "client_id": "110901490489199893217",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{s['client_email'].replace('@', '%40')}"
        }
        
        cred = credentials.Certificate(fb_creds)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"⚠️ Connection Error: {e}")

# Inicijalizacija baze (bez pucanja aplikacije)
db = None
try:
    db = firestore.client()
except:
    pass

# --- 2. CONFIG I JEZICI ---
st.set_page_config(page_title="NexusAI Global", page_icon="🌐", layout="wide")

LANGUAGES = {
    "Srpski": "Serbian", "English": "English", "Deutsch": "German", 
    "Français": "French", "Español": "Spanish", "தமிழ் (Tamil)": "Tamil"
}

if "chat_id" not in st.session_state:
    st.session_state.chat_id = str(uuid.uuid4())[:8]

# --- 3. SIDEBAR ---
with st.sidebar:
    st.title("🌐 Settings")
    selected_lang = st.selectbox("Language", list(LANGUAGES.keys()))
    target_lang = LANGUAGES[selected_lang]
    if st.button("➕ New Chat"):
        st.session_state.chat_id = str(uuid.uuid4())[:8]
        st.rerun()

# --- 4. CHAT INTERFEJS ---
st.title(f"🌐 NexusAI ({selected_lang})")

if db:
    try:
        msgs = db.collection("nexus_chats").document("petar").collection("sessions").document(st.session_state.chat_id).collection("messages").order_by("timestamp").stream()
        for m_doc in msgs:
            m = m_doc.to_dict()
            with st.chat_message(m["role"]):
                st.write(m["text"])
    except: pass

prompt = st.chat_input("Command...")
if prompt:
    st.chat_message("user").write(prompt)
    
    if db:
        try:
            db.collection("nexus_chats").document("petar").collection("sessions").document(st.session_state.chat_id).set({"first_msg": prompt, "start_time": datetime.now()}, merge=True)
            db.collection("nexus_chats").document("petar").collection("sessions").document(st.session_state.chat_id).collection("messages").add({"role":"user", "text": prompt, "timestamp": datetime.now()})
        except: pass

    with st.chat_message("assistant"):
        # AI uvek radi, čak i ako baza padne
        sys_msg = f"Your name is NexusAI. Respond only in {target_lang}. No ASCII art."
        try:
            res = requests.get(f"https://text.pollinations.ai/{sys_msg} {prompt}?model=openai")
            st.write(res.text)
            if db:
                db.collection("nexus_chats").document("petar").collection("sessions").document(st.session_state.chat_id).collection("messages").add({"role":"assistant", "text": res.text, "timestamp": datetime.now()})
        except:
            st.error("Offline.")
