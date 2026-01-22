import streamlit as st
import requests
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import uuid
import random

# --- 1. FIREBASE SETUP ---
db = None
if not firebase_admin._apps:
    try:
        s = st.secrets["firebase"]
        
        # Ključ iz Secrets-a (Literal string sa tri navodnika)
        pk = s["private_key"]
        
        fb_creds = {
            "type": "service_account",
            "project_id": s["project_id"],
            "private_key_id": "eecd76124b0bb41c6c43d72db01c47203a29cc7d",
            "private_key": pk,
            "client_email": s["client_email"],
            "client_id": "110901490489199893217",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{s['client_email'].replace('@', '%40')}"
        }
        
        cred = credentials.Certificate(fb_creds)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
    except Exception as e:
        st.error(f"⚠️ Veza sa bazom nije uspela: {e}")

if firebase_admin._apps and not db:
    try: db = firestore.client()
    except: pass

# --- 2. MULTI-JEZIK PODEŠAVANJA ---
st.set_page_config(page_title="NexusAI World", page_icon="🌐", layout="wide")

LANGUAGES = {
    "Srpski": "Serbian", "English": "English", "Deutsch": "German", 
    "Français": "French", "Español": "Spanish", "Italiano": "Italian", 
    "Русский": "Russian", "தமிழ் (Tamil)": "Tamil", "日本語 (Japanese)": "Japanese"
}

if "chat_id" not in st.session_state:
    st.session_state.chat_id = str(uuid.uuid4())[:8]

# --- 3. SIDEBAR ---
with st.sidebar:
    st.title("🌐 NexusAI Global")
    selected_lang = st.selectbox("Choose Language", list(LANGUAGES.keys()))
    target_lang = LANGUAGES[selected_lang]
    
    if st.button("➕ New chat", use_container_width=True):
        st.session_state.chat_id = str(uuid.uuid4())[:8]
        st.rerun()
    
    st.divider()
    if db:
        st.subheader("Chat History")
        try:
            history = db.collection("nexus_chats").document("petar").collection("sessions").order_by("start_time", direction=firestore.Query.DESCENDING).limit(10).stream()
            for h in history:
                title = h.to_dict().get("first_msg", "New Chat")[:20]
                if st.button(f"💬 {title}", key=h.id):
                    st.session_state.chat_id = h.id
                    st.rerun()
        except: pass

# --- 4. GLAVNI EKRAN ---
st.title(f"🌐 NexusAI ({selected_lang})")

if db:
    try:
        msgs = db.collection("nexus_chats").document("petar").collection("sessions").document(st.session_state.chat_id).collection("messages").order_by("timestamp").stream()
        for m_doc in msgs:
            m = m_doc.to_dict()
            with st.chat_message(m["role"]):
                if "https://" in m["text"]: st.image(m["text"])
                else: st.write(m["text"])
    except: pass

prompt = st.chat_input("Pitaj nešto...")

if prompt:
    st.chat_message("user").write(prompt)
    if db:
        try:
            db.collection("nexus_chats").document("petar").collection("sessions").document(st.session_state.chat_id).set({"first_msg": prompt, "start_time": datetime.now()}, merge=True)
            db.collection("nexus_chats").document("petar").collection("sessions").document(st.session_state.chat_id).collection("messages").add({"role":"user", "text": prompt, "timestamp": datetime.now()})
        except: pass

    with st.chat_message("assistant"):
        if any(w in prompt.lower() for w in ["nacrtaj", "slika", "draw", "image"]):
            seed = random.randint(0, 99999)
            url = f"https://image.pollinations.ai/prompt/{prompt.replace(' ', '%20')}?width=1024&height=1024&model=flux&seed={seed}"
            st.image(url)
            ans = url
        else:
            sys = f"You are NexusAI. Respond only in {target_lang}. No ASCII art."
            res = requests.get(f"https://text.pollinations.ai/{sys} {prompt}?model=openai")
            st.write(res.text)
            ans = res.text
        
        if db:
            try: db.collection("nexus_chats").document("petar").collection("sessions").document(st.session_state.chat_id).collection("messages").add({"role":"assistant", "text": ans, "timestamp": datetime.now()})
            except: pass


