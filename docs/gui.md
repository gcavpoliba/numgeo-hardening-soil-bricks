# Interfaccia Grafica (GUI) — `gui_hs_bricks.py`

La GUI PyQt6 `gui_hs_bricks.py` e' lo strumento principale per eseguire prove
elementari con il driver IncrementalDriver, calibrare i parametri interni del
modello HS-MN-Bricks e visualizzare i risultati in modo interattivo.

## Avvio rapido

### Windows

1. Assicurarsi di avere una distribuzione Python 3.10+ con `PyQt6`,
   `numpy`, `pandas`, `matplotlib` installati.
2. Lanciare il batch `Avvia_Interfaccia.bat` dalla cartella radice del repo.
3. In alternativa, da terminale:

   ```bat
   python gui_hs_bricks.py
   ```

### Linux / macOS

La GUI funziona anche sotto Linux/macOS a patto di ricompilare l'eseguibile
`IncrementalDriver.exe` (o fornire un equivalente compatibile con la keyword
parser descritta in `src/incremental-driver/`).

## Tipi di prova supportati

La GUI supporta tre tipi di prova elementare, selezionabili indipendentemente
tramite checkbox nel pannello di sinistra:

| Prova | Keyword driver | Condizione | Output principale |
|-------|----------------|------------|-------------------|
| **TX-CID** (Consolidated Isotropic Drained) | `*TriaxialE1` | Controllo di `eps_1`, cell pressure `sigma_3 = p0'` costante | `q, p', eps_v` |
| **TX-CIU** (Consolidated Isotropic Undrained) | `*TriaxialUEq` | Controllo di `eps_q` (Roscoe) con `eps_v = 0` | `q, p', ∆u, p_totale` |
| **Ciclico non drenato** (per G/G0) | `*CirculatingLoad` con `*Cartesian` | Sweep di ampiezze cicliche in `eps_xy` | `G/G0, D, cicli tau-gamma` |

### TX-CID — Triassiale Drenata

E' la prova di riferimento per la calibrazione del modello HS in condizioni
drenate. Il driver applica un controllo cinematico sulla deformazione assiale
`eps_1`, mantenendo costante la tensione radiale `sigma_3 = p0'` (cell pressure
costante). L'output fornisce direttamente le tensioni efficaci `sigma_1'`,
`sigma_3'` (poiche' in drenato `u = 0`):

```
q   = sigma_1 - sigma_3
p'  = (sigma_1 + 2*sigma_3) / 3
eps_v = eps_1 + 2*eps_3
```

### TX-CIU — Triassiale Non Drenata

La prova **non drenata** e' essenziale per la calibrazione del modello in
condizioni di carico rapido (short-term) e per la verifica del percorso di
tensione efficace. Il driver impone `eps_v = 0` (nessuna deformazione
volumetrica) e applica un incremento di `eps_q` (deformazione deviatorica in
coordinate Roscoe).

La GUI calcola automaticamente:

- **`p'` (efficace)** — dalla media delle tensioni efficaci in output
- **`p_total`** — assumendo `sigma_3,total = p0'` costante (condizione di
  cella della prova lab):
  ```
  p_total = p0' + q/3
  ```
- **`∆u` (pressione di poro)** — come differenza fra `p_total` e `p'`:
  ```
  ∆u = p_total - p' = (p0' + q/3) - p'
  ```

