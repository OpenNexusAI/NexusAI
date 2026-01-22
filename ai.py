import streamlit as st
import requests
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import uuid
import random

# --- 1. FIREBASE SETUP (FINALNA POPRAVKA ZA KLJUČ) ---
db = None
if not firebase_admin._apps:
    try:
        s = st.secrets["firebase"]
        
        # Uzimamo ključ i nasilno popravljamo nove redove koje Streamlit kvari
        raw_key = s["private_key"]
        clean_key = raw_key.replace("\\n", "\n")
        
        fb_creds = {
            "type": "service_account",
            "project_id": s["project_id"],
            "private_key_id": "eecd76124b0bb41c6c43d72db01c47203a29cc7d",
            "private_key": clean_key,
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
        # Prikazuje grešku samo ako baza ne radi, ali AI će i dalje raditi
        st.error(f"⚠️ Baza nije povezana, ali AI radi. Greška: {e}")

# Osiguravamo db objekat ako je aplikacija već podignuta
if firebase_admin._apps and not db:
    try:
        db = firestore.client()
    except:
        pass

# --- 2. CONFIG I JEZICI ---
st.set_page_config(page_title="NexusAI Global", page_icon="🌐", layout="wide")

LANGUAGES = {
    "Srpski": "Serbian",
    "English": "English",
    "Deutsch": "German",
    "Français": "French",
    "Español": "Spanish",
    "Italiano": "Italian",
    "Русский": "Russian",
    "Português": "Portuguese",
    "தமிழ் (Tamil)": "Tamil",
    "日本語 (Japanese)": "Japanese",
    "العربية (Arabic)": "Arabic"
}

if "chat_id" not in st.session_state:
    st.session_state.chat_id = str(uuid.uuid4())[:8]

# --- 3. SIDEBAR (ISTORIJA I PODEŠAVANJA) ---
with st.sidebar:
    st.title("🌐 NexusAI Settings")
    
    selected_lang = st.selectbox("Izaberi jezik / Select Language", list(LANGUAGES.keys()))
    target_lang = LANGUAGES[selected_lang]
    
    if st.button("➕ New Chat", use_container_width=True):
        st.session_state.chat_id = str(uuid.uuid4())[:8]
        st.rerun()
    
    st.divider()
    st.subheader("Recent Chats")
    if db:
        try:
            history = db.collection("nexus_chats").document("petar").collection("sessions").order_by("start_time", direction=firestore.Query.DESCENDING).limit(10).stream()
            for h in history:
                title = h.to_dict().get("first_msg", "New Chat")[:20]
                if st.button(f"💬 {title}", key=h.id):
                    st.session_state.chat_id = h.id
                    st.rerun()
        except:
            st.write("History unavailable.")

# --- 4. GLAVNI CHAT ---
st.title(f"🌐 NexusAI ({selected_lang})")

if db:
    try:
        messages_ref = db.collection("nexus_chats").document("petar").collection("sessions").document(st.session_state.chat_id).collection("messages").order_by("timestamp")
        for m_doc in messages_ref.stream():
            m = m_doc.to_dict()
            with st.chat_message(m["role"]):
                if "https://image.pollinations.ai" in m["text"]:
                    st.image(m["text"])
                else:
                    st.write(m["text"])
    except:
        pass

prompt = st.chat_input(f"Type in {selected_lang}...")

if prompt:
    with st.chat_message("user"):
        st.write(prompt)

    if db:
        try:
            db.collection("nexus_chats").document("petar").collection("sessions").document(st.session_state.chat_id).set({
                "first_msg": prompt, "start_time": datetime.now()
            }, merge=True)
            db.collection("nexus_chats").document("petar").collection("sessions").document(st.session_state.chat_id).collection("messages").add({
                "role": "user", "text": prompt, "timestamp": datetime.now()
            })
        except:
            pass

    with st.chat_message("assistant"):
        img_triggers = ["draw", "image", "slika", "nacrtaj", "photo", "prikazi"]
        
        if any(word in prompt.lower() for word in img_triggers):
            with st.spinner("🌐 Nexus is drawing..."):
                seed = random.randint(0, 999999)
                clean_p = prompt.lower()
                for w in img_triggers: clean_p = clean_p.replace(w, "")
                img_url = f"https://image.pollinations.ai/prompt/{clean_p.strip().replace(' ', '%20')}?width=1024&height=1024&model=flux&nologo=true&seed={seed}"
                st.image(img_url)
                ans_text = img_url
        else:
            sys_instr = f"Your name is NexusAI. Respond ONLY in {target_lang} language. Never use ASCII art. Be modern and helpful."
            try:
                res = requests.get(f"https://text.pollinations.ai/{sys_instr} {prompt}?model=openai")
                st.write(res.text)
                ans_text = res.text
            except:
                st.error("Nexus Brain offline.")
                ans_text = "Error."

        if db:
            try:
                db.collection("nexus_chats").document("petar").collection("sessions").document(st.session_state.chat_id).collection("messages").add({
                    "role": "assistant", "text": ans_text, "timestamp": datetime.now()
                })
            except:
                pass
