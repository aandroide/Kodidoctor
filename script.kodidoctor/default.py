# -*- coding: utf-8 -*-
"""Kodi Doctor: menu principale e comandi da altri addon.

Uso da altri addon:
    RunScript(script.kodidoctor,diagnosi)
    RunScript(script.kodidoctor,errore,TESTO DELL'ERRORE)
    RunScript(script.kodidoctor,aggiorna)    apre il menu degli aggiornamenti
    RunScript(script.kodidoctor,evento,ID)   apre il dettaglio di un problema rilevato
"""

import os
import sys

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

from resources.lib import aggiorna_kodi, controlli, errori, eventi, kodi_utils, rete, report, testi

ADDON = xbmcaddon.Addon()
NOME = ADDON.getAddonInfo("name")


def _domini_extra():
    grezzo = ADDON.getSetting("domini_extra") or ""
    scelti = [d.strip() for d in grezzo.replace(";", ",").split(",") if d.strip()]
    try:
        recenti = eventi.host_recenti(_file_eventi())
    except Exception:
        recenti = []
    return scelti + [h for h in recenti if h not in scelti]


def _intestazione():
    return ["Kodi " + kodi_utils.versione_kodi(), "Sistema: " + kodi_utils.piattaforma()]


def _file_report():
    cartella = xbmcvfs.translatePath(ADDON.getAddonInfo("profile"))
    if not xbmcvfs.exists(cartella):
        xbmcvfs.mkdirs(cartella)
    return os.path.join(cartella, "ultimo_report.txt")


def _mostra(rilievi):
    """Mostra il report e lo salva su file."""
    testo = report.testo_report(rilievi, _intestazione())
    try:
        with open(_file_report(), "w", encoding="utf-8") as f:
            f.write(report.testo_file(rilievi, _intestazione()))
    except OSError as e:
        xbmc.log("[Kodi Doctor] report non salvato: %s" % e, xbmc.LOGWARNING)
    xbmcgui.Dialog().textviewer(NOME, testo)


def diagnosi_completa(completa=True):
    barra = xbmcgui.DialogProgress()
    barra.create(NOME, "Avvio")

    def avanzamento(percentuale, messaggio):
        barra.update(percentuale, messaggio)

    try:
        rilievi = controlli.diagnosi(
            completa=completa, domini_extra=_domini_extra(), dns_kodi=kodi_utils.dns_in_uso(),
            dipendenze=kodi_utils.DIPENDENZE, stato_addon=kodi_utils.stato_addon, avanzamento=avanzamento)
    finally:
        barra.close()
    _mostra(rilievi)


def prova_indirizzo():
    url = xbmcgui.Dialog().input("Incolla l'indirizzo che non parte", type=xbmcgui.INPUT_ALPHANUM)
    if not url:
        return
    barra = xbmcgui.DialogProgress()
    barra.create(NOME, "Provo l'indirizzo")
    try:
        esito = rete.prova_url(url)
    finally:
        barra.close()
    stato, titolo, spiegazione, soluzione = testi.ESITI_URL.get(esito["esito"], testi.ESITI_URL["altro"])
    dettaglio = spiegazione
    if esito.get("codice"):
        dettaglio += " Codice di risposta: %s." % esito["codice"]
    _mostra([controlli.rilievo("url", titolo, stato, dettaglio, soluzione)])


def componenti_mancanti():
    da_sistemare = []
    for id_addon, nome, scopo, _ in kodi_utils.DIPENDENZE:
        s = kodi_utils.stato_addon(id_addon)
        if s is None:
            da_sistemare.append((id_addon, nome, "da installare"))
        elif not s.get("enabled", True):
            da_sistemare.append((id_addon, nome, "da attivare"))
    if not da_sistemare:
        xbmcgui.Dialog().ok(NOME, "Tutti i componenti sono presenti e attivi.")
        return
    elenco = "\n".join("%s (%s)" % (nome, cosa) for _, nome, cosa in da_sistemare)
    if not xbmcgui.Dialog().yesno(NOME, "Questi componenti mancano:\n\n%s\n\nVuoi sistemarli adesso?" % elenco):
        return
    for id_addon, _, cosa in da_sistemare:
        if cosa == "da attivare":
            kodi_utils.abilita_addon(id_addon)
        else:
            xbmc.executebuiltin("InstallAddon(%s)" % id_addon, True)


