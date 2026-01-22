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
        pk = s["private_key"].replace("\\n", "\n")
        fb_creds = {
            "type": "service_account", "project_id": s["project_id"],
            "private_key_id": "eecd76124b0bb41c6c43d72db01c47203a29cc7d",
            "private_key": pk, "client_email": s["client_email"],
            "client_id": "110901490489199893217", "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{s['client_email'].replace('@', '%40')}"
        }
        cred = credentials.Certificate(fb_creds)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
    except: pass

if firebase_admin._apps and not db:
    try: db = firestore.client()
    except: pass

# --- 2. CONFIG ---
st.set_page_config(page_title="NexusAI Pro", page_icon="🌐", layout="wide")

if "chat_id" not in st.session_state:
    st.session_state.chat_id = str(uuid.uuid4())[:8]

# --- 3. SIDEBAR (English UI) ---
with st.sidebar:
    st.title("🌐 NexusAI Navigation")
    if st.button("➕ New Chat", use_container_width=True):
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

# --- 4. MAIN INTERFACE ---
st.title("🌐 NexusAI Console")

chat_context = "" # Ovde gradimo memoriju

# Prikaz poruka i skupljanje konteksta
if db:
    try:
        msgs_ref = db.collection("nexus_chats").document("petar").collection("sessions").document(st.session_state.chat_id).collection("messages").order_by("timestamp")
        all_msgs = list(msgs_ref.stream())
        
        for i, m_doc in enumerate(all_msgs):
            m = m_doc.to_dict()
            with st.chat_message(m["role"]):
                if "https://" in m["text"] and "pollinations" in m["text"]: st.image(m["text"])
                else: st.write(m["text"])
            
            # Dodajemo u memoriju poslednjih 6 poruka
            if i > len(all_msgs) - 7:
                chat_context += f"{m['role']}: {m['text']}\n"
    except: pass

# --- 5. ATTACHMENT MENU & INPUT ---
col1, col2 = st.columns([0.07, 0.93])

with col1:
    with st.popover("➕"):
        st.write("### Attachments")
        uploaded_file = st.file_uploader("Upload Image/File", type=['png', 'jpg', 'jpeg', 'pdf', 'txt'])
        camera_photo = st.camera_input("Use Camera")

prompt = st.chat_input("Message NexusAI...")

# --- 6. CHAT LOGIC ---
if prompt or uploaded_file or camera_photo:
    user_display_text = prompt if prompt else "Sent an attachment."
    
    with st.chat_message("user"):
        if prompt: st.write(prompt)
        if uploaded_file:
            st.info(f"Attached: {uploaded_file.name}")
            if uploaded_file.type.startswith("image/"): st.image(uploaded_file)
        if camera_photo:
            st.image(camera_photo)

    # Save User Msg to DB
    if db:
        try:
            db.collection("nexus_chats").document("petar").collection("sessions").document(st.session_state.chat_id).set({"first_msg": user_display_text, "start_time": datetime.now()}, merge=True)
            db.collection("nexus_chats").document("petar").collection("sessions").document(st.session_state.chat_id).collection("messages").add({"role":"user", "text": user_display_text, "timestamp": datetime.now()})
        except: pass

    # AI Response
    with st.chat_message("assistant"):
        with st.spinner("Nexus thinking..."):
            # Provera za crtanje slika
            img_triggers = ["draw", "image", "slika", "nacrtaj"]
            if prompt and any(w in prompt.lower() for w in img_triggers):
                seed = random.randint(0, 99999)
                ans = f"https://image.pollinations.ai/prompt/{prompt.replace(' ', '%20')}?width=1024&height=1024&model=flux&seed={seed}"
                st.image(ans)
            else:
                # Običan tekstualni odgovor sa MEMORIJOM
                sys_instr = f"Your name is NexusAI. Respond only in English. Stay focused on the topic but flexible. Context of previous messages:\n{chat_context}"
                final_input = f"{prompt} (User sent attachment)" if (uploaded_file or camera_photo) else prompt
                
                try:
                    res = requests.get(f"https://text.pollinations.ai/{sys_instr} User: {final_input}?model=openai")
                    ans = res.text
                    st.write(ans)
                except:
                    st.error("Nexus offline.")
                    ans = "Connection error."
        
        # Save Assistant Msg to DB
        if db:
            try:
                db.collection("nexus_chats").document("petar").collection("sessions").document(st.session_state.chat_id).collection("messages").add({"role":"assistant", "text": ans, "timestamp": datetime.now()})
            except: pass
