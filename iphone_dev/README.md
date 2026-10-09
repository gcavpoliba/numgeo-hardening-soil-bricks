# 📱 Hardening Soil Bricks — Geotech Simulator (iPhone & Netlify)

Applicazione web progressiva (PWA) ottimizzata per **Apple iPhone (iOS Safari)**, pronta per essere ospitata gratuitamente su **[Netlify](https://www.netlify.com/)** (`*.netlify.app`).

Permette di eseguire simulazioni geotecniche avanzate del modello **Hardening Soil con estensione Matsuoka–Nakai e Bricks (numgeo)** direttamente dal proprio smartphone, con calcoli 100% client-side ad altissima velocità e senza bisogno di backend o eseguibili Windows.

---

## 🚀 Come caricare su Netlify.app (In 1 minuto)

### Metodo 1: Netlify Drop (Senza riga di comando — Più Semplice)
1. Accedi a [app.netlify.com/drop](https://app.netlify.com/drop).
2. Trascina la cartella `iphone_dev` direttamente nella finestra del browser.
3. In pochi secondi Netlify genererà un URL pubblico gratuito (es. `https://hs-bricks-geotech.netlify.app`).
4. Fatto! Il sito è subito attivo e accessibile da qualsiasi iPhone o browser.

### Metodo 2: Collegamento da GitHub / GitLab
1. Nel tuo account Netlify, clicca su **"Add new site"** → **"Import an existing project"**.
2. Collega il repository GitHub `numgeo-hardening-soil-bricks`.
3. Nelle impostazioni di build configura:
   - **Base directory**: `iphone_dev`
   - **Build command**: *(lasciare vuoto)*
   - **Publish directory**: `.`
4. Clicca su **"Deploy"**. Ad ogni aggiornamento Git, Netlify ricompilerà e pubblicherà automaticamente il sito.

### Metodo 3: Netlify CLI
Dalla cartella `iphone_dev`:
```bash
npm install -g netlify-cli
netlify deploy --prod --dir=.
```

---

## 📲 Come installare su iPhone (Come App Nativa)

1. Apri l'URL Netlify su **Safari** sul tuo iPhone (es. `https://tuo-sito.netlify.app`).
2. Tocca l'icona **Condividi** (il quadrato con la freccia verso l'alto al centro in basso).
3. Scorri il menu verso il basso e tocca **"Aggiungi alla schermata Home"** (*Add to Home Screen*).
4. Tocca **"Aggiungi"** in alto a destra.
5. Sulla schermata Home apparirà l'icona **HS-Bricks**.
6. Toccandola, l'applicazione si aprirà a **schermo intero standalone**, con:
   - Area sicura per notch e Dynamic Island.
   - Fluidità nativa a 60/120 fps (ProMotion).
   - Funzionamento **100% offline** (anche senza connessione internet) grazie al Service Worker integrato.

---

## 🔬 Funzionalità Scientifiche del Modello

| Prova / Funzionalità | Descrizione Tecnica |
|---|---|
| **TX-CID (Drenata)** | Prova triassiale drenata isotropa a tensione radiale $\sigma_3' = p_0'$ costante. Risposta deviatorica iperbolica ($q - \varepsilon_s$), evoluzione volumetrica ($\varepsilon_v - \varepsilon_s$) con teoria di dilatanza di Rowe ($\sin\psi_m$) e rottura Matsuoka-Nakai. |
| **TX-CIU (Non Drenata)** | Prova triassiale non drenata a volume costante ($\varepsilon_v = 0$). Calcolo dinamico della pressione neutra $\Delta u = p_{tot} - p'$ con percorso di tensione totale $p_{tot} = p_0' + q/3$ e percorso di tensione efficace $q - p'$. |
| **Ciclico Non Drenato per $G/G_0$ e $D$** | Sweep logaritmico delle ampiezze di deformazione di taglio $\gamma_a \in [10^{-6}, 10^{-2}]$. Calcolo della curva di decadimento del modulo di taglio (Santos & Correia / Cudny & Truty) e dello smorzamento isteretico $D\%$ (regole di Masing). |
| **Cicli di Isteresi $\tau - \gamma$** | Generazione dei cicli isteretici chiusi per qualsiasi ampiezza $\gamma_a$ selezionata, con calcolo automatico dell'energia dissipata per ciclo $\Delta W = \oint \tau d\gamma$. |
| **10 Bricks (Simpson / Cudny)** | Discretizzazione multi-superficie a 10 brick cinetici, con calcolo e rappresentazione delle lunghezze di corda $sl_j$ e delle superfici di snervamento. |
| **Calibrazione Automatica $\alpha$ & $H_{pp}$** | Risolutore numerico globale di Newton per determinare i parametri interni del cap ($\alpha$ e $H_{pp}$) dalla prova edometrica virtuale ($E_{oed}^{ref}, K_0^{nc}$). Include la visualizzazione tabellare della cronologia di convergenza. |
| **Overlay Dati di Laboratorio** | Caricamento di curve sperimentali CSV per prove triassiali e colonna risonante, con calcolo automatico della bontà di calibrazione ($R^2$, RMSE). Include dataset campione precaricati (Glacial Till). |
| **Compatibilità parameters.inp** | Importazione ed esportazione diretta nel formato originale `parameters.inp` compatibile al 100% con `IncrementalDriver.exe` e `numgeo`. |

---

## 📂 Struttura Cartella `iphone_dev`

```
iphone_dev/
├── index.html              # Applicazione principale iOS PWA
├── manifest.json           # Manifest per installazione nativa su iPhone
├── sw.js                   # Service Worker per funzionamento offline
├── netlify.toml            # Configurazione e header di sicurezza per Netlify
├── _redirects              # Routing fallback per Netlify
├── css/
│   └── ios-theme.css       # Design Apple iOS (SF Pro, Frosted Glass, Dark/Light Mode)
├── js/
│   ├── app.js              # Controller interfaccia e gestione eventi
│   ├── engine.js           # Motore costitutivo numerico HS-MN-Bricks
│   ├── charts.js           # Grafici interattivi touch ad alta risoluzione Retina
│   ├── presets.js          # Preset geotecnici e parser/exporter parameters.inp
│   └── lab-data.js         # Gestore CSV e analisi errore di calibrazione
└── assets/
    ├── icon.svg            # Icona ufficiale iOS HS-Bricks
    ├── sample_triaxial.csv # Dati sperimentali triassiali (Glacial Till)
    └── sample_cyclic.csv   # Dati sperimentali colonna risonante
```

---

## 🛠 Sviluppo Locale
Per testare localmente prima di caricare su Netlify:
```bash
# Avvia un semplice server HTTP locale
cd iphone_dev
python -m http.server 8000
```
Quindi apri `http://localhost:8000` (o da iPhone connesso alla stessa rete WiFi `http://<IP-computer>:8000`).
