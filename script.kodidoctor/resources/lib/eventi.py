# -*- coding: utf-8 -*-
"""Dal testo di un blocco di log a un evento comprensibile, con storico e antispam."""

import json
import os
import re
import time

from . import errori, rete, testi

IGNORA = ("[Kodi Doctor]", "dnscheck")
ID_PLUGIN = re.compile(r"plugin://([A-Za-z0-9_.\-]+)/")
ID_PERCORSO = re.compile(r"addons[/\\]([A-Za-z0-9_.\-]+)[/\\]")
ESCLUSI = ("script.module.", "xbmc.", "resource.", "skin.", "metadata.", "kodi.", "repository.")
PREFISSO_RIGA = re.compile(r"^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\.\d+ T:\d+\s+\w+\s+<[^>]*>:\s?")
SIGLA_LOG = re.compile(r"\b([A-Za-z][A-Za-z0-9_]*)\[[A-Za-z0-9_]+\.[A-Za-z0-9_<>]+:\d+\]")
# Alcuni addon scrivono nel log con una sigla (s4me[modulo.funzione:riga]) invece che con il percorso
SIGLE_ADDON = {"s4me": "plugin.video.s4me", "mandrakodi": "plugin.video.mandrakodi"}
# Controlli di rete che Kodi e Android fanno da soli: non riguardano nessun addon
RUMORE_KODI = re.compile(r"msftconnecttest\.com|connectivitycheck\.|captive\.apple|clients3\.google\.com|"
                         r"CCurlFile::(?:Exists|Stat|Open)\b[^\n]*(?:thumb|\.jpg|\.png|fanart|image)", re.IGNORECASE)
MAX_STORICO = 20


def registra_plugin(id_addon):
    """Impara la sigla di un plugin installato (l'ultima parte del suo id)."""
    if id_addon.startswith("plugin."):
        SIGLE_ADDON.setdefault(id_addon.split(".")[-1].lower(), id_addon)


def interessante(livello, messaggio):
    """Quali righe del log ci riguardano: errori, e avvisi del lettore video."""
    if livello in ("error", "fatal"):
        return True
    return livello == "warning" and bool(errori.PLAYER_RE.search(messaggio))


def trova_addon(testo):
    """L'addon che ha causato l'errore: preferisce i plugin, ignora le librerie."""
    candidati = ID_PLUGIN.findall(testo) + ID_PERCORSO.findall(testo)
    for c in candidati:
        if c.startswith("plugin."):
            return c
    for sigla in SIGLA_LOG.findall(testo):
        if sigla.lower() in SIGLE_ADDON:
            return SIGLE_ADDON[sigla.lower()]
    for c in candidati:
        if not c.startswith(ESCLUSI):
            return c
    return None


def righe_pulite(testo):
    pulite = []
    for riga in testo.splitlines():
        if any(i in riga for i in IGNORA):
            continue
        riga = PREFISSO_RIGA.sub("", riga).strip()
        if riga:
            pulite.append(riga)
    return pulite


def _estratto(righe, frammento):
    scelte = [r for r in righe if frammento and frammento.lower() in r.lower()][:3] or righe[-3:]
    return [r[:240] for r in scelte]


ECCEZIONE = re.compile(r"^(?:[A-Za-z_][\w.]*\.)?[A-Z]\w*(?:Error|Exception)\b(?::.*)?$")


def _eccezione_finale(righe):
    """L'ultima riga di un traceback, tipo 'KeyError: x', se il blocco ne contiene uno."""
    if not any(r.startswith("Traceback") for r in righe):
        return None
    trovate = [r for r in righe if ECCEZIONE.match(r)]
    return trovate[-1][:240] if trovate else None


def analizza_blocco(testo, tutti=False):
    """None se il blocco non e un problema che ci riguarda."""
    righe = righe_pulite(testo)
    if not righe:
        return None
    pulito = "\n".join(righe)
    if RUMORE_KODI.search(pulito) and not any(a.startswith("plugin.") for a in [trova_addon(testo) or ""]):
        return None
    esito = errori.interpreta_errore(pulito)
    if esito is None:
        # Errore che non conosco: se e un traceback di un plugin lo mostro com'e
        addon = trova_addon(testo)
        eccezione = _eccezione_finale(righe)
        if eccezione and addon and addon.startswith("plugin."):
            stato, titolo, spiegazione, soluzione = testi.ESITI_URL["errore_addon"]
            return {"causa": "errore_addon", "stato": stato, "titolo": titolo,
                    "spiegazione": "%s %s" % (spiegazione, eccezione), "soluzione": soluzione,
                    "host": None, "addon": addon, "eccezione": eccezione,
                    "ora": time.strftime("%H:%M:%S"), "estratto": [eccezione]}
        return None
    addon = trova_addon(testo)
    dal_lettore = bool(errori.PLAYER_RE.search(pulito))
    if not tutti and not (addon and addon.startswith("plugin.")) and not dal_lettore:
        return None
    esito["addon"] = addon
    esito["ora"] = time.strftime("%H:%M:%S")
    esito["estratto"] = _estratto(righe, esito.pop("frammento", ""))
    return esito


CAUSE_DA_VERIFICARE = ("cloudflare", "vietato", "timeout", "rifiutata", "reset", "errore_server",
                       "non_trovato", "troppe_richieste", "certificato", "bloccato_legale", "apertura_flusso")


