# -*- coding: utf-8 -*-
"""Testi mostrati all'utente. Italiano semplice, senza gergo."""

SOLUZIONE_DNS = (
    "I DNS del tuo provider bloccano questo sito. Servono i DNS di Cloudflare oppure di OpenDNS.\n"
    "Rete fissa (Wi-Fi di casa): impostali sul router, se il tuo operatore lo permette. "
    "Cloudflare 1.1.1.1 e 1.0.0.1, oppure OpenDNS 208.67.222.222 e 208.67.220.220. "
    "Con alcuni operatori (per esempio TIM, Edison, Sky Wifi ed Eolo) il router non li accetta: "
    "allora vanno impostati sul dispositivo (Android, Android TV o Firestick, con IP statico o con "
    "un'app come DNS Changer) oppure su un router tuo.\n"
    "Rete mobile (dati del telefono): nelle impostazioni di Android apri DNS privato e scrivi "
    "1dot1dot1dot1.cloudflare-dns.com oppure dns.opendns.com.\n"
    "Per controllare: vai su dnsleaktest.com, scegli Extended test e verifica che compaia il nome "
    "dei DNS che hai scelto al posto del tuo provider. Poi riavvia Kodi.")

SOLUZIONE_ORARIO = (
    "Imposta data e ora in modo automatico nelle impostazioni del dispositivo. "
    "Con l'orologio sbagliato i siti sicuri vengono rifiutati e molti flussi non partono.")

SOLUZIONE_CLOUDFLARE = (
    "Il sito è protetto da Cloudflare e ti blocca. Prova ad attivare WARP (l'app gratuita di "
    "Cloudflare) oppure una VPN, poi riprova. Se continua, il sito potrebbe richiedere un browser vero.")

SOLUZIONE_TIMEOUT = (
    "Il server non risponde in tempo. Riprova tra qualche minuto, controlla di essere "
    "collegato bene alla rete e prova anche con un altro sito per capire se il problema è solo qui.")

SOLUZIONE_CERTIFICATO = (
    "Il certificato di sicurezza non è stato accettato. Se il sito è bloccato dal provider, di solito "
    "è colpa dei DNS: il blocco ti manda su un server sbagliato e il certificato non corrisponde. "
    "Prova a cambiare i DNS (Cloudflare oppure OpenDNS). Se i DNS sono già cambiati, controlla data e ora del "
    "dispositivo e riprova.")

SOLUZIONE_LINK_MORTO = (
    "Il link non esiste più. Prova un'altra voce della lista, oppure aggiorna la lista o l'addon.")

SOLUZIONE_BLOCCO_LEGALE = (
    "Il sito risulta non disponibile per motivi legali nel tuo paese. Non è un guasto di Kodi.")

SOLUZIONE_SERVER = (
    "Il guasto è sul server del sito, non da te. Riprova più tardi o scegli un'altra fonte.")

SOLUZIONE_RETE = (
    "Controlla il collegamento WiFi o cavo e il router. Se altri dispositivi navigano, "
    "riavvia il dispositivo con Kodi.")

