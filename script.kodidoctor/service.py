# -*- coding: utf-8 -*-
"""Servizio in background di Kodi Doctor.

1. Legge kodi.log in diretta: quando un addon (MandraKodi, S4Me, altri) ha un errore, dice il motivo.
2. Quando una riproduzione fallisce, segnala il probabile motivo anche se il log non basta.
"""

import os
import threading
import time

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

from resources.lib import aggiorna_kodi, controlli, eventi, kodi_utils, logwatch, report

PAUSA_SECONDI = 120      # tra due avvisi del lettore video
PROP_AVVISO = "kodidoctor.ultimo_avviso"
LOG_KODI = "special://logpath/kodi.log"


def _domini_extra(addon):
    grezzo = addon.getSetting("domini_extra") or ""
    return [d.strip() for d in grezzo.replace(";", ",").split(",") if d.strip()]


def _percorso_eventi():
    profilo = xbmcvfs.translatePath(xbmcaddon.Addon().getAddonInfo("profile"))
    return os.path.join(profilo, "eventi.json")


def _nome_addon(id_addon):
    if not id_addon:
        return None
    try:
        return report.senza_marcatori(xbmcaddon.Addon(id_addon).getAddonInfo("name")) or id_addon
    except Exception:
        return id_addon


def _segna_avviso():
    xbmcgui.Window(10000).setProperty(PROP_AVVISO, str(int(time.time())))


class Osservatore:
    """Collega il lettore del log alla notifica."""

    def __init__(self):
        self._blocco_lock = threading.Lock()
        self._antispam = eventi.Antispam()
        self._watcher = None

    def attivo(self):
        return self._watcher is not None

    def avvia(self):
        percorso = xbmcvfs.translatePath(LOG_KODI)
        if not os.path.exists(percorso):
            xbmc.log("[Kodi Doctor] log non trovato: %s" % percorso, xbmc.LOGWARNING)
            return
        try:
            r = kodi_utils.jsonrpc("Addons.GetAddons", {"type": "xbmc.python.pluginsource", "enabled": True})
            for a in (r.get("result") or {}).get("addons", []):
                eventi.registra_plugin(a.get("addonid", ""))
        except Exception as e:
            xbmc.log("[Kodi Doctor] elenco plugin non letto: %s" % e, xbmc.LOGWARNING)
        self._watcher = logwatch.LogWatcher(percorso, self._su_blocco, eventi.interessante)
        self._watcher.avvia()
        xbmc.log("[Kodi Doctor] monitor del log attivo", xbmc.LOGINFO)

    def ferma(self):
        self._watcher = None

    def passo(self):
        if self._watcher:
            self._watcher.passo()

    def _su_blocco(self, testo):
        # l'analisi puo fare richieste di rete: fuori dal ciclo che legge il log
        threading.Thread(target=self._gestisci, args=(testo,), daemon=True).start()

    def _gestisci(self, testo):
        addon = xbmcaddon.Addon()
        ev = eventi.analizza_blocco(testo, addon.getSettingBool("monitor_tutti"))
        if ev is None:
            return
        with self._blocco_lock:
            if not self._antispam.nuovo(ev):
                return
        ev = eventi.completa(ev)
        ev["nome"] = _nome_addon(ev.get("addon")) or "Kodi"
        with self._blocco_lock:
            eventi.aggiungi(_percorso_eventi(), ev)
            avvisa = self._antispam.puo_avvisare()
        xbmc.log("[Kodi Doctor] %s: %s (%s)" % (ev["nome"], ev["titolo"], ev.get("host") or "-"), xbmc.LOGINFO)
        if avvisa:
            _segna_avviso()
            kodi_utils.notifica(eventi.messaggio_notifica(ev, ev["nome"]), 9000)
            if addon.getSettingBool("mostra_finestra"):
                self._chiedi_se_aprire(addon, ev)

    def _chiedi_se_aprire(self, addon, ev):
        """Finestra con la scelta di aprire subito il dettaglio. Si chiude da sola dopo 20 secondi."""
        try:
            testo = "%s\n%s" % (ev["titolo"], ev["spiegazione"][:220])
            if ev.get("host"):
                testo = "%s: %s\nSito: %s\n%s" % (ev["nome"], ev["titolo"], ev["host"], ev["spiegazione"][:200])
            apri = xbmcgui.Dialog().yesno(addon.getAddonInfo("name"), testo, nolabel="Chiudi", yeslabel="Apri Kodi Doctor",
                                          autoclose=20000)
            if apri:
                xbmc.executebuiltin("RunScript(script.kodidoctor,evento,%s)" % ev.get("id", ""))
        except Exception as e:
            xbmc.log("[Kodi Doctor] finestra non mostrata: %s" % e, xbmc.LOGWARNING)


def _analizza_riproduzione():
    addon = xbmcaddon.Addon()
    rilievi = controlli.diagnosi(completa=False, domini_extra=_domini_extra(addon), dns_kodi=kodi_utils.dns_in_uso())
    problemi = [r for r in rilievi if r["stato"] == "errore"]
    if problemi:
        messaggio = "Riproduzione non riuscita: %s. Apri Kodi Doctor per i dettagli." % problemi[0]["titolo"]
    else:
        messaggio = "Riproduzione non riuscita. La rete sembra a posto: apri Kodi Doctor per una diagnosi completa."
    xbmc.log("[Kodi Doctor] %s" % messaggio, xbmc.LOGINFO)
    kodi_utils.notifica(messaggio, 8000)


class Controllore(xbmc.Player):
    def __init__(self):
        super().__init__()
        self._ultimo = 0.0

    def onPlayBackError(self):
        if not xbmcaddon.Addon().getSettingBool("avviso_errore"):
            return
        ora = time.time()
        if ora - self._ultimo < PAUSA_SECONDI:
            return
        try:
            if ora - int(xbmcgui.Window(10000).getProperty(PROP_AVVISO) or 0) < 30:
                return  # il monitor del log ha appena avvisato: non ripeto
        except ValueError:
            pass
        self._ultimo = ora
        threading.Thread(target=_analizza_riproduzione, daemon=True).start()


if __name__ == "__main__":
    monitor = xbmc.Monitor()
    controllore = Controllore()
    osservatore = Osservatore()
    aggiornatore = aggiorna_kodi.Aggiornatore()
    tick = 0
    # dopo un aggiornamento: avviso e novita, senza fermare il resto del servizio
    threading.Timer(5, aggiorna_kodi.mostra_se_nuovo).start()
    while not monitor.abortRequested():
        if monitor.waitForAbort(1):
            break
        tick += 1
        if tick % 5 == 1:
            # l'impostazione si puo cambiare mentre Kodi e acceso
            voluto = xbmcaddon.Addon().getSettingBool("monitor_log")
            if voluto and not osservatore.attivo():
                osservatore.avvia()
            elif not voluto and osservatore.attivo():
                osservatore.ferma()
        osservatore.passo()
        aggiornatore.passo(lambda f: threading.Thread(target=f, daemon=True).start())
