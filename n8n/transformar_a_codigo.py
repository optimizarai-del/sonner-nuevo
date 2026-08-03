# -*- coding: utf-8 -*-
"""Transforma el workflow `SONNER · PRINCIPAL EXTERNO` para usar el agente en código.

Borra el nodo AI Agent `AGENTE PRINCIPAL MINORISTA` y TODOS sus sub-nodos (subagentes,
modelos LLM, memoria, parsers, tools de Google/Calendar/Sheets, Memoria HTTP, etc.),
agrega en su lugar un nodo HTTP Request (mismo nombre) que le pega a /api/agente/n8n, y
reconecta todo. n8n sigue recibiendo / buffizando / enviando; el cerebro corre en código.

Uso:
    python transformar_a_codigo.py  entrada.json  salida.json

Después: importá salida.json en n8n. La X-Memoria-Key del nodo nuevo usa
$env.MEMORIA_INTERNAL_KEY; si tu n8n no tiene esa variable, editá el header y poné el
valor literal (el mismo de tu nodo Memoria).
"""
import json
import sys

# Nodos a eliminar (el AI Agent + todo lo que le colgaba). Nombres exactos.
REMOVE = {
    "AGENTE PRINCIPAL MINORISTA",              # el AI Agent (se reemplaza por el HTTP)
    "Postgres Chat Memory1",
    "Anthropic Chat Model1", "Google Gemini Chat Model1",
    "Think",
    "agente_calendario", "Anthropic Chat Model9", "Google Gemini Chat Model2",
    "Auto-fixing Output Parser", "Structured Output Parser4", "Anthropic Chat Model5",
    "Create_Read2", "Get availability in a calendar in Google Calendar",
    "AGENTE DE SALONES", "Anthropic Chat Model2", "Google Gemini Chat Model9",
    "leer1", "crear1", "actualizar1",
    "Auto-fixing Output Parser1", "Structured Output Parser5", "Anthropic Chat Model14",
    "Consultar_Reunion",
    "Memoria",
}

# Nodo HTTP que reemplaza al AI Agent (mismo nombre → los nodos de abajo no cambian).
HTTP_NODE = {
    "parameters": {
        "method": "POST",
        "url": "https://n8n-nuevo-agente-sonner.3buyoj.easypanel.host/api/agente/n8n",
        "sendHeaders": True,
        "headerParameters": {
            "parameters": [
                {"name": "X-Memoria-Key", "value": "={{ $env.MEMORIA_INTERNAL_KEY }}"},
                {"name": "Content-Type", "value": "application/json"},
            ]
        },
        "sendBody": True,
        "specifyBody": "json",
        "jsonBody": "={{ JSON.stringify({ mensaje: Array.isArray($('Redis7').item.json.mensajes) ? $('Redis7').item.json.mensajes.join(String.fromCharCode(10)) : $('Redis7').item.json.mensajes, telefono: $('Edit Fields2').item.json.usuario, nombre: $('Edit Fields2').item.json.nombre_usuario, tipo_cliente: $('Code in JavaScript').item.json.tipo_cliente }) }}",
        "options": {"timeout": 120000},
    },
    "type": "n8n-nodes-base.httpRequest",
    "typeVersion": 4.2,
    "position": [28544, 1280],
    "id": "a9e1f000-0000-4000-8000-agenteprincipal",
    "name": "AGENTE PRINCIPAL MINORISTA",
}


def transformar(data: dict) -> dict:
    # 1) sacar los nodos a eliminar y agregar el HTTP (mismo nombre)
    data["nodes"] = [n for n in data["nodes"] if n.get("name") not in REMOVE]
    data["nodes"].append(HTTP_NODE)
    vivos = {n["name"] for n in data["nodes"]}  # incluye el HTTP nuevo

    # 2) reconstruir connections: conservar solo las que salen de nodos vivos y
    #    apuntan a nodos vivos (elimina todo el cableado ai_* de los subagentes).
    nuevas = {}
    for src, conns in (data.get("connections") or {}).items():
        if src not in vivos:
            continue
        limpio = {}
        for ctype, grupos in conns.items():
            grupos_filtrados = [[t for t in grupo if t.get("node") in vivos] for grupo in grupos]
            if any(any(g) for g in grupos_filtrados):
                limpio[ctype] = grupos_filtrados
        if limpio:
            nuevas[src] = limpio
    data["connections"] = nuevas
    return data


def main():
    if len(sys.argv) != 3:
        print("Uso: python transformar_a_codigo.py entrada.json salida.json")
        sys.exit(1)
    with open(sys.argv[1], encoding="utf-8") as f:
        data = json.load(f)
    data = transformar(data)

    # Chequeo de integridad: toda conexión debe apuntar a un nodo existente.
    vivos = {n["name"] for n in data["nodes"]}
    rotas = []
    for src, conns in data["connections"].items():
        for ctype, grupos in conns.items():
            for grupo in grupos:
                for t in grupo:
                    if t.get("node") not in vivos:
                        rotas.append((src, t.get("node")))
    if rotas:
        print("ADVERTENCIA: conexiones rotas:", rotas)

    with open(sys.argv[2], "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("OK. Nodos: %d  |  archivo: %s" % (len(data["nodes"]), sys.argv[2]))
    print("Verificá que exista el nodo HTTP 'AGENTE PRINCIPAL MINORISTA' y sus 4 salidas.")


if __name__ == "__main__":
    main()
