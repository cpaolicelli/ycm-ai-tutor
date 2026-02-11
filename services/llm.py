import json
import re
from vertexai.generative_models import GenerativeModel, Tool, grounding, GenerationConfig, Part
from config import DATA_STORE_PATH

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
      "lesson_id": "Seleziona ESCLUSIVAMENTE uno degli ID elencati nella sezione 'CANDIDATE LESSONS' del prompt. Scegli quello più pertinente alla richiesta. Se nessuno è pertinente, usa null.",
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

class GeminiTutor:
    def __init__(self):
        self.tools = [
             Tool.from_retrieval(
                retrieval=grounding.Retrieval(
                    source=grounding.VertexAISearch(datastore=DATA_STORE_PATH)
                )
            )
        ]
        self.model = GenerativeModel(
            "gemini-2.5-flash",
            system_instruction=SYSTEM_INSTRUCTION
        )

    def generate_response(self, prompt, history, candidates_context, image_data=None):
        """
        Genera una risposta usando il modello Gemini configurato.
        Combina storico, prompt corrente, candidati trovati manualmente e opzionalmente un'immagine.
        """
        augmented_prompt = f"{history}\n\n=== CURRENT REQUEST ===\n{prompt}\n{candidates_context}"
        
        contents = [augmented_prompt]
        
        if image_data:
            # Crea un oggetto Part per l'immagine
            image_part = Part.from_data(
                data=image_data,
                mime_type="image/jpeg" # Assumiamo JPEG o PNG, Vertex AI gestisce entrambi
            )
            contents.append(image_part)
        
        response = self.model.generate_content(
            contents,
            tools=self.tools,
            generation_config=GenerationConfig(temperature=0.1)
        )
        return response

    @staticmethod
    def clean_json_response(text):
        """
        Pulisce la risposta raw del modello per estrarre il JSON valido.
        Gestisce i markdown fence e i backslash LaTeX.
        """
        # Rimuove markdown ```json ... ```
        clean_json = re.sub(r"```json\s?|```", "", text).strip()
        
        # FIX: Escape dei backslash per LaTeX se il modello non lo ha fatto
        # Modificata regex per includere anche \f (frac), \t (tan), \b, \r ma escludere \n e unicode validi
        clean_json = re.sub(r'(?<!\\)\\(?!["\\/n]|u[0-9a-fA-F]{4})', r'\\\\', clean_json)
        
        try:
            return json.loads(clean_json)
        except json.JSONDecodeError as e:
            # Rilancia l'errore o ritorna None, qui preferiamo gestire l'eccezione nel chiamante o rilanciarla
            raise e
