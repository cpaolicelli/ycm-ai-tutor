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

# System Prompt aggiornato con obbligo LaTeX
SYSTEM_INSTRUCTION = """Sei il tutor esperto di YouCanMath. Usa la RAG per rispondere.

REGOLE MANDATORIE PER IL FORMATO:
1. FORMULE MATEMATICHE: Ogni singola variabile, operazione o formula deve essere scritta in LaTeX racchiusa tra simboli del dollaro.
   Esempio: Invece di scrivere 'x al quadrato', scrivi sempre '$x^2$'. Invece di 'A unione B', scrivi '$A \\cup B$'.
2. OUTPUT: Rispondi ESCLUSIVAMENTE con un oggetto JSON valido. Non aggiungere spiegazioni fuori dal JSON.

Struttura JSON:
{
  "intent": "spiegazione" | "interrogazione" | "risoluzione_esercizio",
  "recommendations": [
    {
      "id_lesson": "ID",
      "video_url": "URL",
      "message": "Testo con formule LaTeX inline (es: $f(x) = y$)",
      "quiz_questions": ["Domande con LaTeX"],
      "step_by_step_solution": ["Passaggi con LaTeX"]
    }
  ]
}
"""

model = GenerativeModel(
    "gemini-2.5-flash",
    system_instruction=SYSTEM_INSTRUCTION
)

# --- INTERFACCIA UTENTE ---
st.set_page_config(page_title="YouCanMath AI Tutor", page_icon="📐")
st.title("📐 YouCanMath AI Tutor")

# CSS per rendere i caratteri matematici più leggibili
st.markdown("""
    <style>
    .stMarkdown p { font-size: 1.1rem; }
    .katex { font-size: 1.1em; color: #1E88E5; }
    </style>
    """, unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Chiedimi una spiegazione matematica..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Calcolo in corso..."):
            response = model.generate_content(
                prompt,
                tools=tools,
                generation_config=GenerationConfig(temperature=0.1)
            )
            
            # Pulizia automatica dei tag markdown JSON
            clean_json = re.sub(r"```json\s?|```", "", response.text).strip()
            
            try:
                res_data = json.loads(clean_json)
                
                for rec in res_data.get("recommendations", []):
                    # Messaggio principale con supporto LaTeX inline
                    ans_text = rec.get("message", "")
                    st.markdown(ans_text)
                    
                    # Se l'AI ha trovato un video nei metadati del Data Store
                    if rec.get("video_url"):
                        st.write("---")
                        st.video(rec["video_url"])
                    
                    # Passaggi matematici
                    if rec.get("step_by_step_solution"):
                        with st.expander("📝 Procedimento dettagliato"):
                            for step in rec["step_by_step_solution"]:
                                st.markdown(f"**-** {step}")

                    # Quiz per lo studente
                    if rec.get("quiz_questions"):
                        st.info("🎯 Esercitati ora:")
                        for q in rec["quiz_questions"]:
                            st.markdown(f"❓ {q}")
                
                st.session_state.messages.append({"role": "assistant", "content": ans_text})

            except Exception:
                # Fallback nel caso il JSON sia malformato, mostra comunque il testo
                st.markdown(response.text)
