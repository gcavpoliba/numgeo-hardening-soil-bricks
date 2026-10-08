# Esempio: Prova Ciclica Non Drenata per la curva G/G0 - gamma

Questa cartella contiene un esempio di **prova ciclica non drenata** per la
determinazione della curva di decadimento del modulo di taglio `G/G0` e dello
smorzamento isteretico `D` in funzione dell'ampiezza di deformazione di
scorrimento `gamma`.

## File contenuti

| File | Descrizione |
|------|-------------|
| `test_cyclic.inp`      | File di controllo del driver (keyword `*CirculatingLoad` con `*Cartesian`) |
| `initialconditions.inp`| Stato iniziale: consolidamento isotropo a `p0' = 100 kPa` |
| `parameters.inp`        | Parametri del modello HS-MN-Bricks (16 properties) |

## Come si esegue manualmente (riga di comando)

1. Copiare `IncrementalDriver.exe` in questa cartella.
2. Eseguire:

   ```bat
   IncrementalDriver.exe param=parameters.inp ini=initialconditions.inp test=test_cyclic.inp
   ```

3. Verra' generato il file `cycle_test.out` con 78 colonne.

## Significato della keyword `*CirculatingLoad` con `*Cartesian`

Il driver applica una **sollecitazione armonica** con ampiezza `deltaLoadCirc(i)`
sulla componente `i` (qui `i = 4`, deformazione di taglio `xy`).

Il blocco `*Cartesian` richiede 6 righe con il formato:
```
ifstress(i)  deltaLoadCirc(i)  phase0(i)  deltaLoad(i)
```

- `ifstress(i) = 1` → la componente `i` e' controllata in tensione
- `ifstress(i) = 0` → la componente `i` e' controllata in deformazione

Nell'esempio, la componente 4 ha `ifstress = 0` (deformazione controllata) con
ampiezza `1e-4`: si applica un ciclo di deformazione di taglio con ampiezza
`gamma_a = 1e-4`.

## Sweep di ampiezze (nella GUI)

La GUI esegue in automatico uno **sweep logaritmico** di `n_cycles` ampiezze
(da `1e-6` a `1e-2` di default), generando un file `.out` separato per ogni
ampiezza. Per ciascun ciclo vengono calcolati:

- **`gamma_a`**: ampiezza di scorrimento (`(gamma_max - gamma_min)/2`)
- **`tau_a`  : ampiezza di tensione tangenziale (`(tau_max - tau_min)/2`)
- **`G_sec`  : modulo secante (`tau_a / gamma_a`)
- **`G/G0`** : modulo secante normalizzato al modulo iniziale `G0`
- **`D`**    : rapporto di smorzamento isteretico:
  ```
  D = Area_ciclo / (2 * pi * tau_a * gamma_a)
  ```

## Ciclo non drenato

La prova di taglio semplice ciclica (componente 4 = `eps_xy`) e' **non drenata
di default** sulla componente di taglio: non viene imposta alcuna deformazione
volumetrica. Per analisi cicliche triassiali non drenate con `eps_v = 0`
esplicito, e' possibile usare `*CirculatingLoad` con `*Roscoe` e
`deltaLoadCirc(1) = 0` (volumetrica nulla).

Nella GUI, lo sweep di ampiezze avviene automaticamente con la configurazione
default (Cartesian, componente 4). Cio' corrisponde alla prassi di laboratorio
per prove di colonna risonante o cicliche di taglio semplice.
