import streamlit as st
import requests
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import uuid
import random
from streamlit_mic_recorder import mic_recorder

# --- 1. USER SESSION & PRIVACY ---
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

# --- 3. CONFIG & LANGUAGES ---
st.set_page_config(page_title="NexusAI Pro", page_icon="🌐", layout="wide")
LANGUAGES = {"Srpski": "Serbian", "English": "English", "Deutsch": "German", "Français": "French", "Español": "Spanish", "Italiano": "Italian", "Русский": "Russian"}
user_ref = db.collection("users").document(st.session_state.user_unique_id) if db else None

# --- 4. SIDEBAR (History, Language & Delete) ---
with st.sidebar:
    st.title("🌐 NexusAI Settings")
    selected_lang = st.selectbox("Interface Language", list(LANGUAGES.keys()))
    
    if st.button("➕ New Chat", use_container_width=True):
        st.session_state.chat_id = str(uuid.uuid4())[:8]
        st.rerun()
    
    st.divider()
    if user_ref:
        st.subheader("Your Chats")
        try:
            history = user_ref.collection("sessions").order_by("start_time", direction=firestore.Query.DESCENDING).limit(15).stream()
            for h in history:
                h_id = h.id
                title = h.to_dict().get("first_msg", "New Chat")[:20]
                col_h1, col_h2 = st.columns([0.8, 0.2])
                with col_h1:
                    if st.button(f"💬 {title}", key=f"btn_{h_id}", use_container_width=True):
                        st.session_state.chat_id = h_id
                        st.rerun()
                with col_h2:
                    if st.button("🗑️", key=f"del_{h_id}"):
                        user_ref.collection("sessions").document(h_id).delete()
                        if st.session_state.chat_id == h_id: st.session_state.chat_id = str(uuid.uuid4())[:8]
                        st.rerun()
        except: pass

# --- 5. MAIN INTERFACE ---
st.title(f"🌐 NexusAI Console")
chat_context = ""

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

st.write("---")

# --- 6. BOTTOM MENU (Attachments, Mic & Input) ---
audio_text = None
with st.container():
    # Raspored: Plus dugme, Mikrofon, Textbox
    col_plus, col_mic, col_txt = st.columns([0.07, 0.07, 0.86])
    
    with col_plus:
        with st.popover("➕"):
            uploaded_file = st.file_uploader("Gallery / Files", type=['png', 'jpg', 'jpeg', 'pdf', 'txt'])
            st.divider()
            use_cam = st.toggle("Enable Camera")
            camera_photo = st.camera_input("Take Photo") if use_cam else None
    
    with col_mic:
        # Mikrofon dugme koje snima glas
        audio_input = mic_recorder(start_prompt="🎤", stop_prompt="🛑", key='mic_input', just_once=True)
        if audio_input:
            audio_text = "Audio message received (Transcription simulation)"

    prompt = st.chat_input("Type your message...")

# --- 7. CHAT LOGIC ---
final_prompt = prompt if prompt else audio_text

if final_prompt or uploaded_file or camera_photo:
    user_display_text = final_prompt if final_prompt else "Attachment sent."
    
    with st.chat_message("user"):
        if final_prompt: st.write(final_prompt)
        if uploaded_file:
            if uploaded_file.type.startswith("image/"): st.image(uploaded_file)
            else: st.info(f"File: {uploaded_file.name}")
        if camera_photo: st.image(camera_photo)

    if user_ref:
        try:
            session_doc = user_ref.collection("sessions").document(st.session_state.chat_id)
            session_doc.set({"first_msg": user_display_text[:30], "start_time": datetime.now()}, merge=True)
            session_doc.collection("messages").add({"role":"user", "text": user_display_text, "timestamp": datetime.now()})
        except: pass

    with st.chat_message("assistant"):
        with st.spinner("Nexus thinking..."):
            img_triggers = ["draw", "image", "slika", "nacrtaj"]
            if final_prompt and any(w in final_prompt.lower() for w in img_triggers):
                ans = f"https://image.pollinations.ai/prompt/{final_prompt.replace(' ', '%20')}?width=1024&height=1024&model=flux&seed={random.randint(0,99999)}"
                st.image(ans)
            else:
                sys_instr = f"Your name is NexusAI. Respond in the user's language. Context:\n{chat_context}"
                try:
                    res = requests.get(f"https://text.pollinations.ai/{sys_instr} User: {final_prompt}?model=openai")
                    ans = res.text
                    st.write(ans)
                except:
                    st.error("Connection error.")
                    ans = "Error."
        
        if user_ref:
            user_ref.collection("sessions").document(st.session_state.chat_id).collection("messages").add({"role":"assistant", "text": ans, "timestamp": datetime.now()})
