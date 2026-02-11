import streamlit as st
from services.auth import get_gcp_credentials
from services.rag_service import RagService
from services.llm import GeminiTutor
from api.client import ApiClient
from ui.styles import apply_custom_styles
from ui.components import render_history, render_recommendation, get_history_text

# --- SETUP ---
st.set_page_config(page_title="YouCanMath AI Tutor", page_icon="📐", layout="centered")

# 1. Autenticazione & Inizializzazione Servizi
credentials = get_gcp_credentials()
rag_service = RagService(credentials)
tutor = GeminiTutor()
api_client = ApiClient()

# 2. UI Setup
# 2. UI Setup
apply_custom_styles()
st.title("📐 YouCanMath AI Tutor")

# Expander per Immagini
with st.expander("📸 Carica un'immagine del problema (opzionale)"):
    uploaded_file = st.file_uploader("Allega immagine", type=["jpg", "jpeg", "png", "webp"])

# 3. Rendering Storico
render_history()

# --- CHAT LOOP ---
if prompt := st.chat_input("Chiedimi una spiegazione matematica..."):
    
    # Preparazione messaggio utente
    user_msg = {"role": "user", "content": prompt}
    image_data = None
    
    if uploaded_file:
        image_data = uploaded_file.getvalue()
        user_msg["image"] = image_data

    # Salva messaggio utente
    st.session_state.messages.append(user_msg)
    
    with st.chat_message("user"):
        if image_data:
            st.image(image_data, width=200)
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Elaborazione della lezione in corso..."):
            try:
                # A. Recupero Candidati Manuali (RAG Engine)
                # search_results serve se vuoi debuggare, candidates_text va al modello
                _, candidates_text = rag_service.search_candidates(prompt)

                # B. Ottieni Storico
                # Recuperiamo tutto tranne l'ultimo (il prompt corrente)
                current_history = st.session_state.messages[:-1]
                
                # Funzione helper rapida per formattare solo questa slice
                history_text_formatted = "\n\n=== PREVIOUS CONVERSATION ===\n"
                if current_history:
                    for msg in current_history:
                        role = "Student" if msg["role"] == "user" else "Tutor"
                        content = msg["content"][:300] + "..." if len(msg["content"]) > 300 else msg["content"]
                        history_text_formatted += f"{role}: {content}\n"
                else:
                    history_text_formatted += "Nessuna conversazione precedente.\n"

                # C. Generazione Risposta (LLM) - Passiamo image_data se presente
                response = tutor.generate_response(prompt, history_text_formatted, candidates_text, image_data=image_data)
                
                # D. Parsing & Rendering
                res_data = tutor.clean_json_response(response.text)
                
                full_response_text = ""
                for rec in res_data.get("recommendations", []):
                    full_response_text += render_recommendation(rec, api_client)
                
                # E. Salva Risposta Tutor nello Storico
                st.session_state.messages.append({"role": "assistant", "content": full_response_text})

            except Exception as e:
                st.error(f"Qualcosa è andato storto: {e}")
                # st.write(response.text) # Uncomment for debug