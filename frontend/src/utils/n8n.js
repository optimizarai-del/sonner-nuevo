const BASE = import.meta.env.VITE_N8N_BASE || "https://n8n.optimizar-ia.com";

export const WEBHOOKS = {
  chat:      import.meta.env.VITE_N8N_WEBHOOK_INTERNO   || `${BASE}/webhook/sonner-pagina`,
  contratos: import.meta.env.VITE_N8N_WEBHOOK_CONTRATOS  || `${BASE}/webhook/sonner-contratos`,
  analista:  import.meta.env.VITE_N8N_WEBHOOK_ANALISTA   || `${BASE}/webhook/sonner-analista`,
};

/**
 * POST a un webhook de n8n con timeout configurable.
 * Devuelve el JSON de respuesta o lanza un error.
 */
export async function callWebhook(url, body, timeoutMs = 90_000) {
  const controller = new AbortController();
  const tid = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: controller.signal,
    });
    clearTimeout(tid);
    if (!res.ok) throw new Error(`n8n respondió ${res.status}`);
    return await res.json();
  } catch (err) {
    clearTimeout(tid);
    throw err;
  }
}

/** Extrae el texto de respuesta del JSON que devuelve n8n */
export function extractText(data) {
  if (typeof data === "string") return data;
  return (
    data?.output   ??
    data?.text     ??
    data?.message  ??
    data?.reply    ??
    data?.respuesta ??
    JSON.stringify(data)
  );
}
