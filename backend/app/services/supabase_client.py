"""Cliente Supabase singleton."""
from supabase import create_client, Client
from ..config import settings

_client: Client | None = None
_admin_client: Client | None = None


def get_supabase() -> Client:
    global _client
    if _client is None:
        _client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
    return _client


def get_supabase_admin() -> Client:
    """Cliente con service_role (saltea RLS). Solo backend. Cae a anon si no hay key."""
    global _admin_client
    if _admin_client is None:
        key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY
        _admin_client = create_client(settings.SUPABASE_URL, key)
    return _admin_client


def insertar_contrato(form: dict, urls: dict) -> dict | None:
    """Inserta el registro del contrato en la tabla `contratos` de Supabase."""
    sb = get_supabase()
    payload = {
        "nombre_prestatario":     form.get("nombre_prestatario"),
        "dni_prestatario":        form.get("DNI_prestatario"),
        "domicilio_prestatario":  form.get("domicilio_prestatario"),
        "lugar_evento":           form.get("lugar_evento"),
        "dia_evento":             form.get("dia_evento"),
        "dia_finevento":          form.get("dia_finevento"),
        "hora_inicio":            form.get("hora_inicio"),
        "hora_fin":               form.get("hora_fin"),
        "dias_para_pagar":        form.get("dias_para_pagar"),
        "valor_total_prestacion": form.get("valor_total_prestacion") or 0,
        "equipamientos":          form.get("equipamientos"),
        "monto_total_pesos":      form.get("monto_total_pesos") or 0,
        "monto_total_reserva":    form.get("monto_total_reserva") or 0,
        "saldo_a_cancelar":       form.get("saldo_a_cancelar") or 0,
        "dia_firma":              form.get("dia_firma"),
        "mes_firma":              form.get("mes_firma"),
        "anio_firma":             form.get("año_firma"),
        "doc_url":                urls["doc_url"],
        "pdf_url":                urls["pdf_url"],
    }
    res = sb.table("contratos").insert(payload).execute()
    return res.data[0] if res.data else None
