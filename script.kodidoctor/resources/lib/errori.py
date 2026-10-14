# -*- coding: utf-8 -*-
"""Interpreta il testo di un errore (anche di un altro addon o del log di Kodi) e ne spiega la causa."""

import re

from . import testi

# Segnali di una riproduzione fallita nel log di Kodi stesso
PLAYER_RE = re.compile(
    r"CVideoPlayer::OpenInputStream|Playlist Player: skipping unplayable item|"
    r"Open - failed to open source|failed to open inputstream|"
    r"InputStream.{0,40}(?:failed|not found|disabled)", re.IGNORECASE)

# (espressione regolare, chiave in ESITI_URL). L'ordine conta: la prima che combacia vince.
# I numeri di stato HTTP si cercano solo in forma esplicita, per non confonderli con altri numeri.
REGOLE = (
    (r"ModuleNotFoundError|No module named", "modulo_mancante"),
    (r"NameResolutionError|Failed to resolve|No address associated|Name or service not known|"
     r"Temporary failure in name resolution|getaddrinfo failed|gaierror|"
     r"Couldn't resolve host|Could not resolve host", "dns"),
    (r"CERTIFICATE_VERIFY_FAILED|certificate verify failed|SSLCertVerificationError|SSLError|"
     r"SSL certificate problem|SSL connect error", "certificato"),
    (r"cf-chl|Just a moment|Attention Required|error code: 1020", "cloudflare"),
    # l'addon non riesce a superare la protezione Cloudflare di un sito
    (r"app non raggiungibile|timeout avvio app|impossibile risolvere", "cloudflare_app"),
    (r"timed out|ReadTimeout|ConnectTimeout|TimeoutError|Timeout was reached", "timeout"),
    (r"Connection refused|ConnectionRefusedError", "rifiutata"),
    (r"Connection reset|ConnectionResetError|RemoteDisconnected", "reset"),
    (r"HTTP Error 403|403 Client Error|403 Forbidden|status[_ ]?code[=: ]+403|returned error 403|"
     r"\bForbidden\b", "vietato"),
    (r"HTTP Error 404|404 Client Error|404 Not Found|status[_ ]?code[=: ]+404|returned error 404",
     "non_trovato"),
    (r"HTTP Error 429|429 Client Error|Too Many Requests|status[_ ]?code[=: ]+429|returned error 429",
     "troppe_richieste"),
    (r"HTTP Error 451|451 Client Error|status[_ ]?code[=: ]+451|returned error 451", "bloccato_legale"),
    (r"HTTP Error 5\d\d|5\d\d Server Error|Bad Gateway|Service Unavailable|status[_ ]?code[=: ]+5\d\d|"
     r"returned error 5\d\d", "errore_server"),
    (PLAYER_RE.pattern, "apertura_flusso"),
)

_COMPILATE = tuple((re.compile(s, re.IGNORECASE if k in ("cloudflare", "apertura_flusso") else 0), k)
                   for s, k in REGOLE)


def host_dall_errore(testo):
    for schema in (r"Failed to resolve '([^']+)'", r"Failed to resolve hostname ([A-Za-z0-9.\-]+?)[,\s]",
                   r"impossibile risolvere ([A-Za-z0-9][A-Za-z0-9.\-]*\.[A-Za-z]{2,})", r"host='([^']+)'", r"https?://([^/\s'\"]+)"):
        m = re.search(schema, testo or "")
        if m:
            return m.group(1)
    return None


def interpreta_errore(testo):
    """Ritorna None se non riconosce l'errore, altrimenti un dict pronto da mostrare."""
    testo = testo or ""
    for schema, chiave in _COMPILATE:
        m = schema.search(testo)
        if m:
            stato, titolo, spiegazione, soluzione = testi.ESITI_URL[chiave]
            return {"causa": chiave, "stato": stato, "titolo": titolo,
                    "spiegazione": spiegazione, "soluzione": soluzione,
                    "host": host_dall_errore(testo), "frammento": m.group(0)}
    return None
