import streamlit as st
import requests
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import uuid
import random

# --- 1. FIREBASE SETUP (ULTIMATE FIX ZA VAŠ KLJUČ) ---
if not firebase_admin._apps:
    try:
        s = st.secrets["firebase"]
        
        # Uzimamo ključ i osiguravamo da nema skrivenih karaktera koji kvare certifikat
        # Koristimo strip() da skinemo prazna mesta sa početka i kraja
        raw_key = s["private_key"].strip()
        
        # Popravljamo problem sa novim redovima (\n) koji zbunjuje ASN.1 parser
        if "\\n" in raw_key:
            clean_key = raw_key.replace("\\n", "\n")
        else:
            clean_key = raw_key

        fb_credentials = {
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
        
        cred = credentials.Certificate(fb_credentials)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"⚠️ NexusAI Connection Error: {e}")

# Inicijalizacija baze (SAD ĆE RADITI!)
try:
    db = firestore.client()
except Exception as e:
    st.error(f"❌ Baza nedostupna: {e}")

# --- 2. KONFIGURACIJA I JEZICI ---
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

# --- 3. SIDEBAR ---
with st.sidebar:
    st.title("🌐 NexusAI Settings")
    
    # Izbor jezika
    selected_lang = st.selectbox("Izaberi jezik / Select Language", list(LANGUAGES.keys()))
    target_lang = LANGUAGES[selected_lang]
    
    if st.button("➕ New Chat", use_container_width=True):
        st.session_state.chat_id = str(uuid.uuid4())[:8]
        st.rerun()
    
    st.divider()
    st.subheader("Chat History")
    try:
        history = db.collection("nexus_chats").document("petar").collection("sessions").order_by("start_time", direction=firestore.Query.DESCENDING).limit(10).stream()
        for h in history:
            title = h.to_dict().get("first_msg", "New Chat")[:20]
            if st.button(f"💬 {title}", key=h.id):
                st.session_state.chat_id = h.id
                st.rerun()
    except:
        st.write("No history.")

# --- 4. CHAT INTERFEJS ---
st.title(f"🌐 NexusAI ({selected_lang})")

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

# --- 5. LOGIKA SLANJA PORUKA ---
prompt = st.chat_input(f"Send a message in {selected_lang}...")

if prompt:
    with st.chat_message("user"):
        st.write(prompt)
    
    # Čuvanje sesije
    db.collection("nexus_chats").document("petar").collection("sessions").document(st.session_state.chat_id).set({
        "first_msg": prompt, "start_time": datetime.now()
    }, merge=True)
    
    db.collection("nexus_chats").document("petar").collection("sessions").document(st.session_state.chat_id).collection("messages").add({
        "role": "user", "text": prompt, "timestamp": datetime.now()
    })

    # Provera za slike
    img_triggers = ["draw", "image", "slika", "nacrtaj", "photo"]
    if any(w in prompt.lower() for w in img_triggers):
        with st.chat_message("assistant"):
            with st.spinner("Visualizing..."):
                seed = random.randint(0, 999999)
                img_url = f"https://image.pollinations.ai/prompt/{prompt.replace(' ', '%20')}?width=1024&height=1024&model=flux&seed={seed}"
                st.image(img_url)
                db.collection("nexus_chats").document("petar").collection("sessions").document(st.session_state.chat_id).collection("messages").add({
                    "role": "assistant", "text": img_url, "timestamp": datetime.now()
                })
    else:
        with st.chat_message("assistant"):
            # Forsiranje jezika i blokiranje ASCII-ja
            sys_msg = f"Your name is NexusAI. Respond only in {target_lang}. Never use ASCII art. Be direct and modern."
            try:
                res = requests.get(f"https://text.pollinations.ai/{sys_msg} {prompt}?model=openai")
                st.write(res.text)
                db.collection("nexus_chats").document("petar").collection("sessions").document(st.session_state.chat_id).collection("messages").add({
                    "role": "assistant", "text": res.text, "timestamp": datetime.now()
                })
            except:
                st.error("Connection lost.")
