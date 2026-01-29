import streamlit as st
import vertexai
import json
import os
from vertexai.generative_models import GenerativeModel, Tool, grounding, GenerationConfig


# 1. Configurazione Iniziale Google Cloud
PROJECT_ID = "youcanmath"
LOCATION = "global"
DATA_STORE_ID = "ycm-rag-1" # Assicurati che sia l'ID corretto
DATA_STORE_PATH = f"projects/{PROJECT_ID}/locations/global/collections/default_collection/dataStores/{DATA_STORE_ID}"

# Carica le credenziali dai Secrets di Streamlit
if "gcp_service_account" in st.secrets:
    creds_info = st.secrets["gcp_service_account"]
    credentials = service_account.Credentials.from_service_account_info(creds_info)
    vertexai.init(project=PROJECT_ID, location=LOCATION, credentials=credentials)
else:
    # Per il test locale (se hai gcloud auth login fatto)
    vertexai.init(project=PROJECT_ID, location=LOCATION)

# 2. Configurazione dello Schema di Risposta (JSON)
response_schema = {
    "type": "OBJECT",
    "properties": {
        "intent": {"type": "STRING", "enum": ["risoluzione_esercizio", "interrogazione", "spiegazione"]},
        "recommendations": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "id_lesson": {"type": "STRING"},
                    "video_url": {"type": "STRING"},
                    "message": {"type": "STRING"},
                    "quiz_questions": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "step_by_step_solution": {"type": "ARRAY", "items": {"type": "STRING"}}
                },
                "required": ["id_lesson", "message"]
            }
        }
    },
    "required": ["intent", "recommendations"]
}

# 3. Setup del Modello con RAG
# Sostituisci il vecchio blocco tools con questo:
tools = [
    Tool.from_retrieval(
        retrieval=grounding.Retrieval(
            source=grounding.VertexAISearch(datastore=DATA_STORE_PATH)
        )
    )
]

model = GenerativeModel(
    "gemini-2.5-flash",
    system_instruction="Sei il tutor di YouCanMath. Usa la RAG per rispondere. Se l'utente vuole un video, estrai video_url dai metadati. Se vuole un quiz, usa quiz_questions. Rispondi SEMPRE in JSON."
)

# --- INTERFACCIA STREAMLIT ---
st.set_page_config(page_title="YouCanMath AI Tutor", page_icon="📐")
st.title("📐 YouCanMath AI Tutor")
st.caption("Il tuo assistente personale per la matematica supportato da RAG")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Mostra lo storico dei messaggi
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Input Utente
if prompt := st.chat_input("Chiedimi un esercizio o una spiegazione..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Consultando i manuali..."):
            # Chiamata a Gemini con Grounding e Schema JSON
            response = model.generate_content(
                prompt,
                tools=tools,
                generation_config=GenerationConfig(
                    response_mime_type="application/json",
                    response_schema=response_schema
                )
            )
            
            # Parsing della risposta JSON
            res_data = json.loads(response.text)
            
            # Logica di Visualizzazione UI basata sull'intento
            intent = res_data.get("intent")
            for rec in res_data.get("recommendations", []):
                st.write(rec["message"])
                
                # Mostra link video se presente
                if "video_url" in rec and rec["video_url"]:
                    st.video(rec["video_url"]) if "youtube" in rec["video_url"] else st.link_button("🎥 Guarda la Video Lezione", rec["video_url"])
                
                # Mostra soluzione step-by-step se l'intento è risoluzione
                if intent == "risoluzione_esercizio" and "step_by_step_solution" in rec:
                    with st.expander("Vedi i passaggi della soluzione"):
                        for step in rec["step_by_step_solution"]:
                            st.write(f"• {step}")

                # Mostra quiz se l'intento è interrogazione
                if intent == "interrogazione" and "quiz_questions" in rec:
                    st.info("Rispondi a queste domande per l'interrogazione:")
                    for q in rec["quiz_questions"]:
                        st.write(f"❓ {q}")

    st.session_state.messages.append({"role": "assistant", "content": res_data["recommendations"][0]["message"]})
