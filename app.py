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

st.title("👨🏻‍🏫 YouCanMath AI Tutor")

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
        with st.spinner("Sto scrivendo la spiegazione matematica..."):
            response = model.generate_content(
                prompt,
                tools=tools,
                generation_config=GenerationConfig(temperature=0.1)
            )
            
            # 1. Pulizia della stringa JSON (rimuove i backticks del markdown)
            clean_json = re.sub(r"```json\s?|```", "", response.text).strip()
            
            try:
                # 2. Parsing del JSON
                res_data = json.loads(clean_json)
                
                # Recuperiamo la lista delle raccomandazioni
                recommendations = res_data.get("recommendations", [])
                
                # Se la lista è vuota, proviamo a cercare un messaggio diretto nel root (fallback)
                if not recommendations and "message" in res_data:
                    recommendations = [res_data]

                for rec in recommendations:
                    # --- A. MESSAGGIO PRINCIPALE (LATEX + TEXT) ---
                    # Estraiamo il testo. Se è None, mettiamo stringa vuota.
                    message_text = rec.get("message", "")
                    
                    # TRUCCO: A volte il JSON ha i \n come doppi backslash \\n se generato male.
                    # Questo li corregge per farli andare a capo correttamente.
                    if message_text:
                        message_text = message_text.replace("\\n", "\n")
                        st.markdown(message_text)
                    
                    # --- B. VIDEO (ANTEPRIMA) ---
                    if rec.get("video_url"):
                        st.write("---") # Linea separatrice
                        st.markdown("### 📺 Video Lezione")
                        # Container visivo per il video
                        with st.container():
                            st.video(rec["video_url"])
                            st.caption(f"Lezione: {rec.get('id_lesson', 'Dettagli')}")
                    
                    # --- C. SOLUZIONI (EXPANDER) ---
                    if rec.get("step_by_step_solution"):
                        with st.expander("📝 Vedi i passaggi matematici"):
                            for step in rec["step_by_step_solution"]:
                                # Renderizza ogni passaggio come Markdown/LaTeX
                                st.markdown(f"**•** {step}")

                    # --- D. QUIZ (BOX SUCCESS) ---
                    if rec.get("quiz_questions"):
                        st.write("---")
                        st.markdown("#### 🎯 Mettiti alla prova")
                        for q in rec["quiz_questions"]:
                            st.info(f"❓ {q}")
                
                # Salvataggio nello storico (solo il testo del primo messaggio per brevità)
                if recommendations:
                    first_msg = recommendations[0].get("message", "")
                    st.session_state.messages.append({"role": "assistant", "content": first_msg})

            except json.JSONDecodeError:
                # Caso di emergenza: se il JSON è rotto, mostriamo il testo grezzo ma pulito
                st.error("Errore nel formato della risposta. Ecco il testo grezzo:")
                st.markdown(response.text)
            except Exception as e:
                st.error(f"Si è verificato un errore imprevisto: {e}")
