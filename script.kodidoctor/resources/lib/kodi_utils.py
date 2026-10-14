# -*- coding: utf-8 -*-
"""Tutto quello che tocca Kodi sta qui, il resto del codice resta indipendente."""

import json
import re

import xbmc
import xbmcaddon
import xbmcgui

# (id, nome, a cosa serve, indispensabile)
DIPENDENZE = (
    ("inputstream.adaptive", "InputStream Adaptive", "serve per i flussi DASH, HLS e protetti", True),
    ("inputstream.ffmpegdirect", "InputStream FFmpeg Direct", "serve per alcuni flussi in diretta", False),
    ("script.module.resolveurl", "ResolveURL", "serve per molti siti di video", False),
    ("pvr.iptvsimple", "PVR IPTV Simple Client", "serve per liste IPTV e playlist m3u", False),
)


def versione_kodi():
    return xbmc.getInfoLabel("System.BuildVersion") or "sconosciuta"


def piattaforma():
    for condizione, nome in (("system.platform.android", "Android"),
                             ("system.platform.windows", "Windows"),
                             ("system.platform.osx", "macOS"),
                             ("system.platform.ios", "iOS"),
                             ("system.platform.linux", "Linux")):
        if xbmc.getCondVisibility(condizione):
            return nome
    return "sconosciuta"


def dns_in_uso():
    """DNS letti da Kodi. Su alcuni dispositivi restituisce testo tipo 'Attendi': in quel caso vuoto."""
    risultato = []
    for etichetta in ("Network.DNS1Address", "Network.DNS2Address"):
        valore = (xbmc.getInfoLabel(etichetta) or "").strip()
        if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", valore) and valore != "0.0.0.0":
            risultato.append(valore)
    return risultato


def notifica(messaggio, durata=9000, avviso=True):
    """Notifica con il logo di Kodi Doctor al posto dell'icona standard."""
    addon = xbmcaddon.Addon()
    icona = addon.getAddonInfo("icon") or (xbmcgui.NOTIFICATION_WARNING if avviso else xbmcgui.NOTIFICATION_INFO)
    xbmcgui.Dialog().notification(addon.getAddonInfo("name"), messaggio, icona, durata)


def jsonrpc(metodo, parametri=None):
    richiesta = {"jsonrpc": "2.0", "id": 1, "method": metodo}
    if parametri is not None:
        richiesta["params"] = parametri
    try:
        return json.loads(xbmc.executeJSONRPC(json.dumps(richiesta)))
    except (ValueError, TypeError):
        return {}


def stato_addon(id_addon):
    """None se non installato, altrimenti dict con enabled e version."""
    r = jsonrpc("Addons.GetAddonDetails", {"addonid": id_addon, "properties": ["enabled", "version"]})
    if "error" in r or "result" not in r:
        return None
    return r["result"].get("addon")


def abilita_addon(id_addon):
    jsonrpc("Addons.SetAddonEnabled", {"addonid": id_addon, "enabled": True})


def installa_addon(id_addon):
    xbmc.executebuiltin("InstallAddon(%s)" % id_addon)
