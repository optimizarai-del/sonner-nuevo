CALENDAR_TOOLS = [
    # ── LECTURA ────────────────────────────────────────────────────────────────
    {
        "name": "encontrar_evento_sonner",
        "description": (
            "Busca eventos en los 3 calendarios de Sonner simultáneamente: "
            "Eventos Sonner, Fiestas Tijereta y Fiestas Cromo. "
            "Usalo como PASO 1 obligatorio antes de cualquier actualización o eliminación de eventos de Sonner. "
            "Devuelve listas de eventos con sus IDs."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "time_min": {
                    "type": "string",
                    "description": "Inicio del rango en ISO 8601 con timezone. Ej: 2026-05-10T00:00:00-03:00"
                },
                "time_max": {
                    "type": "string",
                    "description": "Fin del rango en ISO 8601 con timezone. Ej: 2026-05-11T23:59:59-03:00"
                },
            },
            "required": ["time_min", "time_max"],
        },
    },
    {
        "name": "get_availability_sonner",
        "description": (
            "Busca disponibilidad en el calendario Eventos Sonner entre dos fechas. "
            "Retorna los eventos ya agendados en ese rango para saber si la fecha está libre."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "time_min": {
                    "type": "string",
                    "description": "Inicio del rango en ISO 8601. Ej: 2026-05-10T00:00:00-03:00"
                },
                "time_max": {
                    "type": "string",
                    "description": "Fin del rango en ISO 8601. Ej: 2026-05-10T23:59:59-03:00"
                },
            },
            "required": ["time_min", "time_max"],
        },
    },
    {
        "name": "encontrar_reunion",
        "description": (
            "Obtiene un evento personal del calendario Reuniones Gabi por su ID. "
            "Usalo como PASO 1 obligatorio antes de actualizar o eliminar una reunión de Gabi."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "event_id": {
                    "type": "string",
                    "description": "ID del evento en Google Calendar"
                },
            },
            "required": ["event_id"],
        },
    },

    # ── CREAR ──────────────────────────────────────────────────────────────────
    {
        "name": "crear_evento_sonner",
        "description": (
            "Crea un evento nuevo en el calendario Eventos Sonner. "
            "Usalo para eventos de producción, fechas de trabajo y eventos de la empresa."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "summary":     {"type": "string", "description": "Título del evento"},
                "start":       {"type": "string", "description": "Inicio en ISO 8601 con timezone. Ej: 2026-05-10T20:00:00-03:00"},
                "end":         {"type": "string", "description": "Fin en ISO 8601 con timezone. Ej: 2026-05-11T04:00:00-03:00"},
                "description": {"type": "string", "description": "Descripción del evento (opcional)"},
                "location":    {"type": "string", "description": "Lugar del evento (opcional)"},
            },
            "required": ["summary", "start", "end"],
        },
    },
    {
        "name": "crear_reunion",
        "description": (
            "Crea un evento personal en el calendario Reuniones Gabi. "
            "Usalo EXCLUSIVAMENTE para bloqueos personales de Gabi: ir al banco, compromisos propios, ausencias, indisponibilidades."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "summary":     {"type": "string", "description": "Título del bloqueo o reunión personal"},
                "start":       {"type": "string", "description": "Inicio en ISO 8601 con timezone"},
                "end":         {"type": "string", "description": "Fin en ISO 8601 con timezone"},
                "description": {"type": "string", "description": "Descripción (opcional)"},
                "location":    {"type": "string", "description": "Lugar (opcional)"},
            },
            "required": ["summary", "start", "end"],
        },
    },

    # ── ACTUALIZAR ─────────────────────────────────────────────────────────────
    {
        "name": "actualizar_evento_sonner",
        "description": (
            "Actualiza el TÍTULO y/o DESCRIPCIÓN de un evento en Eventos Sonner. "
            "NO usar para cambiar fechas u horarios — para eso usar actualizar_fechas_sonner. "
            "FLUJO OBLIGATORIO: 1) encontrar_evento_sonner → 2) obtener ID → 3) usar esta herramienta."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "event_id":    {"type": "string", "description": "ID del evento (obtenido de encontrar_evento_sonner)"},
                "summary":     {"type": "string", "description": "Nuevo título (opcional)"},
                "description": {"type": "string", "description": "Nueva descripción (opcional)"},
            },
            "required": ["event_id"],
        },
    },
    {
        "name": "actualizar_fechas_sonner",
        "description": (
            "Cambia la FECHA y/o HORARIO de un evento en Eventos Sonner. "
            "NO usar para cambiar solo el título — para eso usar actualizar_evento_sonner. "
            "Fechas en ISO 8601 con timezone. Ej: 2026-05-10T20:00:00-03:00. "
            "FLUJO OBLIGATORIO: 1) encontrar_evento_sonner → 2) obtener ID → 3) usar esta herramienta."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "event_id":    {"type": "string", "description": "ID del evento (obtenido de encontrar_evento_sonner)"},
                "start":       {"type": "string", "description": "Nueva fecha/hora de inicio en ISO 8601 con timezone"},
                "end":         {"type": "string", "description": "Nueva fecha/hora de fin en ISO 8601 con timezone"},
                "summary":     {"type": "string", "description": "Nuevo título (opcional)"},
                "description": {"type": "string", "description": "Nueva descripción (opcional)"},
            },
            "required": ["event_id", "start", "end"],
        },
    },
    {
        "name": "actualizar_reunion",
        "description": (
            "Modifica un evento personal en el calendario Reuniones Gabi. "
            "FLUJO OBLIGATORIO: 1) encontrar_reunion → 2) obtener ID → 3) usar esta herramienta."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "event_id":    {"type": "string", "description": "ID del evento (obtenido de encontrar_reunion)"},
                "summary":     {"type": "string", "description": "Nuevo título (opcional)"},
                "start":       {"type": "string", "description": "Nueva fecha/hora de inicio en ISO 8601 (opcional)"},
                "end":         {"type": "string", "description": "Nueva fecha/hora de fin en ISO 8601 (opcional)"},
                "description": {"type": "string", "description": "Nueva descripción (opcional)"},
            },
            "required": ["event_id"],
        },
    },

    # ── ELIMINAR ───────────────────────────────────────────────────────────────
    {
        "name": "eliminar_evento_sonner",
        "description": (
            "Elimina un evento del calendario Eventos Sonner. "
            "FLUJO OBLIGATORIO: 1) encontrar_evento_sonner → 2) obtener ID → 3) usar esta herramienta."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "event_id": {"type": "string", "description": "ID del evento a eliminar (obtenido de encontrar_evento_sonner)"},
            },
            "required": ["event_id"],
        },
    },
    {
        "name": "borrar_reunion",
        "description": (
            "Elimina un evento personal del calendario Reuniones Gabi. "
            "FLUJO OBLIGATORIO: 1) encontrar_reunion → 2) obtener ID → 3) usar esta herramienta."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "event_id": {"type": "string", "description": "ID del evento a eliminar (obtenido de encontrar_reunion)"},
            },
            "required": ["event_id"],
        },
    },
]
