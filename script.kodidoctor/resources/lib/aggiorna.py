# -*- coding: utf-8 -*-
"""Aggiornamento dell'addon da GitHub: controlla l'ultimo commit, scarica, verifica, applica.

Niente di Kodi in questo file, cosi si puo provare da solo. Il pacchetto nuovo viene controllato
(id dell'addon, file indispensabili, sintassi di ogni file Python) prima di toccare quello installato,
e se qualcosa va storto si torna alla copia di sicurezza.
"""

import json
import os
import re
import shutil
import tempfile
import time
import zipfile
from urllib.parse import quote
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

UA = "KodiDoctor-Updater"
REPO_PREDEFINITO = "aandroide/Kodidoctor"
RAMO_PREDEFINITO = "master"
MAX_ZIP = 25 * 1024 * 1024
MAX_FILE_ZIP = 2000
MAX_CRONOLOGIA = 10
IGNORA = {".git", ".github", ".gitignore", ".gitattributes", "__pycache__", "tests"}
INDISPENSABILI = ("addon.xml", "default.py", "service.py")
RE_REPO = re.compile(r"^[A-Za-z0-9_.\-]+/[A-Za-z0-9_.\-]+$")
RE_RAMO = re.compile(r"^[A-Za-z0-9_./\-]+$")


def repo_valido(repo, ramo):
    return bool(RE_REPO.match(repo or "")) and bool(RE_RAMO.match(ramo or "")) and ".." not in (ramo or "")


def commit_da_json(d):
    sha = d["sha"]
    c = d.get("commit", {})
    return {"sha": sha, "corto": sha[:7],
            "messaggio": (c.get("message") or "").strip().split("\n")[0][:200],
            "data": (c.get("committer") or c.get("author") or {}).get("date", "")}


def novita_da_json(d):
    """Cosa e cambiato tra due commit: messaggi e file."""
    messaggi = []
    for x in d.get("commits", []):
        riga = ((x.get("commit") or {}).get("message") or "").strip().split("\n")[0][:200]
        if riga:
            messaggi.append(riga)
    file = [(f.get("status", "modified"), f.get("filename", "")) for f in d.get("files", []) if f.get("filename")]
    return {"messaggi": messaggi[-20:], "file": file[:40], "totale_commit": d.get("total_commits", len(messaggi)),
            "totale_file": len(d.get("files", []))}


RE_SHA = re.compile(r"\b([0-9a-f]{40})\b")


def commit_da_feed(testo):
    """Elenco dei commit (dal piu recente) letti dal feed Atom di GitHub. Non ha il limite di richieste dell'API."""
    ns = {"a": "http://www.w3.org/2005/Atom"}
    lista = []
    for voce in ET.fromstring(testo).findall("a:entry", ns):
        cerca = (voce.findtext("a:id", "", ns) or "") + " " + " ".join(
            (l.get("href") or "") for l in voce.findall("a:link", ns))
        m = RE_SHA.search(cerca)
        if not m:
            continue
        titolo = " ".join((voce.findtext("a:title", "", ns) or "").split())[:200]
        lista.append({"sha": m.group(1), "corto": m.group(1)[:7], "messaggio": titolo,
                      "data": voce.findtext("a:updated", "", ns) or ""})
    return lista


class GitHub:
    def __init__(self, repo, ramo, timeout=15):
        if not repo_valido(repo, ramo):
            raise ValueError("repository o ramo non validi")
        self.repo, self.ramo, self.timeout = repo, ramo, timeout

    def _apri(self, url, timeout=None):
        richiesta = Request(url, headers={"User-Agent": UA, "Accept": "application/vnd.github+json"})
        return urlopen(richiesta, timeout=timeout or self.timeout)

    def _json(self, percorso):
        with self._apri("https://api.github.com/repos/%s/%s" % (self.repo, percorso)) as r:
            return json.loads(r.read().decode("utf-8"))

    def _feed(self):
        with self._apri("https://github.com/%s/commits/%s.atom" % (self.repo, quote(self.ramo, safe="/"))) as r:
            return commit_da_feed(r.read().decode("utf-8"))

    def ultimo_commit(self):
        try:
            return commit_da_json(self._json("commits/%s" % quote(self.ramo, safe="/")))
        except Exception as errore:
            # limite di richieste raggiunto o API non raggiungibile: provo con il feed dei commit
            try:
                lista = self._feed()
            except Exception:
                lista = []
            if lista:
                return lista[0]
            raise errore

    def confronto(self, base, testa):
        try:
            return novita_da_json(self._json("compare/%s...%s" % (base, testa)))
        except Exception:
            pass
        try:
            messaggi = []
            for c in self._feed():
                if c["sha"] == base:
                    break
                messaggi.append(c["messaggio"])
            if messaggi:
                return {"messaggi": list(reversed(messaggi))[-20:], "file": [], "totale_commit": len(messaggi),
                        "totale_file": 0}
        except Exception:
            pass
        return None

    def scarica_zip(self, sha, percorso):
        with self._apri("https://codeload.github.com/%s/zip/%s" % (self.repo, sha), 60) as r:
            totale = 0
            with open(percorso, "wb") as f:
                while True:
                    blocco = r.read(65536)
                    if not blocco:
                        break
                    totale += len(blocco)
                    if totale > MAX_ZIP:
                        raise ValueError("pacchetto troppo grande")
                    f.write(blocco)