def ultimo_report():
    percorso = _file_report()
    if not xbmcvfs.exists(percorso):
        xbmcgui.Dialog().ok(NOME, "Non c'è ancora nessun report. Lancia prima una diagnosi.")
        return
    with open(percorso, encoding="utf-8") as f:
        xbmcgui.Dialog().textviewer(NOME, f.read())


def guida():
    xbmcgui.Dialog().textviewer(NOME, testi.GUIDA)


def _file_eventi():
    return os.path.join(xbmcvfs.translatePath(ADDON.getAddonInfo("profile")), "eventi.json")


def problemi_rilevati():
    """Elenco dei problemi segnalati dal monitor del log, dal piu recente."""
    while True:
        elenco = eventi.carica(_file_eventi())
        if not elenco:
            xbmcgui.Dialog().ok(NOME, "Nessun problema rilevato finora. Il monitor del log segnala qui gli errori "
                                      "degli addon appena succedono.")
            return
        voci = ["%s  %s: %s" % (e.get("ora", "?"), e.get("nome") or e.get("addon") or "Kodi", e["titolo"])
                for e in elenco]
        voci.append("Svuota l'elenco")
        scelta = xbmcgui.Dialog().select("Problemi rilevati", voci)
        if scelta < 0:
            return
        if scelta == len(elenco):
            eventi.svuota(_file_eventi())
            return
        xbmcgui.Dialog().textviewer(NOME, report.testo_evento(elenco[scelta]))


def apri_evento(id_evento=None):
    """Apre il dettaglio del problema segnalato (quello con questo id, o l'ultimo)."""
    ev = eventi.trova_evento(_file_eventi(), id_evento)
    if ev is None:
        problemi_rilevati()
        return
    xbmcgui.Dialog().textviewer(NOME, report.testo_evento(ev))


def _versione_corrente():
    return "Versione installata: %s" % ADDON.getAddonInfo("version")


def aggiornamenti():
    """Cerca e applica gli aggiornamenti da GitHub, e mostra cosa e cambiato."""
    while True:
        scelte = ["Cerca aggiornamenti adesso", "Novità dell'ultimo aggiornamento", "Cronologia degli aggiornamenti"]
        scelta = xbmcgui.Dialog().select("%s. %s" % (NOME, _versione_corrente()), scelte)
        if scelta < 0:
            return
        if scelta == 0:
            barra = xbmcgui.DialogProgress()
            barra.create(NOME, "Controllo GitHub")
            try:
                esito = aggiorna_kodi.esegui()
            finally:
                barra.close()
            if esito["esito"] == "aggiornato_ora":
                xbmcgui.Dialog().textviewer(NOME, report.testo_aggiornamento(esito))
                aggiorna_kodi.chiedi_riavvio()
                xbmcgui.Dialog().ok(NOME, "Aggiornamento installato. Il servizio si riavvia da solo: chiudi e riapri "
                                          "Kodi Doctor per usare la versione nuova.")
                return
            if esito["esito"] in ("aggiornato", "baseline"):
                c = esito["commit"]
                xbmcgui.Dialog().ok(NOME, "Kodi Doctor è già aggiornato.\nVersione %s, commit %s." % (
                    esito.get("versione", ADDON.getAddonInfo("version")), c["corto"]))
            else:
                xbmcgui.Dialog().ok(NOME, esito.get("errore", "Controllo non riuscito."))
        elif scelta == 1:
            voce = aggiorna_kodi.ultima_voce()
            if voce is None:
                xbmcgui.Dialog().ok(NOME, "Nessun aggiornamento installato finora.")
            else:
                xbmcgui.Dialog().textviewer(NOME, report.testo_aggiornamento(voce))
        else:
            elenco = aggiorna_kodi.cronologia()
            if not elenco:
                xbmcgui.Dialog().ok(NOME, "Nessun aggiornamento installato finora.")
                continue
            voci = ["%s  versione %s (commit %s)" % (v.get("quando", ""), v["versione_nuova"], v["corto"]) for v in elenco]
            quale = xbmcgui.Dialog().select("Cronologia degli aggiornamenti", voci)
            if quale >= 0:
                xbmcgui.Dialog().textviewer(NOME, report.testo_aggiornamento(elenco[quale]))


