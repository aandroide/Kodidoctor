# -*- coding: utf-8 -*-
"""Collega l'aggiornamento da GitHub a Kodi: impostazioni, notifiche, riavvio del servizio."""

import os
import time

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

from . import aggiorna, kodi_utils, report


def _percorsi():
    addon = xbmcaddon.Addon()
    cartella = xbmcvfs.translatePath(addon.getAddonInfo("path")).rstrip("/\\")
    profilo = xbmcvfs.translatePath(addon.getAddonInfo("profile")).rstrip("/\\")
    return addon, cartella, profilo


def _repository(addon):
    repo = (addon.getSetting("repo_github") or "").strip()
    ramo = (addon.getSetting("ramo_github") or "").strip()
    if not aggiorna.repo_valido(repo, ramo):
        repo, ramo = aggiorna.REPO_PREDEFINITO, aggiorna.RAMO_PREDEFINITO
    return repo, ramo


def esegui(crea_github=None, applica=True):
    """Controlla GitHub e, se c'e un commit nuovo, aggiorna l'addon. Restituisce l'esito."""
    addon, cartella, profilo = _percorsi()
    repo, ramo = _repository(addon)
    try:
        gh = (crea_github or aggiorna.GitHub)(repo, ramo)
    except ValueError as e:
        return {"esito": "errore", "errore": str(e)}
    esito = aggiorna.aggiorna(gh, cartella, profilo, addon.getAddonInfo("id"), addon.getAddonInfo("version"),
                              applica_aggiornamenti=applica)
    if esito["esito"] == "aggiornato_ora":
        xbmc.executebuiltin("UpdateLocalAddons")
    xbmc.log("[Kodi Doctor] aggiornamento: %s" % esito["esito"], xbmc.LOGINFO)
    return esito


def riavvia_servizio():
    """Spegne e riaccende l'addon: il servizio riparte con il codice nuovo. Va chiamato da uno script a parte."""
    id_addon = xbmcaddon.Addon().getAddonInfo("id")
    kodi_utils.jsonrpc("Addons.SetAddonEnabled", {"addonid": id_addon, "enabled": False})
    xbmc.sleep(1500)
    kodi_utils.jsonrpc("Addons.SetAddonEnabled", {"addonid": id_addon, "enabled": True})


def chiedi_riavvio():
    xbmc.executebuiltin("RunScript(%s,riavvia)" % xbmcaddon.Addon().getAddonInfo("id"))


def ultima_voce():
    _, _, profilo = _percorsi()
    cronologia = aggiorna.carica_stato(profilo).get("cronologia") or []
    return cronologia[0] if cronologia else None


def cronologia():
    _, _, profilo = _percorsi()
    return aggiorna.carica_stato(profilo).get("cronologia") or []


def mostra_se_nuovo():
    """Dopo un aggiornamento, al primo avvio del servizio nuovo: notifica e scelta di vedere le novità."""
    addon, _, profilo = _percorsi()
    stato = aggiorna.carica_stato(profilo)
    if not stato.get("da_mostrare") or not stato.get("cronologia"):
        return False
    stato["da_mostrare"] = False
    try:
        aggiorna.salva_stato(profilo, stato)
    except OSError:
        pass
    voce = stato["cronologia"][0]
    nome = addon.getAddonInfo("name")
    xbmcgui.Dialog().notification(nome, report.messaggio_aggiornamento(voce), xbmcgui.NOTIFICATION_INFO, 9000)
    try:
        if xbmcgui.Dialog().yesno(nome, "Aggiornato alla versione %s (commit %s).\nVuoi vedere cosa è cambiato?" % (
                voce["versione_nuova"], voce["corto"]), nolabel="Chiudi", yeslabel="Mostra", autoclose=20000):
            xbmcgui.Dialog().textviewer(nome, report.testo_aggiornamento(voce))
    except Exception as e:
        xbmc.log("[Kodi Doctor] novita non mostrate: %s" % e, xbmc.LOGWARNING)
    return True


class Aggiornatore:
    """Nel servizio: controlla GitHub poco dopo l'avvio e poi ogni sei ore."""
    PRIMO_CONTROLLO = 90
    INTERVALLO = 6 * 3600

    def __init__(self, crea_github=None, orologio=time.time):
        self._crea, self._orologio = crea_github, orologio
        self._prossimo = orologio() + self.PRIMO_CONTROLLO
        self._occupato = False

    def passo(self, lancia):
        """lancia(funzione): esegue il lavoro in un thread. Restituisce True se ha avviato un controllo."""
        ora = self._orologio()
        if self._occupato or ora < self._prossimo:
            return False
        self._prossimo = ora + self.INTERVALLO
        if not xbmcaddon.Addon().getSettingBool("aggiorna_auto"):
            return False
        self._occupato = True
        lancia(self._lavoro)
        return True

    def _lavoro(self):
        try:
            esito = esegui(self._crea)
            if esito["esito"] == "aggiornato_ora":
                xbmc.sleep(1000)
                chiedi_riavvio()
            elif esito["esito"] == "errore":
                xbmc.log("[Kodi Doctor] aggiornamento non riuscito: %s" % esito.get("errore"), xbmc.LOGWARNING)
        except Exception as e:
            xbmc.log("[Kodi Doctor] aggiornamento, errore imprevisto: %s" % e, xbmc.LOGWARNING)
        finally:
            self._occupato = False


# per comodita, il percorso del file di stato serve ai test
def file_stato():
    return os.path.join(_percorsi()[2], "aggiornamento.json")
