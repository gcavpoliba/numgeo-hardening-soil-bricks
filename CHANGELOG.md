# Changelog

## [v2-gui] — Interfaccia grafica migliorata

### Aggiunto
- **Prova TX-CIU** (Consolidated Isotropic Undrained) tramite keyword driver
  `*TriaxialUEq`. Calcolo automatico di:
  - pressione efficace `p'`
  - pressione totale `p = p0' + q/3` (assumendo cell pressure costante)
  - pressione di poro `∆u = p - p'`
  - evoluzione di `p'` con `eps_a`
- **Esempio** di TX-CIU in `examples/IncrementalDriver/undrained_examples/`.
- **Esempio** di prova ciclica in
  `examples/IncrementalDriver/cyclic_undrained/`.
- **Documentazione GUI** completa in `docs/gui.md`.
- **Pannello 4-plot** per le prove triassiali: `q-eps_s`, `q-p` (eff + tot),
  `eps_v`/`∆u` vs `eps_s`, `p'` vs `eps_s`. TX-CID e TX-CIU sono sovrapposte
  sullo stesso grafico quando entrambe vengono eseguite.
- **Tabella risultati TX-CIU** con colonne `eps_1, eps_s, p', p_totale, q, ∆u`.
- Controlli per `ninc_tx` (incrementi triassiali) e `ninc_cy` (incrementi
  per ciclo), in precedenza hard-coded.

### Modificato
- Rinominata la prova "TX-CD" in **TX-CID** (Consolidated Isotropic Drained)
  per allineamento con la notazione geotecncia standard di laboratorio.
- Rinominato lo sweep ciclico in **Ciclico Non Drenato per G/G0** per
  evidenziare che la prova di taglio semplice e' intrinsecamente non drenata
  sulla componente di taglio.
- Il pulsante **AVVIA SIMULAZIONE** ora resetta preventivamente tutti i
  grafici e le tabelle: questo risolve il bug "diagrammi non aggiornati" in
  cui i plot di run precedenti rimanevano visibili se la prova corrispondente
  non veniva rieseguita.
- Pulizia dei file `.out` precedenti all'inizio di ogni run del worker per
  evitare letture stale.
- Auto-scroll del log ai nuovi messaggi.

### Fix
- **Bug critico**: i diagrammi non venivano aggiornati quando si faceva una
  nuova simulazione. Causa: il metodo `_on_simulation_finished` aggiornava
  solo i plot delle prove effettivamente eseguite; le prove sospese lasciavano
  i plot precedenti sullo schermo. Fix: il pulsante di avvio richiama
  `_init_empty_plots()` PRIMA di lanciare il worker, garantendo che tutti i
  pannelli siano vuoti fin dall'inizio.
- **Bug minore**: il `combo_amplitudes` dei cicli di isteresi non veniva
  azzerato quando si disattivava la prova ciclica; ora e' gestito insieme
  agli altri widget.
- Le tabelle `TX-CID`, `TX-CIU`, `Ciclico` sono ora separate in sotto-tab
  dedicate nel tab "Tabelle Risultati".

### Interni
- Refactoring del worker: i 16 nomi dei parametri e le 78 colonne di output
  del driver sono ora costanti a livello di modulo (`PARAM_NAMES`,
  `DRIVER_OUT_COLUMNS`).
- Aggiunta la funzione helper `_to_geotech` per la conversione dalla
  convenzione del driver (compressione negativa) alla convenzione geotecnica
  (compressione positiva).
- Aggiornati gli output file: `triax_CD.out` (per TX-CID) e `triax_CIU.out`
  (per TX-CIU) con nomi distinti, per evitare sovrascritture accidentali.

## [v1.0] — Versione originale gcavpoliba

Rilascio iniziale della GUI PyQt6 per il modello HS-MN-Bricks:
- Prova triassiale drenata (TX-CD) con `*TriaxialE1`
- Sweep ciclico con `*CirculatingLoad` per G/G0 e D
- Calibrazione automatica di `alpha` e `Hpp`
- Preset materiali (Glacial Till, Dense Hostun Sand)
- 4 tab: triassiali, dinamici, isteresi, tabelle
- Esportazione CSV e PNG ad alta risoluzione
- Generazione di un foglio Excel di calibrazione
