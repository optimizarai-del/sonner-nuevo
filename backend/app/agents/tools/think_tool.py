THINK_TOOL = {
    "name": "think",
    "description": "Usa esta herramienta para razonar internamente antes de responder. No obtiene información nueva ni modifica datos. Solo registra el pensamiento en el log interno.",
    "input_schema": {
        "type": "object",
        "properties": {
            "thought": {"type": "string", "description": "El razonamiento o pensamiento interno"},
        },
        "required": ["thought"],
    },
}
