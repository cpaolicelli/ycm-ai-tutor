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

# System Prompt migliorato per una spiegazione discorsiva e LaTeX mandatorio
SYSTEM_INSTRUCTION = """Sei il tutor amichevole di YouCanMath. Usa le informazioni della RAG per spiegare i concetti.
NON copiare solo i dati grezzi: crea una spiegazione discorsiva, accogliente e chiara.

REGOLE MATEMATICHE:
- Ogni formula o variabile DEVE essere in LaTeX tra dollari (es: $x$, $A \cup B$, $f(x)$).

REGOLE FORMATO:
- Rispondi SEMPRE in JSON.
- Il campo "message" deve contenere la spiegazione amichevole completa.
"""

model = GenerativeModel(
    "gemini-2.5-flash",
    system_instruction=SYSTEM_INSTRUCTION
)

# --- INTERFACCIA UTENTE ---
st.set_page_config(page_title="YouCanMath AI Tutor", page_icon="👨🏻‍🏫", layout="centered")

# CSS per abbellire il LaTeX e i box
st.markdown("""
    <style>
    .stMarkdown p { font-size: 1.1rem; line-height: 1.6; }
    .video-container { border: 2px solid #1E88E5; border-radius: 10px; padding: 10px; background-color: #f0f2f6; }
    </style>
    """, unsafe_allow_html=True)

st.title("📐 YouCanMath AI Tutor")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Visualizzazione storico
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Chiedimi una lezione..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Sto preparando la tua lezione..."):
            response = model.generate_content(
                prompt,
                tools=tools,
                generation_config=GenerationConfig(temperature=0.1)
            )
            
            # Pulizia e parsing JSON
            clean_json = re.sub(r"```json\s?|```", "", response.text).strip()
            
            try:
                res_data = json.loads(clean_json)
                
                for rec in res_data.get("recommendations", []):
                    # 1. Messaggio discorsivo del Tutor (con LaTeX)
                    message_text = rec.get("message", "")
                    st.markdown(message_text)
                    
                    # 2. Finestra Anteprima Video (se presente l'URL nel DB)
                    if rec.get("video_url"):
                        st.write("---")
                        st.markdown("### 📺 Video-Lezione Suggerita")
                        st.video(rec["video_url"])
                        st.info(f"Titolo lezione: {rec.get('id_lesson', 'Dettagli')}")
                    
                    # 3. Soluzioni e Quiz
                    if rec.get("step_by_step_solution"):
                        with st.expander("🔍 Procedimento Matematico"):
                            for step in rec["step_by_step_solution"]:
                                st.markdown(f"**-** {step}")

                    if rec.get("quiz_questions"):
                        st.write("---")
                        st.success("🎯 Mettiti alla prova con questi quiz:")
                        for q in rec["quiz_questions"]:
                            st.markdown(f"❓ {q}")
                
                # Salvataggio nello storico
                st.session_state.messages.append({"role": "assistant", "content": message_text})

            except Exception:
                st.markdown(response.text)
