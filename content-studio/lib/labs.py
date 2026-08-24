"""Cliente de labs.google: autenticación de dos saltos y llamadas pausadas.

Core reutilizable. Autocontenido a propósito — cada plugin de este
ecosistema lleva su `lib/` adentro para funcionar una vez instalado, sin
depender de que otro repositorio esté presente.

Sólo stdlib: `urllib`, no `requests`. El Python de Homebrew está bajo
PEP 668 e instalar dependencias forzaría `--break-system-packages` sobre el
intérprete del sistema.

    cookie __Secure-next-auth.session-token      (dura meses)
      └─► GET labs.google/fx/api/auth/session ─► access_token (dura horas)
            └─► Authorization: Bearer ─► aisandbox-pa.googleapis.com/v1/*

Las credenciales nunca viven en el repositorio. Se leen de
`~/.config/google-flow/` —el mismo lugar donde ya las tiene el plugin
`google-flow`, para no pedir dos veces la misma exportación— o de donde
apunte `FLOW_COOKIES`.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

LABS = "https://labs.google/fx"
SANDBOX = "https://aisandbox-pa.googleapis.com/v1"

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
)

# Pausa mínima entre llamadas. No se baja. El riesgo de una cuenta marcada
# como automatizada no es por corrida: se acumula sobre la cuenta, y con
# ella se pierde todo el trabajo que dependía de esa sesión.
PAUSA_MIN_S = 2.5

CONFIG_FLOW = Path(os.environ.get("FLOW_CONFIG_DIR", Path.home() / ".config" / "google-flow"))
CACHE_TOKEN = Path(os.environ.get("FLOW_TOKEN_CACHE", CONFIG_FLOW / ".flow-token.json"))


class LabsAuthError(RuntimeError):
    """La sesión no sirve. Quien reciba esto pide re-exportar, no reintenta."""


class LabsError(RuntimeError):
    """Falla operativa contra la API."""


_ultima_llamada = 0.0


def _pausar() -> None:
    global _ultima_llamada
    delta = time.monotonic() - _ultima_llamada
    if delta < PAUSA_MIN_S:
        time.sleep(PAUSA_MIN_S - delta)
    _ultima_llamada = time.monotonic()


# -------------------------------------------------------------------- cookies


def ruta_cookies(explicita: str | os.PathLike | None = None) -> Path:
    """Ubica el JSON de cookies sin suponer una estructura de repositorio.

    Una ruta explícita es una afirmación sobre QUÉ cuenta usar: si no
    existe, falla en vez de buscar en otro lado.
    """
    for origen, valor in (("argumento", explicita), ("FLOW_COOKIES", os.environ.get("FLOW_COOKIES"))):
        if valor:
            p = Path(valor).expanduser()
            if not p.is_file():
                raise LabsAuthError(
                    f"El {origen} apunta a {p}, que no existe. No busco en otro "
                    "lado para no usar una cuenta distinta de la que pediste."
                )
            return p

    candidatas = [
        Path.cwd() / "cookies" / "labs.google.cookies.json",
        Path.cwd() / "labs.google.cookies.json",
        CONFIG_FLOW / "labs.google.cookies.json",
        CONFIG_FLOW / "cookies.json",
    ]
    for c in candidatas:
        if c.is_file():
            return c
    raise LabsAuthError(
        "No encontré las cookies de labs.google. Exportalas desde el navegador "
        f"con la sesión iniciada a {CONFIG_FLOW / 'labs.google.cookies.json'} y "
        "hacele chmod 600, o apuntá FLOW_COOKIES al archivo.\n"
        "Si ya usás el plugin google-flow, es el mismo archivo: no hace falta "
        "exportar de nuevo."
    )


def _jar(explicita=None) -> dict[str, str]:
    ruta = ruta_cookies(explicita)
    try:
        crudo = json.loads(ruta.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise LabsAuthError(f"{ruta} no es JSON válido ({e}). Re-exportá las cookies.") from e

    ahora, jar = time.time(), {}
    for c in crudo:
        exp = c.get("expires") or c.get("expirationDate") or 0
        if exp and 0 < exp < ahora:
            continue
        if "labs.google" in c.get("domain", ""):
            jar[c["name"]] = c["value"]
    if "__Secure-next-auth.session-token" not in jar:
        raise LabsAuthError(
            "Falta la cookie __Secure-next-auth.session-token, o está vencida. "
            "Re-exportá las cookies de labs.google desde el navegador."
        )
    return jar


# ----------------------------------------------------------------------- auth


def _pedir(url: str, *, headers: dict, data: bytes | None = None,
           method: str = "GET", timeout: int = 120) -> tuple[int, bytes]:
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    _pausar()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def sesion(explicita=None) -> dict:
    """Respuesta cruda de /api/auth/session: usuario, vencimiento y bearer."""
    cookie = "; ".join(f"{k}={v}" for k, v in _jar(explicita).items())
    code, body = _pedir(
        f"{LABS}/api/auth/session",
        headers={"Cookie": cookie, "User-Agent": UA, "Accept": "application/json"},
        timeout=30,
    )
    if code >= 400:
        raise LabsAuthError(
            f"/api/auth/session respondió {code}. La cookie ya no sirve: "
            "re-exportá las de labs.google."
        )
    try:
        return json.loads(body)
    except json.JSONDecodeError as e:
        raise LabsAuthError(f"Respuesta no-JSON de /api/auth/session: {e}") from e


def _pedir_token(explicita=None) -> tuple[str, float]:
    data = sesion(explicita)

    # `expires` es el vencimiento de la sesión NextAuth. Pasado ese punto el
    # endpoint sigue devolviendo un access_token, pero vencido — sin este
    # chequeo la falla aparece después como un 401 opaco de googleapis que
    # no dice qué hacer.
    vence = data.get("expires")
    if vence:
        try:
            exp = datetime.fromisoformat(vence.replace("Z", "+00:00"))
            if exp < datetime.now(timezone.utc):
                raise LabsAuthError(
                    f"La sesión de Flow venció el {vence}. Re-exportá las cookies "
                    "de labs.google desde el navegador."
                )
        except ValueError:
            pass  # formato inesperado: seguimos y que falle más adelante si falla

    token = data.get("access_token")
    if not token:
        raise LabsAuthError(
            "La sesión respondió sin access_token: la cookie ya no es válida. "
            "Re-exportá las cookies de labs.google."
        )
    return token, time.time() + 45 * 60


def token(refrescar: bool = False, explicita=None) -> str:
    if not refrescar and CACHE_TOKEN.is_file():
        try:
            cache = json.loads(CACHE_TOKEN.read_text())
            if cache.get("expires_at", 0) > time.time() + 60:
                return cache["token"]
        except (json.JSONDecodeError, KeyError):
            pass
    t, vence = _pedir_token(explicita)
    CACHE_TOKEN.parent.mkdir(parents=True, exist_ok=True)
    CACHE_TOKEN.write_text(json.dumps({"token": t, "expires_at": vence}))
    CACHE_TOKEN.chmod(0o600)
    return t


def estado() -> dict:
    """Diagnóstico de sesión. Toca la red, pero no gasta nada."""
    ruta = ruta_cookies()
    data = sesion()
    usuario = data.get("user") or {}
    return {
        "archivo_cookies": str(ruta),
        "permisos": oct(ruta.stat().st_mode)[-3:],
        "usuario": usuario.get("email") or usuario.get("name"),
        "vence": data.get("expires"),
        "bearer": "ok" if data.get("access_token") else "FALTA",
        "valida": bool(data.get("access_token")),
    }


# -------------------------------------------------------------------- sandbox


def api(method: str, path: str, *, params: dict | None = None,
        body: Any = None, reintentar_auth: bool = True) -> Any:
    """Llamada a aisandbox con el bearer, pausada y con un solo reintento.

    El reintento es exclusivamente para renovar el bearer vencido, que es
    una condición esperada (dura horas). Cualquier otro error no se
    reintenta: un 403 repetido rápido es exactamente lo que se mide.
    """
    url = f"{SANDBOX}/{path.lstrip('/')}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    datos = json.dumps(body).encode() if body is not None else None
    code, crudo = _pedir(
        url,
        headers={
            "Authorization": f"Bearer {token()}",
            "User-Agent": UA,
            "Accept": "*/*",
            "Origin": "https://labs.google",
            "Referer": "https://labs.google/",
            "Content-Type": "application/json",
        },
        data=datos,
        method=method.upper(),
    )
    if code in (401, 403) and reintentar_auth:
        token(refrescar=True)
        return api(method, path, params=params, body=body, reintentar_auth=False)
    if code >= 400:
        detalle = crudo[:1200].decode("utf-8", "replace")
        if code in (401, 403):
            raise LabsAuthError(
                f"{code} en {path}. La sesión no alcanza para esta ruta. "
                "Re-exportá las cookies de labs.google.\n" + detalle
            )
        raise LabsError(f"{method.upper()} {path} -> {code}\n{detalle}")
    if not crudo:
        return {}
    try:
        return json.loads(crudo)
    except json.JSONDecodeError:
        return {"_crudo": crudo.decode("utf-8", "replace")}


def creditos() -> dict:
    """Saldo de la cuenta. Los créditos son de quien instala, no del agente:
    se miden y se informan, no se deciden por él."""
    return api("GET", "credits")


def listar_applets() -> list[dict]:
    return api("GET", "flowAppletAgent/applets").get("applets", [])


def obtener_applet(applet_id: str, version_id: str | None = None) -> dict:
    if version_id is None:
        match = next((a for a in listar_applets() if a["appletId"] == applet_id), None)
        if match is None:
            raise LabsError(f"El applet {applet_id} no existe en esta cuenta.")
        version_id = match["currentVersionId"]
    return api("GET", f"flowAppletAgent/applets/{applet_id}/versions/{version_id}")
