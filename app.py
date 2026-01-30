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

# --- INTERFACCIA STREAMLIT ---
st.set_page_config(page_title="YouCanMath AI Tutor", page_icon="📐")
st.title("📐 YouCanMath AI Tutor")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Chiedimi pure..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Analizzando le lezioni..."):
            # Chiamata RAG (Senza response_schema per evitare l'errore 400)
            response = model.generate_content(
                prompt,
                tools=tools,
                generation_config=GenerationConfig(
                    temperature=0.2 # Bassa temperatura per maggiore stabilità JSON
                )
            )
            
            # Pulizia della risposta (rimuove eventuali blocchi ```json )
            raw_text = response.text
            clean_json = re.sub(r"```json\s?|```", "", raw_text).strip()
            
            try:
                res_data = json.loads(clean_json)
                intent = res_data.get("intent")
                
                for rec in res_data.get("recommendations", []):
                    # Messaggio principale
                    st.markdown(rec.get("message", ""))
                    
                    # Video
                    if rec.get("video_url"):
                        st.link_button("🎥 Guarda la Video Lezione", rec["video_url"])
                    
                    # Soluzione Step-by-Step
                    if intent == "risoluzione_esercizio" and rec.get("step_by_step_solution"):
                        with st.expander("Vedi i passaggi della soluzione"):
                            for step in rec["step_by_step_solution"]:
                                st.write(f"• {step}")

                    # Quiz
                    if intent == "interrogazione" and rec.get("quiz_questions"):
                        st.info("Prova a rispondere a queste domande:")
                        for q in rec["quiz_questions"]:
                            st.write(f"❓ {q}")
                
                # Salvataggio nello storico
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": res_data["recommendations"][0]["message"]
                })
                
            except Exception as e:
                st.error("Errore nel parsing della risposta dell'AI. Riprova.")
                st.write(raw_text) # Utile per debug
