# -*- coding: utf-8 -*-
"""Controlli di rete. Nessuna dipendenza da Kodi, cosi si possono provare ovunque."""

import ipaddress
import json
import socket
import ssl
import time
from email.utils import parsedate_to_datetime
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

UA = ("Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Mobile Safari/537.36")

# Riferimenti DoH raggiunti per IP: non passano dal DNS di sistema, che puo essere filtrato
DOH_URLS = ("https://1.1.1.1/dns-query?name=%s&type=A",
            "https://8.8.8.8/resolve?name=%s&type=A")
TRACE_URL = "https://1.1.1.1/cdn-cgi/trace"

# Domini neutri: se nemmeno questi risolvono, il problema e il DNS in generale
DOMINIO_CONTROLLO = "raw.githubusercontent.com"
# oltre ai siti comuni, quelli che i provider italiani bloccano piu spesso e che servono agli addon
DOMINI_BASE = ("raw.githubusercontent.com", "github.com", "cloudflare.com", "google.com", "streamingunity.fun")


def connessione_internet(timeout=4):
    """True se si riesce ad aprire una connessione verso un IP pubblico (senza DNS)."""
    for indirizzo in (("1.1.1.1", 443), ("8.8.8.8", 443)):
        try:
            s = socket.create_connection(indirizzo, timeout=timeout)
            s.close()
            return True
        except OSError:
            continue
    return False


def e_indirizzo_ip(testo):
    try:
        ipaddress.ip_address(testo)
        return True
    except ValueError:
        return False


def ip_sospetto(ip):
    """Un DNS filtrato spesso risponde con IP nulli, locali o privati."""
    try:
        return not ipaddress.ip_address(ip).is_global
    except ValueError:
        return True


def risolvi_sistema(host):
    """Ritorna (insieme di IP, messaggio di errore o None) usando il DNS di sistema."""
    try:
        return set(socket.gethostbyname_ex(host)[2]), None
    except OSError as e:
        return set(), str(e)


def risolvi_doh(host):
    """IP dal riferimento DoH. None se nessun riferimento e raggiungibile."""
    for url in DOH_URLS:
        try:
            req = Request(url % host, headers={"Accept": "application/dns-json", "User-Agent": UA})
            dati = json.loads(urlopen(req, timeout=5).read().decode("utf-8"))
            return set(r["data"] for r in dati.get("Answer", []) if r.get("type") == 1)
        except Exception:
            continue
    return None


def classifica_dominio(host):
    """stato: ok, filtrato, inesistente o indeterminato."""
    sistema, errore = risolvi_sistema(host)
    if sistema and not any(ip_sospetto(i) for i in sistema):
        # Il DNS risponde con un indirizzo normale: puo essere falso (pagina di blocco del provider).
        # Se non coincide con quello di un DNS pubblico, verifico con la connessione sicura.
        riferimento = risolvi_doh(host)
        if riferimento and not (set(sistema) & set(riferimento)):
            dal_dns = [prova_tls(host, ip) for ip in sorted(sistema)[:2]]
            vero = [prova_tls(host, ip) for ip in sorted(riferimento)[:2]]
            if any(r is True for r in vero) and not any(r is True for r in dal_dns):
                return {"host": host, "stato": "filtrato", "ip": sorted(sistema),
                        "riferimento": sorted(riferimento), "dirottato": True}
        return {"host": host, "stato": "ok", "ip": sorted(sistema)}
    riferimento = risolvi_doh(host)
    base = {"host": host, "ip": sorted(sistema), "errore": errore}
    if riferimento:
        return dict(base, stato="filtrato", riferimento=sorted(riferimento))
    if riferimento is None:
        return dict(base, stato="indeterminato")
    return dict(base, stato="inesistente")


def prova_tls(host, ip, timeout=6):
    """True se la connessione sicura a questo indirizzo presenta un certificato valido per host.
    False se il certificato non va, None se non si riesce nemmeno a collegarsi."""
    try:
        with socket.create_connection((ip, 443), timeout=timeout) as sock:
            with ssl.create_default_context().wrap_socket(sock, server_hostname=host):
                return True
    except ssl.SSLError:
        return False
    except OSError:
        return None


