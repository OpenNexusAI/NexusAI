import streamlit as st
import requests
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import uuid
import random

# --- 1. FIREBASE SETUP ---
if not firebase_admin._apps:
    try:
        cred = credentials.Certificate('serviceAccountKey.json')
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"NexusAI Connection Error: {e}")

db = firestore.client()

# --- 2. SESSION STATE ---
if "chat_id" not in st.session_state:
    st.session_state.chat_id = str(uuid.uuid4())[:8]

# --- 3. UI CONFIG (NexusAI Branding) ---
st.set_page_config(page_title="NexusAI Assistant", page_icon="🌐", layout="wide")
user_id = "owner_petar_nexus" # Unique owner ID

# --- 4. SIDEBAR (NexusAI History) ---
with st.sidebar:
    st.title("🌐 NexusAI")
    st.subheader("Control Center")
    if st.button("➕ New Nexus Chat", use_container_width=True):
        st.session_state.chat_id = str(uuid.uuid4())[:8]
        st.rerun()

    st.divider()
    st.subheader("Memory Bank")
    try:
        # Loading from the new nexus_chats collection
        history_ref = db.collection("nexus_chats").document(user_id).collection("sessions").order_by("start_time", direction=firestore.Query.DESCENDING).limit(15)
        for session in history_ref.stream():
            sess_data = session.to_dict()
            title = sess_data.get("first_msg", "New Connection")[:25]
            if st.button(f"💬 {title}", key=session.id):
                st.session_state.chat_id = session.id
                st.rerun()
    except:
        st.write("NexusAI memory is empty.")

st.title("🌐 NexusAI: The Ultimate Interface")

# --- 5. LOAD CURRENT CHAT ---
messages_ref = db.collection("nexus_chats").document(user_id).collection("sessions").document(st.session_state.chat_id).collection("messages").order_by("timestamp")
current_messages = list(messages_ref.stream())

for msg_doc in current_messages:
    m = msg_doc.to_dict()
    with st.chat_message(m["role"]):
        if "https://image.pollinations.ai" in m["text"]:
            st.image(m["text"], caption="NexusAI Vision")
        else:
            st.write(m["text"])

# --- 6. NEXUS LOGIC (FORCED IMAGE & SMART TALK) ---
prompt = st.chat_input("Command NexusAI...")

if prompt:
    with st.chat_message("user"):
        st.markdown(prompt)

    # Initial session setup
    if not current_messages:
        db.collection("nexus_chats").document(user_id).collection("sessions").document(st.session_state.chat_id).set({
            "first_msg": prompt, "start_time": datetime.now()
        })

    db.collection("nexus_chats").document(user_id).collection("sessions").document(st.session_state.chat_id).collection("messages").add({
        "role": "user", "text": prompt, "timestamp": datetime.now()
    })

    # PRO IMAGE GENERATION (NexusVision)
    img_triggers = ["draw", "image", "picture", "generate", "create", "photo", "paint", "sliku", "nacrtaj"]
    if any(word in prompt.lower() for word in img_triggers):
        with st.chat_message("assistant"):
            with st.spinner("🌐 NexusAI is visualizing..."):
                seed = random.randint(0, 9999999)
                clean_prompt = prompt.lower()
                for word in img_triggers:
                    clean_prompt = clean_prompt.replace(word, "")
                
                # Using the Pro Flux engine
                img_url = f"https://image.pollinations.ai/prompt/{clean_prompt.strip().replace(' ', '%20')}?width=1024&height=1024&model=flux&nologo=true&seed={seed}&enhance=true"
                
                st.image(img_url)
                
                db.collection("nexus_chats").document(user_id).collection("sessions").document(st.session_state.chat_id).collection("messages").add({
                    "role": "assistant", "text": img_url, "timestamp": datetime.now()
                })
    else:
        # SMART TALK (Direct, Cool, No "Vi")
        with st.chat_message("assistant"):
            try:
                # Core instruction for NexusAI persona
                sys_prompt = "Your name is NexusAI. You are a high-tech, direct, and cool AI assistant. Speak naturally like a friend. Never use 'Vi' or formal plural. English only. "
                api_url = f"https://text.pollinations.ai/{sys_prompt}{prompt}?model=openai"
                response = requests.get(api_url)
                ai_text = response.text
                
                st.markdown(ai_text)
                
                db.collection("nexus_chats").document(user_id).collection("sessions").document(st.session_state.chat_id).collection("messages").add({
                    "role": "assistant", "text": ai_text, "timestamp": datetime.now()
                })
            except:
                st.error("NexusAI Core Offline. Check Connection.")
