"""Sub-agente de Memoria de SONNER (vector store).

Reemplaza el sub-agente n8n que usaba Gemini + 4 vector stores manuales.
Es determinístico: parsea el comando, elige la fuente y consulta pgvector
vía la RPC `match_documents`. Sin LLM intermedio que elija mal el filtro.
"""
