"""Jobs de fondo: watchdog de corridas y resumen diario. Ver `scheduler.py`.

El keep-alive de Supabase NO está acá a propósito: lo sigue haciendo el GitHub Action
`.github/workflows/supabase-keepalive.yml`, que funciona aunque el servicio esté caído
—que es justo cuando hace falta. Ver la bitácora del plan de migración.
"""

from . import digest, scheduler, watchdog

__all__ = ["digest", "scheduler", "watchdog"]
