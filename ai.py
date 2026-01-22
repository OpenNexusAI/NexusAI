import streamlit as st
import requests
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import uuid
import random

# --- 1. FIREBASE SETUP (BEZ FAJLA - ČITA IZ SECRETS) ---
if not firebase_admin._apps:
    try:
        # Uzimamo podatke iz tvog Secrets-a
        s = st.secrets["firebase"]
        
        # Pravimo rečnik koji Firebase prihvata
        fb_credentials = {
            "type": "service_account",
            "project_id": s["project_id"],
            "private_key_id": "eecd76124b0bb41c6c43d72db01c47203a29cc7d",
            "private_key": s["private_key"],
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
        st.error(f"NexusAI Connection Error: {e}")

# Inicijalizacija baze (ako je sve OK sa gornjim delom, ovo neće baciti error)
try:
    db = firestore.client()
except:
    st.error("Baza nije dostupna. Proveri Secrets!")

# --- 2. CONFIG I UI ---
st.set_page_config(page_title="NexusAI", page_icon="🌐", layout="wide")

if "chat_id" not in st.session_state:
    st.session_state.chat_id = str(uuid.uuid4())[:8]

# --- 3. SIDEBAR (ISTORIJA IZ BAZE) ---
with st.sidebar:
    st.title("🌐 NexusAI")
    if st.button("➕ New Chat", use_container_width=True):
        st.session_state.chat_id = str(uuid.uuid4())[:8]
        st.rerun()
    
    st.divider()
    st.subheader("Recent Nexus Chats")
    try:
        # Koristimo fixnog usera 'petar' za internet verziju
        history = db.collection("nexus_chats").document("petar").collection("sessions").order_by("start_time", direction=firestore.Query.DESCENDING).limit(10).stream()
        for h in history:
            title = h.to_dict().get("first_msg", "New Chat")[:20]
            if st.button(f"💬 {title}", key=h.id):
                st.session_state.chat_id = h.id
                st.rerun()
    except:
        st.write("No history found.")

# --- 4. PRIKAZ PORUKA ---
st.title("🌐 NexusAI Assistant")

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
    st.info("Start a new conversation!")

# --- 5. KOMANDE I LOGIKA ---
prompt = st.chat_input("Command NexusAI...")

if prompt:
    with st.chat_message("user"):
        st.write(prompt)

    # Čuvanje u bazu
    db.collection("nexus_chats").document("petar").collection("sessions").document(st.session_state.chat_id).set({
        "first_msg": prompt, "start_time": datetime.now()
    }, merge=True)
    
    db.collection("nexus_chats").document("petar").collection("sessions").document(st.session_state.chat_id).collection("messages").add({
        "role": "user", "text": prompt, "timestamp": datetime.now()
    })

    # Provera za slike
    img_triggers = ["draw", "image", "slika", "nacrtaj", "photo", "picture"]
    if any(word in prompt.lower() for word in img_triggers):
        with st.chat_message("assistant"):
            with st.spinner("🌐 Nexus is drawing..."):
                seed = random.randint(0, 999999)
                clean_p = prompt.lower()
                for w in img_triggers: clean_p = clean_p.replace(w, "")
                img_url = f"https://image.pollinations.ai/prompt/{clean_p.strip().replace(' ', '%20')}?width=1024&height=1024&model=flux&nologo=true&seed={seed}"
                st.image(img_url)
                db.collection("nexus_chats").document("petar").collection("sessions").document(st.session_state.chat_id).collection("messages").add({
                    "role": "assistant", "text": img_url, "timestamp": datetime.now()
                })
    else:
        with st.chat_message("assistant"):
            try:
                # Instrukcija da ne crta ASCII i da bude NexusAI
                sys_p = "Your name is NexusAI. Talk naturally, no formal 'Vi'. Direct and cool. NEVER use ASCII art. English only. "
                res = requests.get(f"https://text.pollinations.ai/{sys_p}{prompt}?model=openai")
                st.write(res.text)
                db.collection("nexus_chats").document("petar").collection("sessions").document(st.session_state.chat_id).collection("messages").add({
                    "role": "assistant", "text": res.text, "timestamp": datetime.now()
                })
            except:
                st.error("Nexus Brain offline.")
