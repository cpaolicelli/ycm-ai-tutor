import streamlit as st
import vertexai
from google.oauth2 import service_account
from config import PROJECT_ID, LOCATION

def get_gcp_credentials():
    """
    Recupera le credenziali GCP dai secrets di Streamlit e inizializza Vertex AI.
    Ritorna l'oggetto credentials o None se non configurato.
    """
    if "gcp_service_account" in st.secrets:
        try:
            creds_info = dict(st.secrets["gcp_service_account"])
            
            # Fix per le chiavi private nei file TOML che potrebbero avere \n escapati
            if "private_key" in creds_info:
                pk = creds_info["private_key"].replace("\\n", "\n").strip()
                creds_info["private_key"] = pk

            credentials = service_account.Credentials.from_service_account_info(creds_info)
            
            # Inizializza Vertex AI globalmente
            vertexai.init(project=PROJECT_ID, location=LOCATION, credentials=credentials)
            
            return credentials
        except Exception as e:
            st.error(f"Errore inizializzazione Auth GCP: {e}")
            return None
    return None
