from rag.engine import RagEngine
from config import PROJECT_ID, LOCATION, DATA_STORE_ID
import streamlit as st

class RagService:
    def __init__(self, credentials):
        self.engine = None
        if credentials:
            try:
                # Discovery Engine richiede location="global" se il datastore è globale
                self.engine = RagEngine(
                    project_id=PROJECT_ID,
                    location="global", 
                    data_store_id=DATA_STORE_ID,
                    credentials=credentials
                )
            except Exception as e:
                st.error(f"Errore inizializzazione Ricerca Manuale (RagService): {e}")

    def search_candidates(self, query, limit=3):
        """
        Esegue la ricerca manuale e ritorna:
        1. Lista raw dei risultati (per debug/toast)
        2. Stringa formattata da iniettare nel prompt
        """
        search_results = []
        candidates_text = "\n\n=== CANDIDATE LESSONS (Scegli l'ID più appropriato da qui) ===\n"
        
        if self.engine:
            try:
                search_results = self.engine.search(query, limit=limit)
            except Exception as e:
                st.warning(f"Ricerca manuale fallita: {e}")

        if search_results:
            for i, res in enumerate(search_results, 1):
                candidates_text += f"{i}. [ID: {res['id']}] Titolo: {res['title']}\n   Contenuto: {res['content'][:300]}...\n\n"
        else:
            candidates_text += "Nessun documento trovato dalla ricerca manuale.\n"
            
        return search_results, candidates_text
