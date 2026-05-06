MEMORY_TOOLS = [
    {
        "name": "search_memory",
        "description": "Busca información en la memoria interna de SONNER. Usa source para filtrar: 'eventos', 'informacion_interna' o 'materiales'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Texto a buscar"},
                "source": {
                    "type": "string",
                    "enum": ["eventos", "informacion_interna", "materiales"],
                    "description": "Namespace de la memoria a consultar",
                },
            },
            "required": ["query", "source"],
        },
    },
]
