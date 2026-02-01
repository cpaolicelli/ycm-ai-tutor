from typing import List, Dict, Optional
import re
from google.cloud import discoveryengine
from google.api_core.client_options import ClientOptions

class RagEngine:
    def __init__(self, project_id: str, location: str, data_store_id: str, credentials=None):
        self.project_id = project_id
        self.location = location
        self.data_store_id = data_store_id
        # Per Discovery Engine, se usiamo 'global' collections, usiamo l'endpoint di default.
        # Se specifichiamo una location, la libreria dovrebbe gestirla, ma spesso l'endpoint deve essere esplicito.
        # Tuttavia, se il datastore path è 'locations/global', allora la location deve essere 'global'.
        
        self.client_options = None
        if location != "global":
             self.client_options = ClientOptions(api_endpoint=f"{location}-discoveryengine.googleapis.com")

        self.client = discoveryengine.SearchServiceClient(
            client_options=self.client_options,
            credentials=credentials
        )
        self.serving_config = self.client.serving_config_path(
            project=project_id,
            location=location,
            data_store=data_store_id,
            serving_config="default_config",
        )

    def search(self, query: str, limit: int = 3) -> List[Dict]:
        """
        Esegue una ricerca su Discovery Engine e restituisce i risultati processati.
        Estrae l'ID dal contenuto usando la regex specifica.
        """
        request = discoveryengine.SearchRequest(
            serving_config=self.serving_config,
            query=query,
            page_size=limit,
            content_search_spec=discoveryengine.SearchRequest.ContentSearchSpec(
                snippet_spec=discoveryengine.SearchRequest.ContentSearchSpec.SnippetSpec(
                    return_snippet=True
                ),
                summary_spec=discoveryengine.SearchRequest.ContentSearchSpec.SummarySpec(
                    summary_result_count=3,
                    include_citations=True,
                ),
            ),
        )

        try:
            response = self.client.search(request)
            results = []
            
            for result in response.results:
                data = result.document.derived_struct_data
                content = ""
                
                # Cerca di estrarre il contenuto completo o snippet
                if "snippets" in data and data["snippets"]:
                    content = data["snippets"][0].get("snippet", "")
                elif "extractive_answers" in data and data["extractive_answers"]:
                     content = data["extractive_answers"][0].get("content", "")
                
                # Se possibile, prova a prendere il contenuto raw dal documento originale se presente
                # Nota: spesso è in `struct_data` o `derived_struct_data` a seconda dell'indicizzazione
                
                # ESTRAZIONE ID MANUALE
                # Pattern: > **ID**: <valore>
                # Cerca in tutto il documento disponibile
                doc_id = None
                # Se abbiamo accesso al testo completo del documento (dipende dalla config), usiamo quello.
                # Altrimenti proviamo a cercare nello snippet, ma potrebbe essere tagliato.
                # Per ora assumiamo che l'ID sia nel titolo o nelle prime righe dello snippet.
                
                # Tentativo 1: Regex sul contenuto dello snippet/risultato
                match = re.search(r'> \*\*ID\*\*: ([a-zA-Z0-9]+)', content)
                if match:
                    doc_id = match.group(1)
                
                # Se non trovato, proviamo a vedere se è stato passato come metadato (se configurato)
                # Fallback: parsing del titolo se contiene l'ID (es: ID_Titolo.md)
                if not doc_id:
                     title = result.document.derived_struct_data.get("title", "")
                     # Esempio: 68b81c5dddd308c8ac4ea6e6_Equazioni...
                     match_title = re.match(r'^([a-zA-Z0-9]+)_', title)
                     if match_title:
                         doc_id = match_title.group(1)

                results.append({
                    "id": doc_id,
                    "title": result.document.derived_struct_data.get("title", ""),
                    "content": content,
                    "link": result.document.derived_struct_data.get("link", "")
                })
                
            return results

        except Exception as e:
            print(f"Error executing search: {e}")
            return []
