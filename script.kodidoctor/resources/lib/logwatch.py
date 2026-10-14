# -*- coding: utf-8 -*-
"""Legge kodi.log mentre Kodi lo scrive e raggruppa le righe di errore in blocchi.

Un errore di Python occupa molte righe (il traceback): righe con data e ora, più righe
indentate senza data. Le righe vicine nel tempo finiscono nello stesso blocco, che viene
consegnato a chi ascolta solo quando il log resta fermo per qualche istante.
Nessuna dipendenza da Kodi, cosi si prova ovunque.
"""

import os
import re
import time

RIGA = re.compile(r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)\.(\d+) T:(\d+)\s+(\w+)\s+<[^>]*>:\s?(.*)$")
MAX_LETTURA = 512 * 1024   # se il log cresce di piu in un colpo, guardo solo la coda
MAX_BLOCCO = 20000         # caratteri
GAP_BLOCCO = 3.0           # secondi massimi tra due righe dello stesso blocco
ATTESA_CHIUSURA = 2.0      # silenzio dopo l'ultima riga prima di consegnare il blocco


def _secondi(data, frazione):
    try:
        return time.mktime(time.strptime(data, "%Y-%m-%d %H:%M:%S")) + float("0." + frazione)
    except (ValueError, OverflowError):
        return 0.0


def solo_errori(livello, messaggio):
    return livello in ("error", "fatal")


class LogWatcher:
    def __init__(self, percorso, su_blocco, interessante=solo_errori, orologio=time.time):
        self.percorso = percorso
        self._su_blocco = su_blocco
        self._interessante = interessante
        self._orologio = orologio
        self._offset = 0
        self._inode = None
        self._resto = ""
        self._righe = []
        self._ultimo_ts = 0.0
        self._ultimo_ingresso = 0.0

    def avvia(self):
        """Parte dalla fine del file: il passato non interessa."""
        try:
            st = os.stat(self.percorso)
            self._offset, self._inode = st.st_size, st.st_ino
        except OSError:
            self._offset, self._inode = 0, None

    def _nuove_righe(self):
        try:
            st = os.stat(self.percorso)
        except OSError:
            return []
        if (self._inode is not None and st.st_ino != self._inode) or st.st_size < self._offset:
            # Kodi e stato riavviato: nuovo file di log
            self._offset, self._resto = 0, ""
        self._inode = st.st_ino
        if st.st_size == self._offset:
            return []
        da = self._offset
        if st.st_size - da > MAX_LETTURA:
            da, self._resto = st.st_size - MAX_LETTURA, ""
        try:
            with open(self.percorso, "rb") as f:
                f.seek(da)
                dati = f.read(st.st_size - da)
        except OSError:
            return []
        self._offset = da + len(dati)
        testo = self._resto + dati.decode("utf-8", "replace")
        righe = testo.split("\n")
        self._resto = righe.pop()  # l'ultima riga puo essere ancora a meta
        return [r.rstrip("\r") for r in righe]

    def _chiudi(self):
        if self._righe:
            testo = "\n".join(self._righe)[-MAX_BLOCCO:]
            self._righe = []
            self._su_blocco(testo)

    def passo(self):
        """Da chiamare circa una volta al secondo."""
        ora = self._orologio()
        for riga in self._nuove_righe():
            m = RIGA.match(riga)
            if m:
                livello, messaggio = m.group(4).lower(), m.group(5)
                if not self._interessante(livello, messaggio):
                    continue  # le righe di altro tipo non chiudono il blocco: possono stare in mezzo a un traceback
                ts = _secondi(m.group(1), m.group(2))
                if self._righe and ts - self._ultimo_ts > GAP_BLOCCO:
                    self._chiudi()
                self._righe.append(riga)
                self._ultimo_ts = ts
                self._ultimo_ingresso = ora
            elif self._righe and riga.strip():
                self._righe.append(riga)  # continuazione (indentata) di un messaggio
                self._ultimo_ingresso = ora
        if self._righe and ora - self._ultimo_ingresso >= ATTESA_CHIUSURA:
            self._chiudi()