> **Nota importante**: il driver restituisce direttamente le tensioni
> **efficaci** (il modello HS-MN-Bricks e' formulato in tensioni efficaci).
> Per calcolare `∆u` e' quindi necessario conoscere il percorso di tensione
> totale, che per la prova CIU di laboratorio e' dato dalla cell pressure
> costante.

### Ciclico non drenato per G/G0

La prova ciclica applica una **sollecitazione armonica** di deformazione di
taglio (componente `xy`) con ampiezza `gamma_a`. Lo sweep logaritmico di
ampiezze (default: 13 punti da `1e-6` a `1e-2`) produce la curva di
decadimento del modulo `G/G0` e di smorzamento `D`:

- **`G_sec` = `tau_a / gamma_a`** — modulo secante
- **`D` = `Area_ciclo / (2*pi*tau_a*gamma_a)`** — rapporto di smorzamento
  isteretico

La curva target teorica (formula HS small-strain) e' mostrata in
sovrapposizione per confronto:

```
G/G0 = 1 / (1 + (3/7) * (gamma / gamma_0.7))
```

## Struttura della GUI

La finestra e' divisa in due pannelli tramite uno splitter orizzontale:

- **Pannello sinistro** (scrollabile, 440-540 px):
  1. Preset e file parametri (`parameters.inp`)
  2. 16 parametri costitutivi HS-MN-Bricks
  3. Condizioni di prova (checkbox TX-CID/TX-CIU/Ciclico + setup)
  4. Caricamento dati sperimentali (overlay di calibrazione)
  5. Pulsante di esecuzione + progress bar + log

- **Pannello destro** (tab widget, 4 schede):
  1. **Prove Triassiali** — 4 pannelli: `q-eps_s`, `q-p` (eff + tot), `eps_v`/`∆u` vs `eps_s`, `p'` vs `eps_s`
  2. **Geotecnica Sismica** — `G/G0-gamma` e `D-gamma`
  3. **Cicli di Isteresi** — `tau-gamma` per ampiezza selezionata
  4. **Tabelle Risultati** — TX-CID, TX-CIU, Ciclico in sotto-tab separati

## Risoluzione dei problemi

### I diagrammi non si aggiornano

Nella versione 2 della GUI, i diagrammi vengono **sempre rinfrescati** ad ogni
nuova simulazione: all'avvio del run vengono cancellati tutti i plot e
resettabile il `combo_amplitudes` e le tabelle. Solo i risultati effettivamente
prodotti dal driver vengono poi rappresentati.

Se i diagrammi sembrano non aggiornarsi, verificare:

1. Che il pulsante **AVVIA SIMULAZIONE** non sia disabilitato (ci sono worker
   precedenti in esecuzione?).
2. Che `IncrementalDriver.exe` sia individuato correttamente (verificare il
   path nel log iniziale).
3. Che i file `.out` non siano vuoti (problema di licenza Intel Fortran
   runtime, path Intel mancante, o modello non convergente).
4. Che i parametri `alpha` e `Hpp` siano stati calibrati (pulsante **Calcola
   alpha & Hpp**) o impostati a valori diversi da 0.

### La prova TX-CIU non converge

Prove non drenate su terreni coesivi tendono a saturare presto la
resistenza; ridurre il target di deformazione (es. `-15%` invece di `-25%`) o
aumentare `ninc_tx` (es. 5000 incrementi).

### L'eseguibile non viene trovato

La funzione `find_executables()` cerca in ordine:

1. `examples/IncrementalDriver/IncrementalDriver.exe`
2. `VisualStudio/IncrementalDriver/x64/Release/IncrementalDriver.exe`
3. `<root>/IncrementalDriver.exe`

Si puo' copiare l'eseguibile in una di queste posizioni o aggiungere un path
alternativo nella lista `driver_candidates`.

### Le pressioni di poro sembrano errate

Verificare che:

- `p0'` nel campo "Confinamento p0' [kPa]" corrisponda al valore effettivo
  di consolidamento.
- Lo stato iniziale in `initialconditions.inp` sia isotropo a `p0'`
  (i.e. `stress(1) = stress(2) = stress(3) = -p0'`).
- Non si siano verificate derive numeriche (provare ad aumentare `ninc_tx`).

## Estensione della GUI

Per aggiungere un nuovo tipo di prova:

1. Estendere `SimulationWorker.run()` con un nuovo blocco `if self.run_newtest`.
2. Costruire il file `test.inp` appropriato con la keyword del driver (vedi
   `src/incremental-driver/incrementalDriver.f` per l'elenco completo).
3. Leggere l'output con `self._read_driver_out()`.
4. Convertire con `self._to_geotech()` o logica custom.
5. Aggiungere una checkbox nel pannello sinistro in `_init_ui`.
6. Aggiungere il plot corrispondente in `_plot_triaxial` o una nuova funzione.
7. Aggiornare `_init_empty_plots` per includere il nuovo pannello.

Le keyword disponibili nel driver includono (vedi sorgente Fortran):

- `*TriaxialE1`  — Triassiale, controllo eps_1 (drained)
- `*TriaxialS1`  — Triassiale, controllo sigma_1
- `*TriaxialUEq` — Triassiale non drenato, controllo eps_q (Roscoe)
- `*TriaxialUq`  — Triassiale non drenato, controllo q (Roscoe)
- `*CirculatingLoad` — Sollecitazione armonica
- `*LinearLoad` — Sollecitazione lineare (generica)
- `*PureCreep`, `*UndrainedCreep` — Prove di creep
- `*ImportFile` — Storia di carico da file
- `*ObeyRestrictions` — Restrizioni custom (parser simbolico)
