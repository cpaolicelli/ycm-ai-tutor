import streamlit as st
import vertexai
import json
import re
from google.oauth2 import service_account
from vertexai.generative_models import GenerativeModel, Tool, grounding, GenerationConfig

# --- CONFIGURAZIONE ---
PROJECT_ID = "youcanmath"
LOCATION = "europe-west1"
DATA_STORE_ID = "ycm-rag-unstructured"
DATA_STORE_PATH = f"projects/{PROJECT_ID}/locations/global/collections/default_collection/dataStores/{DATA_STORE_ID}"
BASE_VIDEO_URL = "https://ycm-video.b-cdn.net"

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

SYSTEM_INSTRUCTION = """Sei il tutor di matematica di YouCanMath.
Il tuo obiettivo è risolvere i dubbi dello studente in modo PUNTUALE, SINTETICO e PRATICO.
Lo studente segue già videolezioni, quindi NON fare lezioni teoriche generali se non strettamente necessario.

REGOLE DI COMPORTAMENTO (CRUCIALI):
1. **Sintesi Estrema:** Evita spiegazioni enciclopediche o introduttive. Vai dritto al punto della domanda.
2. **Pratica su Teoria:** Se l'utente chiede un esempio o un esercizio, fornisci una brevissima premessa (max 1-2 frasi) e concentra tutta la risposta sulla risoluzione pratica passo-passo dell'esempio.
3. **Rispondi alla domanda:** Se l'utente chiede un dettaglio specifico (es. "perché questo numero è 6?"), spiega solo quel passaggio logico, senza rispiegare tutta la regola generale da capo.
4. **Niente "Muri di Testo":** Usa liste puntate e vai a capo spesso. La spiegazione deve avvenire *attraverso* l'esercizio, non *prima* dell'esercizio.

REGOLE DI FORMATO (MANDATORIE):
1. Rispondi ESCLUSIVAMENTE con un oggetto JSON valido. Niente testo prima o dopo.
2. Usa la seguente struttura esatta:
{
  "intent": "spiegazione" | "interrogazione" | "risoluzione_esercizio",
  "recommendations": [
    {
      "id_lesson": "Codice o Titolo Lezione",
      "video_url": "URL completo (o null se non presente)",
      "message": "Qui inserisci la spiegazione diretta. Usa Markdown per titoli (###) e liste. Usa LaTeX tra dollari ($...$) per le formule. Sii breve.",
      "quiz_questions": ["Domanda 1 mirata", "Domanda 2 mirata"],
      "step_by_step_solution": ["Passaggio 1 con calcolo esplicito", "Passaggio 2 con risultato"]
    }
  ]
}

REGOLE DI CONTENUTO:
- Usa LaTeX per TUTTI i simboli matematici (es. $x$, $\\alpha$, $\\frac{a}{b}$).
- Se l'utente chiede un esempio, usane uno numerico concreto e risolvilo nel campo 'message' o 'step_by_step_solution'.
"""

model = GenerativeModel(
    "gemini-2.5-flash",
    system_instruction=SYSTEM_INSTRUCTION
)

# --- INTERFACCIA UTENTE ---
st.set_page_config(page_title="YouCanMath AI Tutor", page_icon="📐", layout="centered")

# CSS Migliorato per LaTeX e Spaziatura
st.markdown("""
    <style>
    /* Migliora leggibilità testo generale - Rimosso colore fisso per compatibilità Dark Mode */
    .stMarkdown p { font-size: 1.05rem; line-height: 1.6; }
    
    /* Colore e stile per le formule LaTeX */
    .katex { font-size: 1.1em !important; }
    
    /* Light Mode per KaTeX (Default Blue) */
    @media (prefers-color-scheme: light) {
        .katex { color: #0d47a1; }
    }
    
    /* Dark Mode per KaTeX (Light Blue/Cyan) */
    @media (prefers-color-scheme: dark) {
        .katex { color: #64b5f6; }
    }

    /* Stile per il box del video */
    div[data-testid="stVideo"] { border-radius: 10px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    /* Stile per i box dei quiz */
    .stInfo { background-color: rgba(227, 242, 253, 0.5); border-left-color: #1e88e5; }
    </style>
    """, unsafe_allow_html=True)

st.title("📐 YouCanMath AI Tutor")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Visualizzazione Storico
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Input Utente
if prompt := st.chat_input("Chiedimi una spiegazione matematica..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Elaborazione della lezione in corso..."):
            try:
                # Chiamata al Modello
                response = model.generate_content(
                    prompt,
                    tools=tools,
                    generation_config=GenerationConfig(temperature=0.1)
                )
                
                # Pulizia JSON (Rimuove markdown ```json ... ```)
                clean_json = re.sub(r"```json\s?|```", "", response.text).strip()
                
                # FIX: Escape dei backslash per LaTeX se il modello non lo ha fatto
                # Modificata regex per includere anche \f (frac), \t (tan), \b, \r ma escludere \n e unipcode validi
                clean_json = re.sub(r'(?<!\\)\\(?!["\\/n]|u[0-9a-fA-F]{4})', r'\\\\', clean_json)
                
                # Parsing
                res_data = json.loads(clean_json)
                
                # Loop sulle raccomandazioni
                full_response_text = "" # Per salvare nello storico alla fine
                
                for rec in res_data.get("recommendations", []):
                    
                    # 1. MESSAGGIO PRINCIPALE (TEORIA)
                    # Qui st.markdown farà la magia: interpreterà i ### come titoli, 
                    # i \n come a capo e i $...$ come LaTeX
                    message_content = rec.get("message", "")
                    if message_content:
                        st.markdown(message_content)
                        full_response_text += message_content + "\n\n"

                    # 2. VIDEO (Se presente)
                    if rec.get("lesson_id"):
                        st.write("---")
                        st.markdown(f"### 📺 Video Lezione: {rec.get('id_lesson', '')}")
                        st.video(rec["video_url"])
                        full_response_text += f"[Video: {rec['video_url']}]\n"

                    # 3. QUIZ (Se presenti)
                    if rec.get("quiz_questions"):
                        st.write("---")
                        st.markdown("### 📝 Quiz di verifica")
                        for i, q in enumerate(rec["quiz_questions"], 1):
                            # st.info supporta Markdown e LaTeX al suo interno!
                            st.info(f"**{i}.** {q}") 

                    # 4. SOLUZIONE STEP-BY-STEP (Se presente)
                    if rec.get("step_by_step_solution"):
                        with st.expander("🔍 Vedi Soluzione Passo-Passo"):
                            for step in rec["step_by_step_solution"]:
                                st.markdown(f"- {step}")

                # Aggiornamento storico messaggi (salviamo il testo base per semplicità)
                st.session_state.messages.append({"role": "assistant", "content": full_response_text})

            except json.JSONDecodeError:
                st.error("Errore nel formato della risposta. Visualizzo il testo grezzo:")
                st.write(response.text)
            except Exception as e:
                st.error(f"Errore imprevisto: {e}")