def diagnosi_certificato(host):
    """Perche il certificato non e accettato: 'dns_filtrato' se il DNS dirotta il sito su un altro
    server (con l'indirizzo vero il certificato e valido), 'certificato_sito' se e il sito ad averlo
    rotto, None se non si capisce."""
    if e_indirizzo_ip(host):
        return None
    riferimento = risolvi_doh(host)
    if not riferimento:
        return None
    sistema, _ = risolvi_sistema(host)
    col_sistema = [prova_tls(host, ip) for ip in sorted(sistema or [])[:2]]
    col_riferimento = [prova_tls(host, ip) for ip in sorted(riferimento)[:2]]
    if any(r is True for r in col_riferimento):
        if not any(r is True for r in col_sistema):
            return "dns_filtrato"
        return None
    if col_riferimento and all(r is False for r in col_riferimento):
        return "certificato_sito"
    return None


def info_pubblica():
    """IP pubblico, paese, stato di WARP e scarto dell'orologio, via cdn-cgi/trace di Cloudflare."""
    def scarto(intestazioni):
        data = intestazioni.get("Date")
        if not data:
            return None
        try:
            return parsedate_to_datetime(data).timestamp() - time.time()
        except (TypeError, ValueError):
            return None

    try:
        r = urlopen(Request(TRACE_URL, headers={"User-Agent": UA}), timeout=6)
        testo = r.read().decode("utf-8", "replace")
        valori = dict(riga.split("=", 1) for riga in testo.splitlines() if "=" in riga)
        return {"ip": valori.get("ip"), "paese": valori.get("loc"), "warp": valori.get("warp"),
                "colo": valori.get("colo"), "scarto_orologio": scarto(r.headers),
                "certificati_ok": True}
    except ssl.SSLError:
        # Certificato rifiutato: spesso l'orologio e sbagliato. Leggo solo la data del server.
        try:
            ctx = ssl._create_unverified_context()
            r = urlopen(Request(TRACE_URL, headers={"User-Agent": UA}), timeout=6, context=ctx)
            return {"scarto_orologio": scarto(r.headers), "certificati_ok": False}
        except Exception:
            return None
    except Exception:
        return None


def _esito_eccezione(e):
    motivo = getattr(e, "reason", e)
    if isinstance(motivo, socket.gaierror):
        return "dns"
    if isinstance(motivo, ssl.SSLError):
        return "certificato"
    if isinstance(motivo, (socket.timeout, TimeoutError)):
        return "timeout"
    if isinstance(motivo, ConnectionRefusedError):
        return "rifiutata"
    if isinstance(motivo, ConnectionResetError):
        return "reset"
    return "altro"


def prova_url(url, timeout=8):
    """Prova un indirizzo e restituisce un esito leggibile dal resto dell'addon."""
    url = (url or "").strip()
    p = urlparse(url)
    if p.scheme not in ("http", "https") or not p.hostname:
        return {"esito": "url_non_valido"}
    risultato = {"host": p.hostname}
    if not e_indirizzo_ip(p.hostname):
        dominio = classifica_dominio(p.hostname)
        risultato["dominio"] = dominio
        if dominio["stato"] == "filtrato":
            return dict(risultato, esito="dns_filtrato")
        if dominio["stato"] == "inesistente":
            return dict(risultato, esito="dominio_inesistente")

    req = Request(url, headers={"User-Agent": UA, "Range": "bytes=0-2047", "Accept": "*/*"})
    try:
        r = urlopen(req, timeout=timeout)
        codice, intestazioni, corpo = r.getcode(), r.headers, r.read(2048)
    except HTTPError as e:
        codice, intestazioni = e.code, e.headers
        try:
            corpo = e.read(2048)
        except Exception:
            corpo = b""
    except Exception as e:
        return dict(risultato, esito=_esito_eccezione(e), dettaglio=str(e))

    server = (intestazioni.get("Server") or "").lower()
    tipo = (intestazioni.get("Content-Type") or "").lower()
    testo = corpo.decode("utf-8", "replace").lower()
    cloudflare = "cloudflare" in server or intestazioni.get("CF-RAY") is not None
    sfida = any(m in testo for m in ("just a moment", "cf-chl", "attention required", "error code: 1020"))

    risultato.update(codice=codice, tipo=tipo, server=server, cloudflare=cloudflare)
    if codice in (403, 503) and cloudflare and (sfida or codice == 403):
        esito = "cloudflare"
    elif codice == 403:
        esito = "vietato"
    elif codice == 401:
        esito = "autenticazione"
    elif codice in (404, 410):
        esito = "non_trovato"
    elif codice == 429:
        esito = "troppe_richieste"
    elif codice == 451:
        esito = "bloccato_legale"
    elif codice >= 500:
        esito = "errore_server"
    elif codice in (200, 206):
        esito = "pagina_html" if "text/html" in tipo else "ok"
    else:
        esito = "altro"
    return dict(risultato, esito=esito)
