import streamlit as st
from config import BASE_VIDEO_URL

def render_history():
    """Renderizza l'intero stack di messaggi in session_state."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
        
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            if "image" in msg:
                st.image(msg["image"], width=200)
            st.markdown(msg["content"])

def render_recommendation(rec, api_client):
    """
    Renderizza una singola raccomandazione (blocco) dalla risposta JSON.
    Ritona il testo completo generato per l'archiviazione nello storico.
    """
    full_text_chunk = ""
    
    # 1. MESSAGGIO PRINCIPALE (TEORIA)
    message_content = rec.get("message", "")
    if message_content:
        st.markdown(message_content)
        full_text_chunk += message_content + "\n\n"

    # 2. VIDEO (Se presente)
    if lesson_id := rec.get("lesson_id"):
        try:
            video_api_url = f"https://api.youcanmath.it/lesson/get-video/{lesson_id}"
            api_response = api_client.get(video_api_url)
            
            if api_response.status_code == 200:
                # Parsing URL
                partial_url = api_response.text.strip().strip('"') 
                try:
                     json_resp = api_response.json()
                     if isinstance(json_resp, dict) and "url" in json_resp:
                         partial_url = json_resp["url"]
                     elif isinstance(json_resp, str):
                         partial_url = json_resp
                except:
                    pass 
                
                full_video_url = f"{BASE_VIDEO_URL}/{partial_url}"
                
                st.write("---")
                st.markdown(f"### 📺 Video Lezione: {rec.get('id_lesson', '')}")
                st.video(full_video_url)
                full_text_chunk += f"[Video: {full_video_url}]\n"
            else:
                st.warning(f"Video non disponibile (API Error: {api_response.status_code})")
        except Exception as e:
            st.warning(f"Errore caricamento video: {e}")

    # 3. QUIZ
    if rec.get("quiz_questions"):
        st.write("---")
        st.markdown("### 📝 Quiz di verifica")
        for i, q in enumerate(rec["quiz_questions"], 1):
            st.info(f"**{i}.** {q}") 

    # 4. SOLUZIONE STEP-BY-STEP
    if rec.get("step_by_step_solution"):
        with st.expander("🔍 Vedi Soluzione Passo-Passo"):
            for step in rec["step_by_step_solution"]:
                st.markdown(f"- {step}")
                
    return full_text_chunk

def get_history_text():
    """
    Restituisce una rappresentazione testuale dello storico per il prompt.
    Esclude l'ultimo messaggio (corrente) se non ancora aggiunto, o lo gestisce il chiamante.
    Qui assumiamo che st.session_state.messages contenga SOLO lo storico precedente.
    """
    history_text = "\n\n=== PREVIOUS CONVERSATION ===\n"
    if len(st.session_state.messages) > 0:
        for msg in st.session_state.messages:
            role_label = "Student" if msg["role"] == "user" else "Tutor"
            content_preview = msg["content"][:500] + ("..." if len(msg["content"]) > 500 else "")
            history_text += f"{role_label}: {content_preview}\n"
    else:
        history_text += "Nessuna conversazione precedente.\n"
    return history_text
