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
st.set_page_config(page_title="YouCanMath AI Tutor", page_icon="📐", layout="centered")

# CSS personalizzato per migliorare la leggibilità del LaTeX
st.markdown("""
    <style>
    .stMarkdown p { font-size: 1.1rem; line-height: 1.6; }
    .katex { font-size: 1.1em ! lacer; }
    </style>
    """, unsafe_allow_html=True)

st.title("📐 YouCanMath AI Tutor")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Visualizzazione storico con supporto Markdown + LaTeX
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Chiedimi una spiegazione matematica..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Risolvendo l'equazione..."):
            response = model.generate_content(
                prompt,
                tools=tools,
                generation_config=GenerationConfig(temperature=0.1)
            )
            
            clean_json = re.sub(r"```json\s?|```", "", response.text).strip()
            
            try:
                res_data = json.loads(clean_json)
                
                for rec in res_data.get("recommendations", []):
                    # Il messaggio principale ora renderizza il LaTeX grazie a st.markdown
                    message_content = rec.get("message", "")
                    st.markdown(message_content)
                    
                    # Se c'è un video, lo carichiamo
                    if rec.get("video_url"):
                        st.write("---")
                        st.video(rec["video_url"])
                    
                    # Soluzioni e Quiz con stile dedicato
                    if rec.get("step_by_step_solution"):
                        with st.expander("📝 Guarda i passaggi matematici"):
                            for step in rec["step_by_step_solution"]:
                                # Usiamo markdown per permettere mix di testo e formule inline
                                st.markdown(f"**-** {step}")

                    if rec.get("quiz_questions"):
                        st.info("🎯 Mettiti alla prova:")
                        for q in rec["quiz_questions"]:
                            st.markdown(f"❓ {q}")
                
                st.session_state.messages.append({"role": "assistant", "content": message_content})

            except Exception as e:
                st.error("Errore di formattazione. Testo originale:")
                st.write(response.text)