def completa(ev, classifica=rete.classifica_dominio, prova=rete.prova_url, certificato=rete.diagnosi_certificato):
    """Controlla davvero com'e il sito adesso: per il DNS e per gli errori di collegamento."""
    host = ev.get("host")
    if not host:
        return ev
    if ev["causa"] == "dns" and not rete.e_indirizzo_ip(host):
        dominio = classifica(host)
        if dominio["stato"] == "inesistente":
            stato, titolo, spiegazione, soluzione = testi.ESITI_URL["dominio_inesistente"]
            ev.update(causa="dominio_inesistente", stato=stato, titolo=titolo,
                      spiegazione=spiegazione, soluzione=soluzione)
        elif dominio["stato"] == "ok":
            ev.update(stato="avviso", titolo="Problema di DNS passeggero",
                      spiegazione="Poco fa il nome %s non veniva tradotto, adesso sì." % host,
                      soluzione="Riprova: se succede spesso, cambia i DNS.")
            _verifica_sito(ev, host, prova)
        elif dominio["stato"] == "filtrato":
            ev["spiegazione"] += " Confermato: un DNS pubblico conosce questo sito, quindi lo blocca il tuo DNS."
        return ev
    if ev["causa"] == "certificato":
        try:
            motivo = certificato(host)
        except Exception:
            motivo = None
        if motivo in ("dns_filtrato", "certificato_sito"):
            stato, titolo, spiegazione, soluzione = testi.ESITI_URL[motivo]
            ev.update(causa=motivo, stato=stato, titolo=titolo, soluzione=soluzione,
                      spiegazione="Ho provato la connessione sicura a %s. %s" % (
                          host, "Con l'indirizzo vero del sito il certificato è valido, con il tuo DNS no: "
                                "il tuo DNS ti manda su un altro server. " + spiegazione
                          if motivo == "dns_filtrato" else spiegazione))
            return ev
    if ev["causa"] in CAUSE_DA_VERIFICARE:
        _verifica_sito(ev, host, prova)
    return ev


def _verifica_sito(ev, host, prova):
    """Apre davvero la pagina principale e corregge la diagnosi in base alla risposta."""
    try:
        esito = prova("https://%s/" % host)
    except Exception:
        return
    nome = esito.get("esito")
    if nome in ("dns_filtrato", "dominio_inesistente", "cloudflare") and nome in testi.ESITI_URL:
        stato, titolo, spiegazione, soluzione = testi.ESITI_URL[nome]
        ev.update(causa=nome, stato=stato, titolo=titolo,
                  spiegazione="Ho provato ad aprire %s adesso. %s" % (host, spiegazione), soluzione=soluzione)
    elif nome in ("ok", "pagina_html"):
        extra = " Il sito è dietro Cloudflare ma in questo momento ti lascia passare." if esito.get("cloudflare") else ""
        ev["spiegazione"] += (" Ho provato ad aprire la pagina principale di %s adesso e risponde: "
                              "il sito è raggiungibile, quindi il problema può essere passeggero oppure "
                              "riguardare solo quel link.%s" % (host, extra))
    elif nome in ("timeout", "rifiutata", "reset", "errore_server"):
        ev["spiegazione"] += " Ho riprovato adesso: anche %s non risponde, quindi il sito è giù o irraggiungibile." % host


def messaggio_notifica(ev, nome_addon=None):
    chi = nome_addon or ev.get("addon") or "Riproduzione"
    testo = "%s: %s" % (chi, ev["titolo"])
    if ev.get("host"):
        testo += " (%s)" % ev["host"]
    return testo + ". Apri Kodi Doctor, Problemi rilevati."


class Antispam:
    """Lo stesso problema non si ripete, e due avvisi non si accavallano."""

    def __init__(self, pausa_globale=15, pausa_evento=300, orologio=time.time):
        self._globale, self._evento, self._orologio = pausa_globale, pausa_evento, orologio
        self._ultimo_avviso = None
        self._visti = {}

    def nuovo(self, ev):
        ora = self._orologio()
        chiave = (ev.get("addon"), ev["causa"], ev.get("host") or ev.get("eccezione"))
        prima = self._visti.get(chiave)
        if prima is not None and ora - prima < self._evento:
            return False
        self._visti[chiave] = ora
        return True

    def puo_avvisare(self):
        ora = self._orologio()
        if self._ultimo_avviso is not None and ora - self._ultimo_avviso < self._globale:
            return False
        self._ultimo_avviso = ora
        return True


def carica(percorso):
    try:
        with open(percorso, encoding="utf-8") as f:
            dati = json.load(f)
        return dati if isinstance(dati, list) else []
    except (OSError, ValueError):
        return []


def trova_evento(percorso, id_evento=None):
    """L'evento con questo id, oppure il piu recente."""
    elenco = carica(percorso)
    for ev in elenco:
        if str(ev.get("id")) == str(id_evento):
            return ev
    return elenco[0] if elenco else None


def host_recenti(percorso, massimo=5):
    """Siti che hanno dato errore di recente: la diagnosi li controlla sempre."""
    visti = []
    for ev in carica(percorso):
        h = ev.get("host")
        if h and h not in visti and not rete.e_indirizzo_ip(h):
            visti.append(h)
    return visti[:massimo]


def aggiungi(percorso, ev):
    ev.setdefault("id", int(time.time() * 1000))
    dati = [ev] + carica(percorso)
    try:
        os.makedirs(os.path.dirname(percorso), exist_ok=True)
        with open(percorso, "w", encoding="utf-8") as f:
            json.dump(dati[:MAX_STORICO], f, ensure_ascii=False)
    except OSError:
        pass


def svuota(percorso):
    try:
        os.remove(percorso)
    except OSError:
        pass
