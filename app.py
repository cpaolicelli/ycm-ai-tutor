import streamlit as st
import vertexai
import json
from google.oauth2 import service_account
from vertexai.generative_models import GenerativeModel, Tool, grounding, GenerationConfig

# Configurazione costanti
PROJECT_ID = "youcanmath"
LOCATION = "us-central1"
DATA_STORE_ID = "ycm-rag-1"
DATA_STORE_PATH = f"projects/{PROJECT_ID}/locations/global/collections/default_collection/dataStores/{DATA_STORE_ID}"

# DEBUG: Verifica se i segreti sono caricati senza mostrarli interamente
if "gcp_service_account" in st.secrets:
    secrets_dict = st.secrets["gcp_service_account"]
    st.write("### 🛠 Debug Secrets")
    st.write(f"✅ Project ID trovato: `{secrets_dict.get('project_id')}`")
    st.write(f"✅ Email account: `{secrets_dict.get('client_email')}`")
    
    # Verifichiamo la chiave privata senza stamparla
    pk = secrets_dict.get('private_key', "")
    if pk:
        st.write(f"✅ Private Key presente (Lunghezza: {len(pk)} caratteri)")
        if pk.startswith("-----BEGIN PRIVATE KEY-----"):
            st.write("✅ Formato Private Key: Inizia correttamente")
        else:
            st.error("❌ Formato Private Key ERRATO: Non inizia con il tag corretto")
    else:
        st.error("❌ Private Key MANCANTE nei segreti")
else:
    st.error("❌ Il blocco [gcp_service_account] non è stato trovato nei Secrets di Streamlit")

if "gcp_service_account" in st.secrets:
    creds_info = dict(st.secrets["gcp_service_account"])
    # Questo corregge i problemi di formatting dei caratteri \n
    creds_info["private_key"] = creds_info["private_key"].replace("\\n", "\n")
    
    credentials = service_account.Credentials.from_service_account_info(creds_info)
    vertexai.init(project=PROJECT_ID, location=LOCATION, credentials=credentials)

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
    "gemini-1.5-flash",
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