def da_errore(testo):
    """Chiamato da altri addon con il testo di un errore."""
    esito = errori.interpreta_errore(testo)
    if esito is None:
        xbmcgui.Dialog().ok(NOME, "Non riconosco questo errore. Prova la diagnosi completa dal menu.")
        return
    dettaglio = esito["spiegazione"]
    if esito["host"]:
        dettaglio += " Sito coinvolto: %s." % esito["host"]
    rilievi = [controlli.rilievo("errore", esito["titolo"], esito["stato"], dettaglio, esito["soluzione"])]
    if esito["causa"] == "dns" and esito["host"] and not rete.e_indirizzo_ip(esito["host"]):
        dominio = rete.classifica_dominio(esito["host"])
        if dominio["stato"] == "inesistente":
            rilievi.append(controlli.rilievo("dominio", "Il sito non esiste più", "avviso",
                                             "Nessun DNS pubblico conosce %s: il dominio è chiuso o cambiato." % esito["host"],
                                             testi.SOLUZIONE_LINK_MORTO))
    _mostra(rilievi)


VOCI = (
    ("Diagnosi completa", diagnosi_completa),
    ("Problemi rilevati", problemi_rilevati),
    ("Solo rete e DNS", lambda: diagnosi_completa(False)),
    ("Prova un indirizzo", prova_indirizzo),
    ("Componenti mancanti", componenti_mancanti),
    ("Ultimo report", ultimo_report),
    ("Come funziona", guida),
    ("Aggiornamenti", aggiornamenti),
    ("Impostazioni", ADDON.openSettings),
)


# icona e breve spiegazione di ogni voce del menu
DETTAGLI = {
    "Diagnosi completa": ("diagnosi.png", "Controlla rete, DNS, orologio e componenti"),
    "Problemi rilevati": ("problemi.png", "Gli errori trovati nel log mentre usi gli addon"),
    "Solo rete e DNS": ("rete.png", "Controllo veloce di connessione e DNS"),
    "Prova un indirizzo": ("indirizzo.png", "Scopri perché un link non si apre"),
    "Componenti mancanti": ("componenti.png", "Installa o attiva quello che serve"),
    "Ultimo report": ("report.png", "Rileggi l'ultima diagnosi"),
    "Come funziona": ("funziona.png", "Cosa fa Kodi Doctor e come usarlo"),
    "Aggiornamenti": ("aggiornamenti.png", "Aggiorna Kodi Doctor da GitHub e leggi le novità"),
    "Impostazioni": ("impostazioni.png", "Monitor del log, avvisi e domini extra"),
}


def _elenco_voci():
    """Voci con icona e descrizione. Se qualcosa non va, torna all'elenco semplice."""
    try:
        cartella = os.path.join(xbmcvfs.translatePath(ADDON.getAddonInfo("path")), "resources", "media")
        voci = []
        for nome, _ in VOCI:
            icona, descrizione = DETTAGLI.get(nome, ("", ""))
            voce = xbmcgui.ListItem(nome, descrizione)
            if icona:
                percorso = os.path.join(cartella, icona)
                voce.setArt({"icon": percorso, "thumb": percorso})
            voci.append(voce)
        return voci, True
    except Exception as e:
        xbmc.log("[Kodi Doctor] menu senza icone: %s" % e, xbmc.LOGWARNING)
        return [nome for nome, _ in VOCI], False


def menu():
    while True:
        voci, con_dettagli = _elenco_voci()
        if con_dettagli:
            scelta = xbmcgui.Dialog().select(NOME, voci, useDetails=True)
        else:
            scelta = xbmcgui.Dialog().select(NOME, voci)
        if scelta < 0:
            return
        VOCI[scelta][1]()


def main(argomenti):
    if not argomenti:
        menu()
    elif argomenti[0] == "diagnosi":
        diagnosi_completa()
    elif argomenti[0] == "riavvia":
        aggiorna_kodi.riavvia_servizio()
    elif argomenti[0] == "aggiorna":
        aggiornamenti()
    elif argomenti[0] == "evento":
        apri_evento(argomenti[1] if len(argomenti) > 1 else None)
    elif argomenti[0] == "errore":
        # RunScript separa gli argomenti sulle virgole: li riunisco
        da_errore(", ".join(argomenti[1:]))
    else:
        menu()


if __name__ == "__main__":
    main(sys.argv[1:])
