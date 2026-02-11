import streamlit as st

def apply_custom_styles():
    """
    Applica gli stili CSS personalizzati per l'applicazione.
    Gestisce LaTeX (KaTeX), Dark Mode, e layout componenti.
    """
    st.markdown("""
    <style>
    /* Migliora leggibilità testo generale */
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