def estrai(percorso_zip, cartella):
    base = os.path.realpath(cartella)
    with zipfile.ZipFile(percorso_zip) as z:
        nomi = z.namelist()
        if len(nomi) > MAX_FILE_ZIP:
            raise ValueError("pacchetto con troppi file")
        for nome in nomi:
            dest = os.path.realpath(os.path.join(cartella, nome))
            if dest != base and not dest.startswith(base + os.sep):
                raise ValueError("pacchetto non valido")
        z.extractall(cartella)


def trova_radice(cartella, id_addon):
    """La cartella che contiene l'addon.xml dell'addon cercato, e la sua versione."""
    base = os.path.abspath(cartella)
    for r, dirs, files in sorted(os.walk(base)):
        if r[len(base):].count(os.sep) > 3:
            dirs[:] = []
            continue
        if "addon.xml" in files:
            try:
                radice = ET.parse(os.path.join(r, "addon.xml")).getroot()
            except ET.ParseError:
                continue
            if radice.get("id") == id_addon:
                return r, radice.get("version")
    return None, None


def controlla_pacchetto(radice, id_addon):
    """(versione, errore). Errore None se il pacchetto e a posto."""
    for nome in INDISPENSABILI:
        if not os.path.isfile(os.path.join(radice, nome)):
            return None, "nel pacchetto manca %s" % nome
    try:
        e = ET.parse(os.path.join(radice, "addon.xml")).getroot()
    except ET.ParseError:
        return None, "addon.xml non valido"
    if e.get("id") != id_addon or not e.get("version"):
        return None, "il pacchetto non è questo addon"
    for rel in _file_relativi(radice):
        if rel.endswith(".py"):
            percorso = os.path.join(radice, rel)
            try:
                with open(percorso, encoding="utf-8") as f:
                    compile(f.read(), percorso, "exec")
            except (SyntaxError, ValueError, UnicodeDecodeError) as ex:
                return None, "errore nel file %s: %s" % (rel, ex)
    return e.get("version"), None


def _file_relativi(cartella):
    trovati = set()
    for r, dirs, files in os.walk(cartella):
        dirs[:] = [d for d in dirs if d not in IGNORA]
        for nome in files:
            if nome not in IGNORA:
                trovati.add(os.path.relpath(os.path.join(r, nome), cartella))
    return trovati


