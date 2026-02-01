import os
import toml
from rag.engine import RagEngine
from google.oauth2 import service_account

# Load secrets
try:
    secrets = toml.load(".streamlit/secrets.toml")
    creds_info = secrets["gcp_service_account"]
    
    # Fix private key formatting if needed
    if "private_key" in creds_info:
        creds_info["private_key"] = creds_info["private_key"].replace("\\n", "\n")
        
    credentials = service_account.Credentials.from_service_account_info(creds_info)
    
    PROJECT_ID = "youcanmath"
    LOCATION = "global"
    DATA_STORE_ID = "ycm-rag-unstructured"
    
    print(f"Initializing RagEngine for {PROJECT_ID} / {LOCATION} / {DATA_STORE_ID}...")
    
    engine = RagEngine(
        project_id=PROJECT_ID,
        location=LOCATION,
        data_store_id=DATA_STORE_ID,
        credentials=credentials
    )
    
    query = "Equazioni di secondo grado letterali"
    print(f"Searching for: '{query}'...")
    
    results = engine.search(query)
    
    print(f"Found {len(results)} results.")
    for res in results:
        print(f"- Title: {res['title']}")
        print(f"  ID: {res['id']}")
        print(f"  Snippet len: {len(res['content'])}")
        print("---")
        
except Exception as e:
    print(f"Error: {e}")
