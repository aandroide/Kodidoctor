# -*- coding: utf-8 -*-
"""I controlli veri e propri. Ognuno restituisce una lista di 'rilievi'.

Un rilievo e un dict: id, titolo, stato (ok, info, avviso, errore), dettaglio, soluzione.
"""

from . import rete, testi

SOGLIA_OROLOGIO = 300  # secondi di scarto oltre i quali l'orologio e considerato sbagliato


def rilievo(id_, titolo, stato, dettaglio="", soluzione=""):
    return {"id": id_, "titolo": titolo, "stato": stato, "dettaglio": dettaglio, "soluzione": soluzione}


def controlla_connessione():
    if rete.connessione_internet():
        return [rilievo("internet", "Connessione a internet", "ok", "Il dispositivo è collegato a internet.")]
    return [rilievo("internet", "Connessione a internet", "errore",
                    "Non riesco a collegarmi a internet.", testi.SOLUZIONE_RETE)]


def controlla_rete_pubblica():
    info = rete.info_pubblica()
    if info is None:
        return [rilievo("pubblica", "Rete pubblica", "avviso",
                        "Non sono riuscito a leggere l'indirizzo pubblico.", "")]
    trovati = []
    scarto = info.get("scarto_orologio")
    if info.get("certificati_ok") is False:
        trovati.append(rilievo("certificati", "Certificati di sicurezza", "errore",
                               "Le connessioni sicure vengono rifiutate.", testi.SOLUZIONE_ORARIO))
    if scarto is not None and abs(scarto) > SOGLIA_OROLOGIO:
        minuti = int(abs(scarto) // 60)
        trovati.append(rilievo("orologio", "Orologio del dispositivo", "errore",
                               "L'orologio è sbagliato di circa %d minuti." % minuti, testi.SOLUZIONE_ORARIO))
    elif scarto is not None:
        trovati.append(rilievo("orologio", "Orologio del dispositivo", "ok", "Data e ora sono corrette."))
    if info.get("ip"):
        warp = {"on": "attivo", "plus": "attivo (WARP Plus)", "off": "non attivo"}.get(info.get("warp"), "sconosciuto")
        dettaglio = "Esci su internet con l'indirizzo %s, paese %s, WARP %s." % (
            info["ip"], info.get("paese") or "?", warp)
        paese = info.get("paese")
        if paese and paese != "IT":
            trovati.append(rilievo("pubblica", "Rete pubblica", "avviso",
                                   dettaglio + " Alcuni siti italiani limitano l'accesso dall'estero: "
                                   "se usi una VPN o WARP, prova a spegnerla.", ""))
        else:
            trovati.append(rilievo("pubblica", "Rete pubblica", "info", dettaglio))
    return trovati


def controlla_dns(domini_extra=(), dns_kodi=()):
    """Confronta il DNS di sistema con un riferimento pubblico su alcuni domini."""
    trovati = []
    sistema, _ = rete.risolvi_sistema(rete.DOMINIO_CONTROLLO)
    dns_generale = bool(sistema)
    if dns_kodi:
        trovati.append(rilievo("dns_in_uso", "DNS in uso", "info", "Il dispositivo usa i DNS: " + ", ".join(dns_kodi) + "."))
    if not dns_generale:
        trovati.append(rilievo("dns_generale", "Funzionamento del DNS", "errore",
                               "Il DNS non traduce nemmeno i siti più comuni.", testi.SOLUZIONE_DNS))
        return trovati

    domini = list(rete.DOMINI_BASE) + [d for d in domini_extra if d and d not in rete.DOMINI_BASE]
    filtrati, incerti, inesistenti = [], [], []
    for d in domini:
        esito = rete.classifica_dominio(d)
        if esito["stato"] == "filtrato":
            filtrati.append(d)
        elif esito["stato"] == "indeterminato":
            incerti.append(d)
        elif esito["stato"] == "inesistente":
            inesistenti.append(d)
    if filtrati:
        trovati.append(rilievo("dns_filtrati", "Siti bloccati dal DNS", "errore",
                               "Il tuo DNS non li traduce o li porta su un server sbagliato, mentre un DNS pubblico li conosce bene: "
                               + ", ".join(filtrati) + ".", testi.SOLUZIONE_DNS))
    if incerti:
        trovati.append(rilievo("dns_incerti", "Siti non verificabili", "avviso",
                               "Non ho potuto confrontare questi siti con un DNS pubblico: " + ", ".join(incerti) + ".", ""))
    if inesistenti:
        trovati.append(rilievo("dns_inesistenti", "Siti che non esistono più", "avviso",
                               "Nessun DNS conosce questi nomi: " + ", ".join(inesistenti) + ".", ""))
    if not (filtrati or incerti or inesistenti):
        trovati.append(rilievo("dns_ok", "Traduzione dei nomi (DNS)", "ok",
                               "Il DNS traduce correttamente i %d siti controllati." % len(domini)))
    return trovati


def controlla_dipendenze(elenco, stato_addon):
    """elenco: tuple (id, nome, a cosa serve, indispensabile). stato_addon: funzione id -> dict o None."""
    trovati = []
    for id_addon, nome, scopo, indispensabile in elenco:
        s = stato_addon(id_addon)
        if s is None:
            stato = "errore" if indispensabile else "avviso"
            trovati.append(rilievo("dip_" + id_addon, nome, stato,
                                   "Non è installato: %s." % scopo,
                                   "Installalo dal menu Componenti mancanti di Kodi Doctor."))
        elif not s.get("enabled", True):
            trovati.append(rilievo("dip_" + id_addon, nome, "avviso",
                                   "È installato ma disattivato: %s." % scopo,
                                   "Attivalo dal menu Componenti mancanti di Kodi Doctor."))
        else:
            trovati.append(rilievo("dip_" + id_addon, nome, "ok", "Presente (versione %s)." % s.get("version", "?")))
    return trovati


def diagnosi(completa=True, domini_extra=(), dns_kodi=(), dipendenze=(), stato_addon=None, avanzamento=None):
    """Esegue i controlli in ordine. 'avanzamento' e una funzione (percentuale, messaggio)."""
    def passo(percentuale, messaggio):
        if avanzamento:
            avanzamento(percentuale, messaggio)

    passo(5, "Controllo la connessione")
    trovati = controlla_connessione()
    if trovati[0]["stato"] == "errore":
        return trovati  # senza internet gli altri controlli non hanno senso
    passo(25, "Leggo la rete pubblica e l'orologio")
    trovati += controlla_rete_pubblica()
    passo(50, "Controllo i DNS")
    trovati += controlla_dns(domini_extra, dns_kodi)
    if completa and dipendenze and stato_addon:
        passo(85, "Controllo i componenti")
        trovati += controlla_dipendenze(dipendenze, stato_addon)
    passo(100, "Fatto")
    return trovati
