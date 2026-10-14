# -*- coding: utf-8 -*-
"""Trasforma i rilievi in testo leggibile (con colori Kodi) e in testo semplice per il file."""

import re
import time

COLORI = {"ok": "green", "info": "skyblue", "avviso": "orange", "errore": "red"}
ETICHETTE = {"ok": "OK", "info": "INFO", "avviso": "ATTENZIONE", "errore": "PROBLEMA"}
ORDINE = {"errore": 0, "avviso": 1, "info": 2, "ok": 3}


def riepilogo(rilievi):
    problemi = sum(1 for r in rilievi if r["stato"] == "errore")
    avvisi = sum(1 for r in rilievi if r["stato"] == "avviso")
    if problemi:
        return "Ho trovato %d %s e %d %s." % (problemi, "problema" if problemi == 1 else "problemi",
                                              avvisi, "avviso" if avvisi == 1 else "avvisi")
    if avvisi:
        return "Nessun problema grave, ma %d %s." % (avvisi, "avviso da guardare" if avvisi == 1 else "avvisi da guardare")
    return "Tutto in ordine."


def da_fare_per_primo(rilievi):
    for r in sorted(rilievi, key=lambda x: ORDINE[x["stato"]]):
        if r["stato"] in ("errore", "avviso") and r["soluzione"]:
            return r["soluzione"]
    return ""


def testo_report(rilievi, intestazione=()):
    """Testo con marcatori Kodi."""
    righe = ["[B]%s[/B]" % riepilogo(rilievi), ""]
    primo = da_fare_per_primo(rilievi)
    if primo:
        righe += ["[B]Cosa fare per prima cosa[/B]", primo, ""]
    for r in sorted(rilievi, key=lambda x: ORDINE[x["stato"]]):
        righe.append("[COLOR %s][B]%s[/B][/COLOR]  %s" % (COLORI[r["stato"]], ETICHETTE[r["stato"]], r["titolo"]))
        if r["dettaglio"]:
            righe.append("    " + r["dettaglio"])
        if r["soluzione"] and r["stato"] in ("errore", "avviso"):
            # il testo lungo compare una sola volta, in alto: qui basta il rimando
            if primo and r["soluzione"] == primo and len(primo) > 120:
                righe.append("    Cosa fare: come indicato in alto.")
            else:
                righe.append("    Cosa fare: " + r["soluzione"])
        righe.append("")
    if intestazione:
        righe += ["[B]Dispositivo[/B]"] + ["    " + i for i in intestazione]
    return "\n".join(righe)


def testo_evento(ev):
    """Dettaglio di un problema rilevato dal monitor del log."""
    righe = ["[COLOR %s][B]%s[/B][/COLOR]  %s" % (COLORI.get(ev["stato"], "orange"),
                                                  ETICHETTE.get(ev["stato"], "ATTENZIONE"), ev["titolo"]), ""]
    righe.append("Addon: %s%s" % (ev.get("nome") or ev.get("addon") or "non identificato",
                                  " (%s)" % ev["addon"] if ev.get("addon") and ev.get("nome") != ev.get("addon") else ""))
    righe.append("Ora: %s" % ev.get("ora", "?"))
    if ev.get("host"):
        righe.append("Sito: %s" % ev["host"])
    righe += ["", ev["spiegazione"]]
    if ev.get("soluzione"):
        righe += ["", "[B]Cosa fare[/B]", ev["soluzione"]]
    if ev.get("estratto"):
        righe += ["", "[B]Dal log[/B]"] + ["    " + r for r in ev["estratto"]]
    return "\n".join(righe)


def _data_breve(iso):
    try:
        return "%s/%s/%s" % (iso[8:10], iso[5:7], iso[0:4])
    except (TypeError, IndexError):
        return ""


def messaggio_aggiornamento(voce):
    """Testo corto per la notifica."""
    primo = (voce.get("messaggi") or [""])[-1]
    testo = "Aggiornato alla versione %s (commit %s)" % (voce["versione_nuova"], voce["corto"])
    return testo + (": " + primo[:90] if primo else ".")


STATI_FILE = {"added": "nuovo", "modified": "modificato", "removed": "rimosso", "renamed": "rinominato"}


def testo_aggiornamento(voce):
    """Dettaglio di un aggiornamento: versione, commit, cosa e cambiato."""
    righe = ["[B]Kodi Doctor aggiornato[/B]", ""]
    righe.append("Versione: da %s a %s" % (voce.get("versione_vecchia") or "?", voce["versione_nuova"]))
    data = _data_breve(voce.get("data"))
    righe.append("Commit: %s%s" % (voce["corto"], " del " + data if data else ""))
    if voce.get("quando"):
        righe.append("Installato il: %s" % voce["quando"])
    righe += ["", "[B]Cosa è stato aggiornato[/B]"]
    righe += ["    " + m for m in voce.get("messaggi", [])] or ["    Nessuna descrizione nel commit."]
    if voce.get("file"):
        righe += ["", "[B]File cambiati[/B]"]
        righe += ["    %s (%s)" % (nome, STATI_FILE.get(stato, stato)) for stato, nome in voce["file"]]
        resto = voce.get("totale_file", 0) - len(voce["file"])
        if resto > 0:
            righe.append("    e altri %d file" % resto)
    return "\n".join(righe)


def senza_marcatori(testo):
    return re.sub(r"\[/?(?:COLOR[^\]]*|B|I|CR)\]", "", testo)


def testo_file(rilievi, intestazione=()):
    """Versione semplice, da salvare e incollare dove serve chiedere aiuto."""
    return "Kodi Doctor, report del %s\n\n%s\n" % (
        time.strftime("%d/%m/%Y %H:%M"), senza_marcatori(testo_report(rilievi, intestazione)))
