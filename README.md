# Kodi Doctor

Addon Kodi (`script.kodidoctor`) che spiega in italiano perché un flusso non parte: DNS, Cloudflare, certificati, componenti mancanti. Legge il log di Kodi mentre usi gli addon e avvisa quando trova un errore.

## Aggiornamento automatico

L'addon controlla questo repository (ramo `master`) e si aggiorna da solo quando c'è un commit nuovo. Il messaggio del commit viene mostrato all'utente come descrizione delle novità, quindi va scritto pensando a lui.

L'addon sta nella cartella `script.kodidoctor`. Ricordati di alzare `version` in `script.kodidoctor/addon.xml` a ogni modifica.
