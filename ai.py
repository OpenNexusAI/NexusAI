import streamlit as st
import requests
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import uuid
import random

# --- 1. USER SESSION & PRIVACY FIX ---
# Generišemo ID korisnika koji je jedinstven za njegov browser
if "user_unique_id" not in st.session_state:
    st.session_state.user_unique_id = str(uuid.uuid4())[:12]

if "chat_id" not in st.session_state:
    st.session_state.chat_id = str(uuid.uuid4())[:8]

# --- 2. FIREBASE SETUP ---
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

# --- 3. CONFIG ---
st.set_page_config(page_title="NexusAI Pro", page_icon="🌐", layout="wide")

# Putanja u bazi: users -> [jedinstveni_id] -> sessions -> [chat_id]
user_ref = db.collection("users").document(st.session_state.user_unique_id) if db else None

# --- 4. SIDEBAR (History restricted to current user) ---
with st.sidebar:
    st.title("🌐 NexusAI Navigation")
    st.caption(f"Your ID: {st.session_state.user_unique_id}") # Da vidiš da je tvoj ID unikatan
    
    if st.button("➕ New Chat", use_container_width=True):
        st.session_state.chat_id = str(uuid.uuid4())[:8]
        st.rerun()
    
    st.divider()
    if user_ref:
        st.subheader("Your Chat History")
        try:
            history = user_ref.collection("sessions").order_by("start_time", direction=firestore.Query.DESCENDING).limit(10).stream()
            for h in history:
                title = h.to_dict().get("first_msg", "New Chat")[:20]
                if st.button(f"💬 {title}", key=h.id):
                    st.session_state.chat_id = h.id
                    st.rerun()
        except: pass

# --- 5. MAIN INTERFACE ---
st.title("🌐 NexusAI Console")
chat_context = ""

# Prikaz samo tvojih poruka
if user_ref:
    try:
        msgs_ref = user_ref.collection("sessions").document(st.session_state.chat_id).collection("messages").order_by("timestamp")
        all_msgs = list(msgs_ref.stream())
        for i, m_doc in enumerate(all_msgs):
            m = m_doc.to_dict()
            with st.chat_message(m["role"]):
                if "https://" in m["text"] and "pollinations" in m["text"]: st.image(m["text"])
                else: st.write(m["text"])
            if i > len(all_msgs) - 7:
                chat_context += f"{m['role']}: {m['text']}\n"
    except: pass

# --- 6. ATTACHMENT MENU ---
col1, col2 = st.columns([0.07, 0.93])
with col1:
    with st.popover("➕"):
        st.write("### Attachments")
        uploaded_file = st.file_uploader("Upload Image/File", type=['png', 'jpg', 'jpeg', 'pdf', 'txt'])
        camera_photo = st.camera_input("Use Camera")

prompt = st.chat_input("Message NexusAI...")

# --- 7. CHAT LOGIC ---
if prompt or uploaded_file or camera_photo:
    user_display_text = prompt if prompt else "Sent an attachment."
    
    with st.chat_message("user"):
        if prompt: st.write(prompt)
        if uploaded_file:
            st.info(f"Attached: {uploaded_file.name}")
            if uploaded_file.type.startswith("image/"): st.image(uploaded_file)
        if camera_photo: st.image(camera_photo)

    # Save to User-Specific collection
    if user_ref:
        try:
            session_doc = user_ref.collection("sessions").document(st.session_state.chat_id)
            session_doc.set({"first_msg": user_display_text, "start_time": datetime.now()}, merge=True)
            session_doc.collection("messages").add({"role":"user", "text": user_display_text, "timestamp": datetime.now()})
        except: pass

    # Assistant Response
    with st.chat_message("assistant"):
        with st.spinner("Nexus thinking..."):
            img_triggers = ["draw", "image", "slika", "nacrtaj"]
            if prompt and any(w in prompt.lower() for w in img_triggers):
                seed = random.randint(0, 99999)
                ans = f"https://image.pollinations.ai/prompt/{prompt.replace(' ', '%20')}?width=1024&height=1024&model=flux&seed={seed}"
                st.image(ans)
            else:
                sys_instr = f"Your name is NexusAI. Respond only in English. Context:\n{chat_context}"
                final_input = f"{prompt} (User sent attachment)" if (uploaded_file or camera_photo) else prompt
                try:
                    res = requests.get(f"https://text.pollinations.ai/{sys_instr} User: {final_input}?model=openai")
                    ans = res.text
                    st.write(ans)
                except:
                    st.error("Nexus offline.")
                    ans = "Connection error."
        
        if user_ref:
            try:
                user_ref.collection("sessions").document(st.session_state.chat_id).collection("messages").add({"role":"assistant", "text": ans, "timestamp": datetime.now()})
            except: pass