# Spiegazioni per gli esiti di prova_url: (stato, titolo, spiegazione, soluzione)
ESITI_URL = {
    "url_non_valido": ("errore", "Indirizzo non valido",
                       "Deve iniziare con http:// oppure https:// e contenere il nome del sito.", ""),
    "dns_filtrato": ("errore", "DNS filtrato",
                     "Il nome del sito non viene tradotto dal DNS che stai usando, mentre un DNS "
                     "pubblico lo conosce. Di solito è un blocco del provider.", SOLUZIONE_DNS),
    "cloudflare_app": ("errore", "Cloudflare: protezione non superata",
                       "Il sito è protetto da Cloudflare e l'addon non è riuscito a superare la protezione, "
                       "quindi la pagina non si apre.",
                       "Riprova tra qualche minuto. Se succede sempre, il sito potrebbe aver rafforzato la "
                       "protezione: prova un altro link o un'altra fonte e controlla che l'addon sia aggiornato."),
    "certificato_sito": ("errore", "Certificato del sito non valido",
                         "Il sito presenta un certificato scaduto o non valido, anche usando un DNS pubblico: "
                         "il problema è del sito, non del tuo dispositivo.",
                         "Aspetta che il gestore del sito lo sistemi oppure usa un altro link o un'altra fonte."),
    "dominio_inesistente": ("errore", "Il sito non esiste più",
                            "Nessun DNS conosce questo nome. Il dominio è stato chiuso o cambiato.",
                            SOLUZIONE_LINK_MORTO),
    "dns": ("errore", "Nome del sito non risolto",
            "Il dispositivo non riesce a trovare il sito.", SOLUZIONE_DNS),
    "certificato": ("errore", "Certificato non accettato",
                    "La connessione sicura al sito è stata rifiutata. Spesso succede quando il DNS del provider "
                    "blocca il sito, più raramente per l'orologio sbagliato.", SOLUZIONE_CERTIFICATO),
    "timeout": ("avviso", "Nessuna risposta in tempo",
                "Il sito è lento o irraggiungibile.", SOLUZIONE_TIMEOUT),
    "rifiutata": ("errore", "Connessione rifiutata",
                  "Il server ha chiuso la porta: può essere spento o bloccare il tuo accesso.",
                  SOLUZIONE_TIMEOUT),
    "reset": ("avviso", "Connessione interrotta",
              "Il server ha chiuso la connessione a metà. Può essere un blocco o un guasto.",
              SOLUZIONE_CLOUDFLARE),
    "cloudflare": ("errore", "Bloccato da Cloudflare",
                   "Il sito ha risposto con la protezione anti bot di Cloudflare.",
                   SOLUZIONE_CLOUDFLARE),
    "vietato": ("errore", "Accesso vietato (403)",
                "Il server ti rifiuta. Può bloccare il tuo paese, la tua rete o il programma usato.",
                SOLUZIONE_CLOUDFLARE),
    "autenticazione": ("avviso", "Serve un accesso (401)",
                       "Il link richiede nome utente e password o un token valido.", ""),
    "non_trovato": ("errore", "Link non trovato (404)",
                    "Il sito risponde ma questo indirizzo non esiste più.", SOLUZIONE_LINK_MORTO),
    "troppe_richieste": ("avviso", "Troppe richieste (429)",
                         "Il sito ti ha limitato perché hai fatto troppi tentativi. Aspetta qualche minuto.", ""),
    "bloccato_legale": ("errore", "Non disponibile per motivi legali (451)",
                        "Il sito è oscurato nel tuo paese.", SOLUZIONE_BLOCCO_LEGALE),
    "errore_server": ("errore", "Il server ha un guasto",
                      "Il sito risponde con un errore interno.", SOLUZIONE_SERVER),
    "pagina_html": ("avviso", "Il link dà una pagina web, non un video",
                    "L'indirizzo risponde ma contiene una pagina, non un flusso. "
                    "L'addon deve prima estrarre il vero indirizzo del video.", ""),
    "ok": ("ok", "Il link risponde",
           "Il server risponde bene. Se il video non parte, il problema è il formato o un "
           "componente mancante: controlla le dipendenze.", ""),
    "modulo_mancante": ("errore", "Manca un componente dell'addon",
                        "L'addon cerca un modulo Python che non è installato o non è compatibile.",
                        "Reinstalla l'addon oppure installa il componente che manca (di solito uno script.module). "
                        "Dal menu Componenti mancanti puoi sistemare quelli più comuni."),
    "apertura_flusso": ("errore", "Il lettore non riesce ad aprire il flusso",
                        "Kodi ha provato ad aprire il video ma non ci è riuscito. Il link può essere "
                        "scaduto, il sito può bloccarti oppure può mancare un componente di lettura.",
                        "Riprova da capo con un'altra voce. Se hai il link usa Prova un indirizzo, "
                        "e controlla Componenti mancanti."),
    "errore_addon": ("errore", "L'addon ha avuto un errore",
                     "Non sembra un problema di rete ma un errore dentro l'addon, per esempio dati ricevuti "
                     "in un formato inatteso. Errore:",
                     "Riprova. Se si ripete, segnala l'errore a chi mantiene l'addon e allega il report "
                     "di Kodi Doctor."),
    "altro": ("avviso", "Risposta insolita", "Il server ha risposto in modo inatteso.", ""),
}

GUIDA = (
    "COME USARE KODI DOCTOR\n\n"
    "Diagnosi completa: controlla internet, DNS, orologio e componenti, e ti dice cosa non va.\n\n"
    "Prova un indirizzo: incolla il link che non parte e scopri se il problema è il DNS, "
    "Cloudflare, un link morto o altro.\n\n"
    "Componenti mancanti: mostra gli addon necessari e li installa.\n\n"
    "Avviso automatico: se una riproduzione fallisce, Kodi Doctor lo segnala da solo "
    "e dice il probabile motivo. Si spegne dalle impostazioni.\n\n"
    "Problemi rilevati: Kodi Doctor legge il log di Kodi mentre usi gli addon e ti avvisa con una "
    "notifica quando trova un errore. Qui trovi l'elenco con la spiegazione di ognuno.\n\n"
    "Aggiornamenti: Kodi Doctor si aggiorna da solo da GitHub quando c'è un commit nuovo e ti dice "
    "la versione e cosa è cambiato. Da qui puoi anche cercare un aggiornamento a mano.\n\n"
    "Per altri addon: RunScript(script.kodidoctor,errore,TESTO DELL'ERRORE) analizza un "
    "messaggio di errore e spiega la causa.")
