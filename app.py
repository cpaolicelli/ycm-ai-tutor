import streamlit as st
import vertexai
import json
import re
from google.oauth2 import service_account
from vertexai.generative_models import GenerativeModel, Tool, grounding, GenerationConfig

# --- CONFIGURAZIONE ---
PROJECT_ID = "youcanmath"
LOCATION = "europe-west1"
DATA_STORE_ID = "ycm-rag-1"
DATA_STORE_PATH = f"projects/{PROJECT_ID}/locations/global/collections/default_collection/dataStores/{DATA_STORE_ID}"

# --- AUTENTICAZIONE ---
if "gcp_service_account" in st.secrets:
    creds_info = dict(st.secrets["gcp_service_account"])
    if "private_key" in creds_info:
        pk = creds_info["private_key"].replace("\\n", "\n").strip()
        creds_info["private_key"] = pk

    try:
        credentials = service_account.Credentials.from_service_account_info(creds_info)
        vertexai.init(project=PROJECT_ID, location=LOCATION, credentials=credentials)
    except Exception as e:
        st.error(f"Errore Credenziali: {e}")

# --- SETUP RAG E MODELLO ---
tools = [
    Tool.from_retrieval(
        retrieval=grounding.Retrieval(
            source=grounding.VertexAISearch(datastore=DATA_STORE_PATH)
        )
    )
]

# Istruzioni di sistema per forzare l'output JSON senza response_schema
SYSTEM_INSTRUCTION = """Sei il tutor AI di YouCanMath. Usa esclusivamente la RAG fornita per rispondere.
Rispondi SEMPRE in formato JSON puro. Non aggiungere testo libero fuori dal JSON.

Struttura richiesta:
{
  "intent": "spiegazione" | "interrogazione" | "risoluzione_esercizio",
  "recommendations": [
    {
      "id_lesson": "ID della lezione",
      "video_url": "URL del video se presente",
      "message": "La tua spiegazione o risposta testuale principale",
      "quiz_questions": ["domanda 1", "domanda 2"],
      "step_by_step_solution": ["passaggio 1", "passaggio 2"]
    }
  ]
}
"""

model = GenerativeModel(
    "gemini-2.5-flash",
    system_instruction=SYSTEM_INSTRUCTION
)

# --- INTERFACCIA UTENTE ---
st.set_page_config(page_title="YouCanMath AI Tutor", page_icon="📐", layout="wide")
st.title("📐 YouCanMath AI Tutor")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Visualizzazione storico
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Input Utente
if prompt := st.chat_input("Chiedimi una spiegazione sugli insiemi..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Consultando il database YouCanMath..."):
            # Chiamata a Gemini
            response = model.generate_content(
                prompt,
                tools=tools,
                generation_config=GenerationConfig(temperature=0.1)
            )
            
            # Pulizia e Parsing del JSON
            raw_text = response.text
            clean_json = re.sub(r"```json\s?|```", "", raw_text).strip()
            
            try:
                res_data = json.loads(clean_json)
                
                for rec in res_data.get("recommendations", []):
                    # 1. Messaggio del Tutor
                    msg_text = rec.get("message", "")
                    st.markdown(msg_text)
                    
                    # 2. BOX VIDEO (Se presente URL)
                    video_url = rec.get("video_url")
                    if video_url:
                        st.write("---")
                        st.subheader("🎥 Video Lezione Suggerita")
                        # Carica il video in un player nativo
                        st.video(video_url)
                        st.caption(f"Sorgente: {video_url}")
                    
                    # 3. Altri contenuti (Quiz/Soluzioni)
                    if rec.get("step_by_step_solution"):
                        with st.expander("📝 Vedi i passaggi matematici"):
                            for step in rec["step_by_step_solution"]:
                                st.latex(step) if "$" in step else st.write(step)

                st.session_state.messages.append({"role": "assistant", "content": msg_text})

            except Exception as e:
                st.error("Non sono riuscito a formattare la risposta. Ecco il testo:")
                st.write(raw_text)