def sincronizza(origine, destinazione):
    """Rende la destinazione identica all'origine (file nuovi, cambiati e tolti)."""
    voluti = _file_relativi(origine)
    for rel in voluti:
        dest = os.path.join(destinazione, rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copyfile(os.path.join(origine, rel), dest)
    for rel in _file_relativi(destinazione) - voluti:
        os.remove(os.path.join(destinazione, rel))
    for r, dirs, files in os.walk(destinazione, topdown=False):
        if r != destinazione and not os.listdir(r):
            os.rmdir(r)


def identici(radice, destinazione):
    """True se i file dell'addon nel pacchetto sono gli stessi di quelli installati."""
    voluti, presenti = _file_relativi(radice), _file_relativi(destinazione)
    if voluti != presenti:
        return False
    for rel in voluti:
        with open(os.path.join(radice, rel), "rb") as a, open(os.path.join(destinazione, rel), "rb") as b:
            if a.read() != b.read():
                return False
    return True


def applica(radice, destinazione, backup):
    if os.path.isdir(backup):
        shutil.rmtree(backup)
    shutil.copytree(destinazione, backup, ignore=shutil.ignore_patterns("__pycache__"))
    try:
        sincronizza(radice, destinazione)
    except Exception:
        sincronizza(backup, destinazione)
        raise


# ---------- stato su disco ----------

def _file_stato(profilo):
    return os.path.join(profilo, "aggiornamento.json")


def carica_stato(profilo):
    try:
        with open(_file_stato(profilo), encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def salva_stato(profilo, stato):
    os.makedirs(profilo, exist_ok=True)
    with open(_file_stato(profilo), "w", encoding="utf-8") as f:
        json.dump(stato, f, ensure_ascii=False)


def _breve(e):
    t = str(e) or e.__class__.__name__
    return t[:160]


def aggiorna(gh, cartella_addon, profilo, id_addon, versione_locale, applica_aggiornamenti=True, orologio=time.time):
    """Esito: aggiornato, baseline, disponibile, aggiornato_ora o errore."""
    stato = carica_stato(profilo)
    try:
        ultimo = gh.ultimo_commit()
    except Exception as e:
        return {"esito": "errore", "errore": "Non riesco a contattare GitHub: %s" % _breve(e)}
    if stato.get("sha") == ultimo["sha"]:
        return {"esito": "aggiornato", "commit": ultimo, "versione": versione_locale}

    lavoro = tempfile.mkdtemp(prefix="kodidoctor_")
    try:
        pacchetto = os.path.join(lavoro, "pacchetto.zip")
        gh.scarica_zip(ultimo["sha"], pacchetto)
        estratto = os.path.join(lavoro, "x")
        os.makedirs(estratto)
        estrai(pacchetto, estratto)
        radice, _ = trova_radice(estratto, id_addon)
        if radice is None:
            return {"esito": "errore", "errore": "Il repository non contiene l'addon %s." % id_addon}
        nuova, errore = controlla_pacchetto(radice, id_addon)
        if errore:
            return {"esito": "errore", "errore": "Pacchetto scartato, %s." % errore}

        if not stato.get("sha") and nuova == versione_locale:
            # prima volta: l'addon installato e gia questa versione, mi segno il punto di partenza
            salva_stato(profilo, dict(stato, sha=ultimo["sha"], corto=ultimo["corto"], versione=nuova))
            return {"esito": "baseline", "commit": ultimo, "versione": nuova}
        if identici(radice, cartella_addon):
            # commit che non tocca l'addon (README, zip nel repository, ...): mi segno il punto e basta
            salva_stato(profilo, dict(stato, sha=ultimo["sha"], corto=ultimo["corto"], versione=nuova))
            return {"esito": "aggiornato", "commit": ultimo, "versione": nuova}
        if not applica_aggiornamenti:
            return {"esito": "disponibile", "commit": ultimo, "versione_vecchia": versione_locale,
                    "versione_nuova": nuova}

        novita = gh.confronto(stato["sha"], ultimo["sha"]) if stato.get("sha") else None
        if not novita or not novita["messaggi"]:
            novita = {"messaggi": [ultimo["messaggio"]] if ultimo["messaggio"] else [],
                      "file": (novita or {}).get("file", []), "totale_commit": 1,
                      "totale_file": (novita or {}).get("totale_file", 0)}
        applica(radice, cartella_addon, os.path.join(profilo, "backup_addon"))

        voce = {"sha": ultimo["sha"], "corto": ultimo["corto"], "data": ultimo["data"],
                "versione_vecchia": versione_locale, "versione_nuova": nuova,
                "messaggi": novita["messaggi"], "file": novita["file"],
                "totale_file": novita.get("totale_file", len(novita["file"])),
                "quando": time.strftime("%d/%m/%Y %H:%M", time.localtime(orologio()))}
        cronologia = [voce] + stato.get("cronologia", [])
        salva_stato(profilo, {"sha": ultimo["sha"], "corto": ultimo["corto"], "versione": nuova,
                              "da_mostrare": True, "cronologia": cronologia[:MAX_CRONOLOGIA]})
        return dict(voce, esito="aggiornato_ora", commit=ultimo)
    except Exception as e:
        return {"esito": "errore", "errore": "Aggiornamento non riuscito, resta la versione installata. (%s)" % _breve(e)}
    finally:
        shutil.rmtree(lavoro, ignore_errors=True)
