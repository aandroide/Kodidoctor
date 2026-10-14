<p align="center">
  <img src="script.kodidoctor/icon.png" alt="Kodi Doctor" width="180">
</p>

# Kodi Doctor

Il medico di Kodi. Quando un link o uno streaming non parte, Kodi Doctor ti dice **perché**, in italiano semplice, e cosa fare per sistemarlo. Funziona con qualsiasi addon.

## Cosa fa

* **Legge il log mentre usi Kodi.** Quando un addon ha un errore, ti arriva una notifica e una finestra con il motivo. Un tasto apre subito il dettaglio.
* **Verifica davvero.** Non si limita a indovinare dal messaggio d'errore: apre il sito e controlla com'è adesso, così la diagnosi è confermata.
* **Riconosce i problemi più comuni:**
  * DNS bloccati dal provider, anche quando rispondono con un indirizzo falso
  * protezione Cloudflare
  * certificati non validi, con la differenza tra colpa del DNS e colpa del sito
  * siti spenti, link morti, accesso vietato, troppe richieste
  * componenti mancanti (per esempio InputStream Adaptive)
* **Tiene l'elenco dei problemi rilevati**, con spiegazione, cosa fare e le righe originali del log.
* **Si aggiorna da solo** da questo repository e ti dice quale versione è arrivata e cosa è cambiato.

## Installazione

1. Scarica lo zip dalla cartella [`repo`](repo): [script.kodidoctor-0.0.1.zip](https://github.com/aandroide/Kodidoctor/raw/master/repo/script.kodidoctor-0.0.1.zip)
2. In Kodi: Add-on, Installa da file zip, scegli il file.
3. Finito. Da ora in poi si aggiorna da solo.

Serve Kodi 19 o più recente. Provato su Kodi 21 per Android.

## Il menu

| Voce | A cosa serve |
| --- | --- |
| Diagnosi completa | Controlla internet, DNS, orologio e componenti, e dice cosa non va |
| Problemi rilevati | L'elenco degli errori trovati nel log |
| Solo rete e DNS | Il controllo veloce |
| Prova un indirizzo | Incolli un link e scopri perché non si apre |
| Componenti mancanti | Mostra e installa gli addon che servono |
| Ultimo report | Rilegge l'ultima diagnosi, utile per chiedere aiuto |
| Aggiornamenti | Cerca una versione nuova e mostra le novità |
| Impostazioni | Monitor del log, finestra, aggiornamenti |

## Impostazioni

* **Monitor del log** (acceso): legge kodi.log e segnala gli errori.
* **Controlla anche gli addon in background** (acceso): senza questa opzione vengono segnalati solo gli addon video e le riproduzioni fallite.
* **Mostra una finestra con il pulsante per aprire Kodi Doctor** (acceso).
* **Aggiorna Kodi Doctor da solo** (acceso): controlla GitHub ogni sei ore.
* **Domini extra**: siti che vuoi sempre controllare nel test DNS, separati da virgola.
* **Repository e ramo** (impostazioni avanzate): da dove arrivano gli aggiornamenti, utile se usi una copia tua.

## Dalla riga di comando di Kodi o da altri addon

```
RunScript(script.kodidoctor,diagnosi)
RunScript(script.kodidoctor,errore,TESTO DELL'ERRORE)
RunScript(script.kodidoctor,aggiorna)
```

`errore` analizza un messaggio e ne spiega la causa. Gli altri addon possono usarlo per mostrare all'utente un aiuto al posto di un errore generico.

## Cosa contatta, e cosa no

Kodi Doctor non invia nulla di tuo a nessuno e non ha server propri. Per le verifiche contatta solo:

* i DNS pubblici di Cloudflare (1.1.1.1) e Google (8.8.8.8), raggiunti per indirizzo IP, per confrontare cosa risponde il tuo DNS;
* il sito che stai controllando, quando gli chiedi di provarlo o quando il log segnala un errore su di lui;
* GitHub, per cercare e scaricare gli aggiornamenti.

Il log di Kodi viene letto solo in locale.

## Aggiornamenti automatici

L'addon controlla questo repository (ramo `master`) e, se c'è un commit nuovo che cambia l'addon, lo scarica, lo verifica (id, file indispensabili, sintassi di ogni file Python) e solo dopo sostituisce i file. Se qualcosa va storto resta la versione di prima. Un commit che non tocca l'addon, come una modifica al README, non provoca nessun avviso.

Il **messaggio del commit** viene mostrato all'utente come descrizione delle novità: va scritto pensando a lui.

### Per chi pubblica una versione

1. Modifica i file in `script.kodidoctor`.
2. Alza `version` in `script.kodidoctor/addon.xml` e aggiungi una riga in `news`.
3. Rigenera lo zip in `repo` (una sola cartella radice `script.kodidoctor`, senza `__pycache__`) e tieni solo l'ultimo.
4. Scrivi un messaggio di commit chiaro e invia.

## Licenza

GPL-3.0-or-later. Autore: Androide.
