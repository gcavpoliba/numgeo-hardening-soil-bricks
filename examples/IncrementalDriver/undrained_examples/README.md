# Esempio: Prova Triassiale Consolidata Isotropa Non Drenata (TX-CIU)

Questa cartella contiene un esempio di prova **TX-CIU** (Consolidated Isotropic
Undrained) per il modello **Hardening Soil - Matsuoka-Nakai - Bricks**.

## File contenuti

| File | Descrizione |
|------|-------------|
| `test_CIU.inp`         | File di controllo del driver (keyword `*TriaxialUEq`) |
| `initialconditions.inp`| Stato iniziale: consolidamento isotropo a `p0' = 100 kPa` |
| `parameters.inp`       | Parametri del modello HS-MN-Bricks (16 properties) |

## Come si esegue manualmente (riga di comando)

1. Copiare `IncrementalDriver.exe` in questa cartella (oppure assicurarsi che il
   PATH individui l'eseguibile).
2. Eseguire:

   ```bat
   IncrementalDriver.exe param=parameters.inp ini=initialconditions.inp test=test_CIU.inp
   ```

3. Verra' generato il file `triax_CIU.out` con 78 colonne:
   `time1, time2, stran_1..6, stress_1..6, statev_1..73`.

## Significato della keyword `*TriaxialUEq`

Il driver converte internamente la richiesta in `*LinearLoad` con coordinate
`*Roscoe`, applicando un **incremento di deformazione deviatorica `eps_q`**
mentre la **deformazione volumetrica `eps_v` e' mantenuta = 0** (condizione
non drenata a livello di elemento).

Dato `eps_v = 0` e il legame cinematico triassiale `eps_3 = -eps_1/2`, vale:
`eps_q (Roscoe) = -eps_1 (driver)`.

Per una compressione del 25%:
- `eps_1 (driver)  = -0.25`  (compressione NEGATIVA nella convenzione del driver)
- `eps_q (Roscoe) = +0.25`   (compressione POSITIVA nella convenzione Roscoe)

Per questo motivo, nel file `test_CIU.inp` si legge `0.25` (positivo).

## Calcolo della pressione di poro

Per una prova CIU di laboratorio con **cell pressure costante = p0'**, il
percorso di tensione totale e' noto:

```
sigma3_total = p0'          (cell pressure costante)
sigma1_total = p0' + q       (applicazione del carico assiale)
p_total      = p0' + q/3     (tensione media totale)
```

La tensione efficace `p'` e' restituita direttamente dal driver (il modello
costitutivo lavora in tensioni efficaci). La pressione di poro e':

```
u  = p_total - p'  = p0' + q/3 - p'
∆u = u              (perche' u0 = 0 dopo consolidamento)
```

La GUI implementa questa formula automaticamente nel worker
`SimulationWorker.run` quando `run_tx_cu = True`.
