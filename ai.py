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

# --- 3. CONFIG & ALL GLOBAL LANGUAGES ---
st.set_page_config(page_title="NexusAI Universal", page_icon="🌐", layout="wide")

GLOBAL_LANGUAGES = {
    "Srpski 🇷🇸": "Serbian", "English 🇺🇸": "English", "Deutsch 🇩🇪": "German",
    "Français 🇫🇷": "French", "Español 🇪🇸": "Spanish", "Italiano 🇮🇹": "Italian",
    "Русский 🇷🇺": "Russian", "中文 🇨🇳": "Chinese", "日本語 🇯🇵": "Japanese",
    "العربية 🇸🇦": "Arabic", "हिन्दी 🇮🇳": "Hindi", "Português 🇵🇹": "Portuguese",
    "Türkçe 🇹🇷": "Turkish", "한국어 🇰🇷": "Korean", "Hrvatski 🇭🇷": "Croatian",
    "Bosanski 🇧🇦": "Bosnian", "Slovenščina 🇸🇮": "Slovenian", "Makedonski 🇲🇰": "Macedonian"
}

user_ref = db.collection("users").document(st.session_state.user_unique_id) if db else None

# --- 4. SIDEBAR (History with Delete & Fix) ---
with st.sidebar:
    st.title("🌐 NexusAI Assistant")
    
    selected_ui_name = st.selectbox("Select Language / Izaberi jezik", list(GLOBAL_LANGUAGES.keys()))
    target_lang = GLOBAL_LANGUAGES[selected_ui_name]
    
    if st.button("➕ New Chat", use_container_width=True):
        st.session_state.chat_id = str(uuid.uuid4())[:8]
        st.rerun()
    
    st.divider()
    if user_ref:
        st.subheader("Your Chats")
        try:
            # Prikazujemo samo sesije koje imaju start_time (stvarne četove)
            history = user_ref.collection("sessions").order_by("start_time", direction=firestore.Query.DESCENDING).limit(20).stream()
            for h in history:
                h_id = h.id
                h_data = h.to_dict()
                # Ako čet nema poruka, ne prikazuj ga
                if "first_msg" not in h_data: continue
                
                title = h_data.get("first_msg", "New Chat")[:20]
                col_h1, col_h2 = st.columns([0.8, 0.2])
                with col_h1:
                    if st.button(f"💬 {title}", key=f"btn_{h_id}", use_container_width=True):
                        st.session_state.chat_id = h_id
                        st.rerun()
                with col_h2:
                    if st.button("🗑️", key=f"del_{h_id}"):
                        user_ref.collection("sessions").document(h_id).delete()
                        if st.session_state.chat_id == h_id:
                            st.session_state.chat_id = str(uuid.uuid4())[:8]
                        st.rerun()
        except: pass

# --- 5. MAIN INTERFACE ---
st.title(f"🌐 NexusAI Assistant")
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
    col_plus, col_mic, col_txt = st.columns([0.07, 0.07, 0.86])
    
    with col_plus:
        with st.popover("➕"):
            uploaded_file = st.file_uploader("Upload / Gallery", type=['png', 'jpg', 'jpeg', 'pdf', 'txt'])
            st.divider()
            use_cam = st.toggle("Enable Camera")
            camera_photo = st.camera_input("Take Photo") if use_cam else None
    
    with col_mic:
        audio_input = mic_recorder(start_prompt="🎤", stop_prompt="🛑", key='mic_input', just_once=True)
        if audio_input:
            audio_text = "Sent a voice message."

    prompt = st.chat_input(f"Type in {target_lang}...")

# --- 7. CHAT LOGIC (Optimized Saving) ---
final_prompt = prompt if prompt else audio_text

if final_prompt or uploaded_file or camera_photo:
    user_msg_text = final_prompt if final_prompt else "Attachment sent."
    
    with st.chat_message("user"):
        if final_prompt: st.write(final_prompt)
        if uploaded_file:
            if uploaded_file.type.startswith("image/"): st.image(uploaded_file)
            else: st.info(f"File: {uploaded_file.name}")
        if camera_photo: st.image(camera_photo)

    if user_ref:
        try:
            session_doc = user_ref.collection("sessions").document(st.session_state.chat_id)
            # PROVERA: Naslov u sidebar-u (first_msg) upisujemo SAMO AKO dokument još ne postoji
            doc_snap = session_doc.get()
            if not doc_snap.exists:
                session_doc.set({
                    "first_msg": user_msg_text[:25], 
                    "start_time": datetime.now()
                })
            
            # Poruku uvek dodajemo u pod-kolekciju
            session_doc.collection("messages").add({
                "role": "user", 
                "text": user_msg_text, 
                "timestamp": datetime.now()
            })
        except: pass

    with st.chat_message("assistant"):
        with st.spinner("Processing..."):
            img_triggers = ["draw", "image", "slika", "nacrtaj"]
            if final_prompt and any(w in final_prompt.lower() for w in img_triggers):
                ans = f"https://image.pollinations.ai/prompt/{final_prompt.replace(' ', '%20')}?width=1024&height=1024&model=flux&seed={random.randint(0,99999)}"
                st.image(ans)
            else:
                sys_instr = f"Your name is NexusAI. The user preferred language is {target_lang}. Always respond in the language the user uses. Context:\n{chat_context}"
                try:
                    res = requests.get(f"https://text.pollinations.ai/{sys_instr} User: {final_prompt}?model=openai")
                    ans = res.text
                    st.write(ans)
                except:
                    st.error("Error."); ans = "Error."
        
        if user_ref:
            try:
                user_ref.collection("sessions").document(st.session_state.chat_id).collection("messages").add({
                    "role": "assistant", 
                    "text": ans, 
                    "timestamp": datetime.now()
                })
            except: pass


