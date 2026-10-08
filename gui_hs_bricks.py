#!/usr/bin/env python3
"""
gui_hs_bricks.py
================
Interfaccia Grafica (GUI) moderna per la simulazione e calibrazione del modello
costitutivo Hardening Soil (Matsuoka-Nakai) con estensione BRICK (numgeo).

Sviluppata per applicazioni di geotecnica e geotecnica sismica:
- Prove Triassiali Drenate  (TX-CID, Consolidated Isotropic Drained)  -> *TriaxialE1
- Prove Triassiali Non Drenate (TX-CIU, Consolidated Isotropic Undrained) -> *TriaxialUEq
- Prove Cicliche Non Drenate per la determinazione della curva G/G0 e dello smorzamento D
- Visualizzazione dei cicli di isteresi tau-gamma
- Calcolo della pressione di poro ∆u e del percorso di tensione totale/effective
- Sovrapposizione di dati sperimentali di laboratorio per calibrazione
- Calibrazione automatica dei parametri interni del cap (alpha e Hpp)

Novità rispetto alla versione precedente:
1. I diagrammi vengono sempre rinfrescati ad ogni nuova simulazione (fix del bug
   "plot non aggiornati"): vengono cancellati all'avvio di ogni run e ripopolati
   solo con i risultati effettivamente prodotti dal driver.
2. Aggiunta della prova TX-CIU (Consolidated Isotropic Undrained) con calcolo
   della pressione di poro ∆u e del percorso di tensione totale p = p0 + q/3.
3. Aggiunta del tracciamento del percorso tensionale in piano q-p' (effective)
   e q-p (total) per le prove non drenate.
4. Aggiunta del pannello per la prova ciclica non drenata (sweep di ampiezze
   di taglio) con output G/G0-gamma e D-gamma.

Convenzioni:
- Driver Fortran:      compressione = numeri NEGATIVI (stran_1 < 0, stress_1 < 0)
- Roscoe invariants:    compressione = numeri POSITIVI (p, q > 0 per compressione)
- GUI (geotecnica):     compressione = numeri POSITIVI (eps_a, q, p' > 0)
- Pressione di poro:    ∆u > 0 indica incremento di pressione di poro

Autore: numgeo-hardening-soil-bricks contributors.
Licenza: vedi LICENSE.
"""

from __future__ import annotations

import os
import sys
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Dict, Tuple, List

import numpy as np
import pandas as pd

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QGroupBox, QLabel, QLineEdit, QPushButton, QCheckBox,
    QDoubleSpinBox, QSpinBox, QComboBox, QTabWidget, QProgressBar,
    QTextEdit, QFileDialog, QMessageBox, QSplitter, QTableWidget,
    QTableWidgetItem, QHeaderView, QScrollArea, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QIcon

import matplotlib
matplotlib.use("QtAgg")
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT


# -----------------------------------------------------------------------------
# Configurazioni di Sistema e Percorsi
# -----------------------------------------------------------------------------
def get_intel_rt_env() -> Dict[str, str]:
    """Aggiunge le cartelle delle runtime Intel Fortran a PATH."""
    env = os.environ.copy()
    candidate_paths = [
        r"C:\Users\uso\anaconda3\Library\bin",
        r"C:\Users\uso\anaconda3\bin",
        r"C:\Program Files (x86)\Intel\oneAPI\compiler\latest\windows\bin",
    ]
    cur_path = env.get("PATH", "")
    for p in candidate_paths:
        if os.path.exists(p) and p not in cur_path:
            cur_path = p + os.pathsep + cur_path
    env["PATH"] = cur_path
    return env


def get_project_root() -> Path:
    return Path(__file__).resolve().parent


def find_executables() -> Tuple[Optional[Path], Optional[Path]]:
    root = get_project_root()
    driver_candidates = [
        root / "examples" / "IncrementalDriver" / "IncrementalDriver.exe",
        root / "VisualStudio" / "IncrementalDriver" / "x64" / "Release" / "IncrementalDriver.exe",
        root / "IncrementalDriver.exe",
    ]
    calib_candidates = [
        root / "examples" / "Calibration" / "numgeo-hs-bricks-calibration.exe",
        root / "VisualStudio" / "numgeo-hs-bricks-calibration" / "x64" / "Release" / "numgeo-hs-bricks-calibration.exe",
        root / "numgeo-hs-bricks-calibration.exe",
    ]

    driver_exe = next((c.resolve() for c in driver_candidates if c.is_file()), None)
    calib_exe = next((c.resolve() for c in calib_candidates if c.is_file()), None)
    return driver_exe, calib_exe


# Preset di parametri noti dalla letteratura
PRESETS = {
    "Glacial Till (Cudny & Truty 2020)": {
        "E50": 8500.0, "Eoed": 6150.0, "Eur": 25750.0, "m": 0.70,
        "c": 6.0, "phi": 28.0, "psi": 6.0, "nu": 0.29,
        "pref": 100.0, "K0nc": 0.80, "Rf": 0.90, "Ei": 15460.0,
        "alpha": 0.515, "Hpp": 9866.0, "gamma07": 3.0e-4, "G0": 60000.0
    },
    "Dense Hostun Sand (Benz 2007)": {
        "E50": 30000.0, "Eoed": 30000.0, "Eur": 90000.0, "m": 0.55,
        "c": 0.1, "phi": 42.0, "psi": 16.0, "nu": 0.25,
        "pref": 100.0, "K0nc": 0.40, "Rf": 0.90, "Ei": 65000.0,
        "alpha": 1.46, "Hpp": 72000.0, "gamma07": 1.0e-4, "G0": 108000.0
    }
}


# Lista ordinata dei 16 parametri del modello HS-MN-Bricks
PARAM_NAMES: List[str] = [
    "E50", "Eoed", "Eur", "m", "c", "phi", "psi", "nu",
    "pref", "K0nc", "Rf", "Ei", "alpha", "Hpp", "gamma07", "G0"
]


# Colonne attese nei file .out del driver (78 colonne totali):
# time1, time2, stran_1..6, stress_1..6, statev_1..73
DRIVER_OUT_COLUMNS: List[str] = (
    ["time1", "time2"]
    + [f"stran_{k}" for k in range(1, 7)]
    + [f"stress_{k}" for k in range(1, 7)]
    + [f"statev_{k}" for k in range(1, 74)]
)


# -----------------------------------------------------------------------------
# Worker Thread per la Simulazione in Background
# -----------------------------------------------------------------------------
class SimulationWorker(QThread):
    """Esegue le prove TX-CID, TX-CIU e cicliche non drenate in un thread
    separato. Emette segnali per progresso, log, risultati finali ed errori.

    Parametri chiave:
        run_tx_cd : bool  - esegue la prova TX-CID (drenata, *TriaxialE1)
        run_tx_cu : bool  - esegue la prova TX-CIU (non drenata, *TriaxialUEq)
        run_cy    : bool  - esegue lo sweep ciclico non drenato per G/G0
        p0       : float - pressione di consolidamento isotropo [kPa]
        eps1_target : float - deformazione assiale target [%] (segno negativo
                              per compressione, in linea con la convenzione GUI)
        ninc_tx  : int    - numero incrementi per le prove triassiali monotoniche
        n_cycles : int    - numero di ampiezze cicliche (sweep logaritmico)
        gamma_min, gamma_max : float - range dello sweep di ampiezze
        ninc_cy  : int    - incrementi per ciclo
    """
    progress_changed = pyqtSignal(int, str)
    log_emitted = pyqtSignal(str)
    finished_simulation = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, driver_exe: Path, params: dict,
                 run_tx_cd: bool, run_tx_cu: bool, run_cy: bool,
                 p0: float, eps1_target: float, ninc_tx: int,
                 n_cycles: int, gamma_min: float, gamma_max: float, ninc_cy: int,
                 work_dir: Path):
        super().__init__()
        self.driver_exe = driver_exe
        self.params = params
        self.run_tx_cd = run_tx_cd
        self.run_tx_cu = run_tx_cu
        self.run_cy = run_cy
        self.p0 = p0
        self.eps1_target = eps1_target
        self.ninc_tx = ninc_tx
        self.n_cycles = n_cycles
        self.gamma_min = gamma_min
        self.gamma_max = gamma_max
        self.ninc_cy = ninc_cy
        self.work_dir = work_dir

    # ----- Helpers -----
    def _write_parameters_inp(self) -> None:
        path = self.work_dir / "parameters.inp"
        with open(path, "w") as f:
            f.write("Hardening-Soil-MN-Bricks     cmname\n")
            f.write("16           nprops\n")
            for name in PARAM_NAMES:
                val = self.params.get(name, 0.0)
                f.write(f"{val:<16.6e} {name}\n")

    def _write_initial_conditions(self) -> None:
        """Condizioni iniziali: stato isotropo a p0' (compressione NEGATIVA
        nella convenzione del driver)."""
        path = self.work_dir / "initialconditions.inp"
        with open(path, "w") as f:
            f.write(f" 6        ntens\n")
            f.write(f" -{self.p0:.4f}     stress(1)\n")
            f.write(f" -{self.p0:.4f}     stress(2)\n")
            f.write(f" -{self.p0:.4f}     stress(3)\n")
            f.write(f"  0.0     stress(4)\n")
            f.write(f"  0.0     stress(5)\n")
            f.write(f"  0.0     stress(ntens)\n")
            f.write(f"  73      nstatv    number of state variables\n")

    def _read_driver_out(self, out_path: Path) -> pd.DataFrame:
        """Legge un file .out del driver; ritorna un DataFrame con colonne
        nominate secondo DRIVER_OUT_COLUMNS."""
        return pd.read_csv(out_path, sep=r"\s+", skiprows=1, names=DRIVER_OUT_COLUMNS)

    @staticmethod
    def _to_geotech(raw_df: pd.DataFrame) -> dict:
        """Converte le quantità cartesiane (convenzione driver: compressione
        negativa) nella convenzione geotecnica (compressione positiva).

        Ritorna un dict con eps1, eps3, eps_v, eps_s, s1, s3, p_eff, q in
        unita' percentuali per le deformazioni e kPa per le tensioni.
        """
        eps1 = -raw_df["stran_1"].values * 100.0
        eps3 = -raw_df["stran_2"].values * 100.0
        s1 = -raw_df["stress_1"].values
        s3 = -raw_df["stress_2"].values
        epss = (2.0 / 3.0) * (eps1 - eps3)
        epsv = eps1 + 2.0 * eps3
        p_eff = (s1 + 2.0 * s3) / 3.0
        q = s1 - s3
        return dict(eps1=eps1, eps3=eps3, eps_s=epss, eps_v=epsv,
                    s1=s1, s3=s3, p_eff=p_eff, q=q)

    # ----- Run principale -----
    def run(self):
        try:
            self.work_dir.mkdir(parents=True, exist_ok=True)
            # Pulisce file .out precedenti per evitare di leggere risultati stale
            for f in self.work_dir.glob("*.out"):
                try:
                    f.unlink()
                except OSError:
                    pass

            env = get_intel_rt_env()
            results: dict = {}

            # 1. Scrivi parameters.inp e initialconditions.inp (una tantum)
            self._write_parameters_inp()
            self._write_initial_conditions()

            # ---- A. Prova Triassiale Drenata (TX-CID) ----
            if self.run_tx_cd:
                self.progress_changed.emit(10, "Esecuzione TX-CID (drenata)...")
                self.log_emitted.emit(
                    f"-> Avvio TX-CID (p0' = {self.p0} kPa, eps_a target = {self.eps1_target}%)..."
                )

                # *TriaxialE1: controlla eps_1 (Cartesiano).
                # Il driver vuole il valore come frazione (NON %), con compressione NEGATIVA.
                # La GUI usa eps1_target < 0 per la compressione, quindi passiamo direttamente /100.
                test_inp = (
                    f"triax_CD.out\n"
                    f"*TriaxialE1\n"
                    f"{self.ninc_tx} 100 1.0\n"
                    f"{self.eps1_target / 100.0:.6f}\n"
                    f"*End\n"
                )
                with open(self.work_dir / "test.inp", "w") as f:
                    f.write(test_inp)

                res = subprocess.run(
                    [str(self.driver_exe)], cwd=self.work_dir,
                    capture_output=True, text=True, env=env
                )
                tx_out = self.work_dir / "triax_CD.out"
                if not tx_out.is_file():
                    raise RuntimeError(
                        f"Errore durante TX-CID:\n{res.stderr}\n{res.stdout}"
                    )

                raw_df = self._read_driver_out(tx_out)
                g = self._to_geotech(raw_df)
                results["df_tx_cd"] = pd.DataFrame({
                    "eps_1_pct": g["eps1"],
                    "eps_3_pct": g["eps3"],
                    "eps_s_pct": g["eps_s"],
                    "eps_v_pct": g["eps_v"],
                    "p_eff_kPa": g["p_eff"],
                    "q_kPa": g["q"],
                })
                self.log_emitted.emit("-> TX-CID completata con successo.")

            # ---- B. Prova Triassiale Non Drenata (TX-CIU) ----
            if self.run_tx_cu:
                base_prog = 25 if self.run_tx_cd else 10
                self.progress_changed.emit(base_prog, "Esecuzione TX-CIU (non drenata)...")
                self.log_emitted.emit(
                    f"-> Avvio TX-CIU (p0' = {self.p0} kPa, eps_a target = {self.eps1_target}%)..."
                )

                # *TriaxialUEq: controlla eps_q (Roscoe) con eps_v=0 (non drenato).
                # Per condizioni non drenate, eps_v = 0, quindi eps_q (Roscoe) = -eps_1 (driver).
                # La GUI usa eps1_target < 0 per la compressione (es. -25):
                #   eps_1 (driver) = -0.25 -> eps_q (Roscoe, compressione positiva) = +0.25
                # Quindi passiamo: deltaLoad(2) = -eps1_target/100
                eps_q_target = -self.eps1_target / 100.0  # roscoe: positivo per compressione

                test_inp = (
                    f"triax_CIU.out\n"
                    f"*TriaxialUEq\n"
                    f"{self.ninc_tx} 100 1.0\n"
                    f"{eps_q_target:.6f}\n"
                    f"*End\n"
                )
                with open(self.work_dir / "test.inp", "w") as f:
                    f.write(test_inp)

                res = subprocess.run(
                    [str(self.driver_exe)], cwd=self.work_dir,
                    capture_output=True, text=True, env=env
                )
                tx_out = self.work_dir / "triax_CIU.out"
                if not tx_out.is_file():
                    raise RuntimeError(
                        f"Errore durante TX-CIU:\n{res.stderr}\n{res.stdout}"
                    )

                raw_df = self._read_driver_out(tx_out)
                g = self._to_geotech(raw_df)

                # Per la prova CIU lab (cell pressure costante = p0):
                #   sigma3_total = p0  ; sigma1_total = p0 + q  ; p_total = p0 + q/3
                #   p_eff (letto dal driver, effettivo)
                #   u = p_total - p_eff = p0 + q/3 - p_eff
                #   u0 = 0 (consolidato) -> ∆u = u
                p_total = self.p0 + g["q"] / 3.0
                delta_u = p_total - g["p_eff"]
                # Per consistenza, forziamo eps_v = 0 (verifica numerica)
                # (in alcuni run il driver può produrre un eps_v macchina != 0)
                eps_v_undr = np.zeros_like(g["eps1"])

                results["df_tx_cu"] = pd.DataFrame({
                    "eps_1_pct": g["eps1"],
                    "eps_3_pct": g["eps3"],
                    "eps_s_pct": g["eps_s"],
                    "eps_v_pct": eps_v_undr,  # forzato = 0 per CIU
                    "p_eff_kPa": g["p_eff"],
                    "p_total_kPa": p_total,
                    "q_kPa": g["q"],
                    "delta_u_kPa": delta_u,
                    "sigma3_eff_kPa": g["s3"],
                    "sigma1_eff_kPa": g["s1"],
                })
                self.log_emitted.emit(
                    f"-> TX-CIU completata. ∆u_max = {np.max(delta_u):.1f} kPa, "
                    f"q_max = {np.max(g['q']):.1f} kPa, p'_min = {np.min(g['p_eff']):.1f} kPa."
                )

            # ---- C. Sweep Dinamico Ciclico Non Drenato (G/G0 - gamma) ----
            if self.run_cy:
                base_prog = 50 if (self.run_tx_cd or self.run_tx_cu) else 30
                self.progress_changed.emit(base_prog, "Esecuzione sweep ciclico non drenato...")
                amplitudes = np.logspace(
                    np.log10(self.gamma_min), np.log10(self.gamma_max), self.n_cycles
                )
                self.log_emitted.emit(
                    f"-> Sweep ciclico non drenato su {self.n_cycles} ampiezze "
                    f"da {self.gamma_min:.1e} a {self.gamma_max:.1e}..."
                )

                cy_records = []
                cycles_dict = {}
                trapz_fn = getattr(np, "trapezoid", getattr(np, "trapz", None))
                G0_val = self.params.get("G0", 60000.0)

                for idx, gam_a in enumerate(amplitudes):
                    prog = base_prog + int((100 - base_prog) * (idx + 1) / len(amplitudes))
                    self.progress_changed.emit(prog, f"Ciclo {idx+1}/{len(amplitudes)} (gamma = {gam_a:.2e})...")

                    out_name = f"cycle_{idx}.out"
                    # *CirculatingLoad con *Cartesian: applica deformazione di taglio
                    # ciclica in componente 4 (xy). E' una prova di taglio semplice
                    # che per la componente di taglio e' intrinsecamente non drenata
                    # (nessuna deformazione volumetrica imposta).
                    test_inp = (
                        f"{out_name}\n"
                        f"*CirculatingLoad\n"
                        f"{self.ninc_cy} 100 1.0\n"
                        f"*Cartesian\n"
                        f"1 0.0 0.0 0.0\n"
                        f"1 0.0 0.0 0.0\n"
                        f"1 0.0 0.0 0.0\n"
                        f"0 {gam_a:.8e} 0.0 0.0\n"
                        f"0 0.0 0.0 0.0\n"
                        f"0 0.0 0.0 0.0\n"
                        f"*End\n"
                    )
                    with open(self.work_dir / "test.inp", "w") as f:
                        f.write(test_inp)

                    subprocess.run(
                        [str(self.driver_exe)], cwd=self.work_dir,
                        capture_output=True, env=env
                    )
                    cy_out = self.work_dir / out_name
                    if not cy_out.is_file():
                        self.log_emitted.emit(
                            f"Attenzione: ciclo {idx} a gamma = {gam_a:.2e} non ha prodotto output."
                        )
                        continue

                    raw_df = self._read_driver_out(cy_out)
                    # stran_4 e stress_4 sono la deformazione di taglio xy e la
                    # tensione di taglio xy. In geotecnica gamma = 2*eps_xy, ma il
                    # driver immagazzina gia' eps_xy (componente 4); useremo stran_4
                    # come gamma perche' il driver applica la deformazione di taglio
                    # come ampiezza, e la relazione G = tau/gamma e' coerente con
                    # l'ampiezza di stran_4 (vedi documento numgeo).
                    gamma = raw_df["stran_4"].values
                    tau = raw_df["stress_4"].values

                    g_ampl = (gamma.max() - gamma.min()) / 2.0
                    t_ampl = (tau.max() - tau.min()) / 2.0
                    G_sec = t_ampl / g_ampl if g_ampl > 0 else G0_val

                    # Area del ciclo di isteresi chiuso dW = \oint tau dgamma
                    dW = abs(trapz_fn(tau, gamma))
                    if t_ampl > 0 and g_ampl > 0:
                        D = dW / (2.0 * np.pi * t_ampl * g_ampl)
                    else:
                        D = 0.0

                    cy_records.append({
                        "gamma_a": g_ampl,
                        "tau_a_kPa": t_ampl,
                        "G_sec_kPa": G_sec,
                        "G_over_G0": G_sec / G0_val,
                        "damping_ratio": D,
                        "damping_pct": D * 100.0,
                    })
                    cycles_dict[g_ampl] = (gamma, tau, G_sec, D * 100.0)
                    self.log_emitted.emit(
                        f"   gamma_a = {g_ampl:9.2e} | G/G0 = {G_sec/G0_val:6.3f} | D = {D*100:5.2f}%"
                    )

                results["df_cy"] = pd.DataFrame(cy_records)
                results["cycles_dict"] = cycles_dict
                self.log_emitted.emit("-> Sweep ciclico non drenato completato.")

            self.progress_changed.emit(100, "Simulazione completata con successo!")
            self.finished_simulation.emit(results)

        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            self.error_occurred.emit(f"{e}\n\n{tb}")


# -----------------------------------------------------------------------------
# Finestra Principale GUI (PyQt6)
# -----------------------------------------------------------------------------
class HSBricksMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("numgeo - Hardening Soil (MN-Bricks) Driver & Calibration Studio v2")
        self.resize(1500, 900)

        self.driver_exe, self.calib_exe = find_executables()
        self.exp_tx_df: Optional[pd.DataFrame] = None
        self.exp_cy_df: Optional[pd.DataFrame] = None
        self.sim_results: Optional[dict] = None

        self._init_ui()
        self._apply_preset("Glacial Till (Cudny & Truty 2020)")

    def _init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        # ---------------------------------------------------------------------
        # PANNELLO SINISTRO: Input e Controlli (Scrollabile)
        # ---------------------------------------------------------------------
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setMinimumWidth(440)
        left_scroll.setMaximumWidth(540)

        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setSpacing(10)

        # 1. Preset e File Parametri
        group_preset = QGroupBox("1. File Parametri & Preset Materiale")
        preset_layout = QVBoxLayout(group_preset)

        h_pre = QHBoxLayout()
        h_pre.addWidget(QLabel("Preset:"))
        self.combo_presets = QComboBox()
        self.combo_presets.addItems(list(PRESETS.keys()))
        self.combo_presets.currentTextChanged.connect(self._apply_preset)
        h_pre.addWidget(self.combo_presets)
        preset_layout.addLayout(h_pre)

        h_btn_par = QHBoxLayout()
        btn_load_p = QPushButton("Carica .inp...")
        btn_load_p.clicked.connect(self._load_parameters_file)
        btn_save_p = QPushButton("Salva .inp...")
        btn_save_p.clicked.connect(self._save_parameters_file)
        h_btn_par.addWidget(btn_load_p)
        h_btn_par.addWidget(btn_save_p)
        preset_layout.addLayout(h_btn_par)

        left_layout.addWidget(group_preset)

        # 2. Parametri Hardening Soil Bricks (16 parametri)
        group_params = QGroupBox("2. Parametri Costitutivi (HS-MN-Bricks)")
        p_layout = QGridLayout(group_params)
        p_layout.setSpacing(6)

        self.param_inputs: Dict[str, QDoubleSpinBox] = {}

        params_meta = [
            ("E50", "E50,ref [kPa]", 8500.0, 10.0, 1e7, "Rigidezza secante a q = 50% di q_f"),
            ("Eoed", "Eoed,ref [kPa]", 6150.0, 10.0, 1e7, "Rigidezza tangente edometrica a pref"),
            ("Eur", "Eur,ref [kPa]", 25750.0, 10.0, 1e7, "Rigidezza di scarico-ricarico a pref"),
            ("m", "m [-]", 0.70, 0.0, 1.5, "Esponente di dipendenza dallo stato tensionale"),
            ("c", "c [kPa]", 6.0, 0.0, 1e5, "Coesione efficace"),
            ("phi", "phi [deg]", 28.0, 0.0, 55.0, "Angolo di attrito efficace (Matsuoka-Nakai)"),
            ("psi", "psi [deg]", 6.0, 0.0, 45.0, "Angolo di dilatanza"),
            ("nu", "nu_ur [-]", 0.29, 0.0, 0.49, "Coefficiente di Poisson elastico scarico/ricarico"),
            ("pref", "pref [kPa]", 100.0, 1.0, 1000.0, "Pressione di riferimento (usualmente 100 kPa)"),
            ("K0nc", "K0,nc [-]", 0.80, 0.1, 1.5, "Coeff. di spinta a riposo per consolidazione normale"),
            ("Rf", "Rf [-]", 0.90, 0.5, 0.99, "Rapporto di rottura q_f / q_a"),
            ("Ei", "Ei,ref [kPa]", 15460.0, 10.0, 1e7, "Rigidezza tangenziale iniziale a pref"),
            ("alpha", "alpha [-]", 0.515, 0.01, 10.0, "Forma della superficie cap (calcolato da Eoed/K0)"),
            ("Hpp", "Hpp [kPa]", 9866.0, 10.0, 1e7, "Modulo di incrudimento del cap"),
            ("gamma07", "gamma_0.7 [-]", 3.0e-4, 1e-6, 1e-1, "Soglia di deformazione a G/G0 = 0.722"),
            ("G0", "G0,ref [kPa]", 60000.0, 10.0, 1e7, "Modulo di taglio elastico a piccolissime deformazioni")
        ]

        for i, (name, label, def_val, vmin, vmax, tip) in enumerate(params_meta):
            row = i // 2
            col = (i % 2) * 2

            lbl = QLabel(label)
            lbl.setToolTip(tip)
            spin = QDoubleSpinBox()
            spin.setRange(vmin, vmax)
            if name == "gamma07":
                spin.setDecimals(6)
                spin.setSingleStep(1e-5)
            elif name in ["m", "nu", "K0nc", "Rf", "alpha", "c", "phi", "psi"]:
                spin.setDecimals(3)
                spin.setSingleStep(0.05)
            else:
                spin.setDecimals(1)
                spin.setSingleStep(500.0)

            spin.setValue(def_val)
            spin.setToolTip(tip)

            self.param_inputs[name] = spin
            p_layout.addWidget(lbl, row, col)
            p_layout.addWidget(spin, row, col + 1)

        # Bottone per calibrare alpha e Hpp con il tool
        btn_calc_alpha = QPushButton("Calcola alpha & Hpp (numgeo-calibration)")
        btn_calc_alpha.setToolTip("Esegue numgeo-hs-bricks-calibration.exe per ottimizzare alpha e Hpp da Eoed e K0nc")
        btn_calc_alpha.clicked.connect(self._run_cap_calibration)
        p_layout.addWidget(btn_calc_alpha, len(params_meta) // 2 + 1, 0, 1, 4)

        left_layout.addWidget(group_params)

        # 3. Impostazioni Prove Meccaniche (con TX-CID, TX-CIU, ciclico)
        group_tests = QGroupBox("3. Condizioni di Prova & Driver Setup")
        t_layout = QGridLayout(group_tests)
        t_layout.setSpacing(6)

        t_layout.addWidget(QLabel("Confinamento p0' [kPa]:"), 0, 0)
        self.spin_p0 = QDoubleSpinBox()
        self.spin_p0.setRange(5.0, 5000.0)
        self.spin_p0.setValue(100.0)
        t_layout.addWidget(self.spin_p0, 0, 1)

        t_layout.addWidget(QLabel("Deformaz. assiale target [%]:"), 1, 0)
        self.spin_eps1 = QDoubleSpinBox()
        # Range NEGATIVO: per compressione, in linea con la convenzione GUI
        self.spin_eps1.setRange(-60.0, -1.0)
        self.spin_eps1.setValue(-25.0)
        self.spin_eps1.setToolTip("Valore NEGATIVO per compressione. Lo stesso target viene usato per TX-CID e TX-CIU.")
        t_layout.addWidget(self.spin_eps1, 1, 1)

        t_layout.addWidget(QLabel("N. incrementi triassiale:"), 2, 0)
        self.spin_ninc_tx = QSpinBox()
        self.spin_ninc_tx.setRange(100, 20000)
        self.spin_ninc_tx.setValue(2500)
        self.spin_ninc_tx.setSingleStep(500)
        t_layout.addWidget(self.spin_ninc_tx, 2, 1)

        # Checkbox prove triassiali
        self.chk_tx_cd = QCheckBox("TX-CID  (Consolidated Isotropic Drained, *TriaxialE1)")
        self.chk_tx_cd.setChecked(True)
        self.chk_tx_cd.setToolTip(
            "Prova triassiale drenata: controllo di deformazione assiale eps_a.\n"
            "L'output fornisce q, p' (efficace), eps_v (volumetrica)."
        )
        t_layout.addWidget(self.chk_tx_cd, 3, 0, 1, 2)

        self.chk_tx_cu = QCheckBox("TX-CIU  (Consolidated Isotropic Undrained, *TriaxialUEq)")
        self.chk_tx_cu.setChecked(False)
        self.chk_tx_cu.setToolTip(
            "Prova triassiale non drenata: controllo di deformazione deviatorica eps_q\n"
            "con eps_v = 0. L'output fornisce q, p' (efficace), ∆u (pressione di poro).\n"
            "Calcoliamo ∆u assumendo cell pressure costante = p0' (condizione di prova lab)."
        )
        t_layout.addWidget(self.chk_tx_cu, 4, 0, 1, 2)

        # Checkbox ciclico
        self.chk_cy = QCheckBox("Ciclico Non Drenato per G/G0 (*CirculatingLoad, taglio xy)")
        self.chk_cy.setChecked(True)
        self.chk_cy.setToolTip(
            "Sweep di ampiezze cicliche di deformazione di taglio (componente 4 = xy).\n"
            "Determina le curve G/G0-gamma e D-gamma e i cicli di isteresi tau-gamma.\n"
            "La prova di taglio semplice e' intrinsecamente non drenata sulla componente di taglio."
        )
        t_layout.addWidget(self.chk_cy, 5, 0, 1, 2)

        t_layout.addWidget(QLabel("N. ampiezze (punti sweep):"), 6, 0)
        self.spin_n_cycles = QSpinBox()
        self.spin_n_cycles.setRange(5, 30)
        self.spin_n_cycles.setValue(13)
        t_layout.addWidget(self.spin_n_cycles, 6, 1)

        t_layout.addWidget(QLabel("N. incrementi per ciclo:"), 7, 0)
        self.spin_ninc_cy = QSpinBox()
        self.spin_ninc_cy.setRange(50, 5000)
        self.spin_ninc_cy.setValue(250)
        self.spin_ninc_cy.setSingleStep(50)
        t_layout.addWidget(self.spin_ninc_cy, 7, 1)

        left_layout.addWidget(group_tests)

        # 4. Caricamento Dati Sperimentali di Laboratorio
        group_exp = QGroupBox("4. Dati di Laboratorio (Overlay Calibrazione)")
        exp_layout = QVBoxLayout(group_exp)

        h_exp_tx = QHBoxLayout()
        btn_load_exp_tx = QPushButton("Carica Triassiale (CSV)...")
        btn_load_exp_tx.clicked.connect(self._load_exp_triaxial)
        self.lbl_exp_tx = QLabel("Nessun file")
        self.lbl_exp_tx.setStyleSheet("color: gray;")
        h_exp_tx.addWidget(btn_load_exp_tx)
        h_exp_tx.addWidget(self.lbl_exp_tx)
        exp_layout.addLayout(h_exp_tx)

        h_exp_cy = QHBoxLayout()
        btn_load_exp_cy = QPushButton("Carica Dinamici (CSV)...")
        btn_load_exp_cy.clicked.connect(self._load_exp_dynamic)
        self.lbl_exp_cy = QLabel("Nessun file")
        self.lbl_exp_cy.setStyleSheet("color: gray;")
        h_exp_cy.addWidget(btn_load_exp_cy)
        h_exp_cy.addWidget(self.lbl_exp_cy)
        exp_layout.addLayout(h_exp_cy)

        btn_clear_exp = QPushButton("Rimuovi Dati Sperimentali")
        btn_clear_exp.clicked.connect(self._clear_exp_data)
        exp_layout.addWidget(btn_clear_exp)

        left_layout.addWidget(group_exp)

        # 5. Pulsante di Esecuzione e Stato
        self.btn_run = QPushButton("AVVIA SIMULAZIONE CON DRIVER")
        self.btn_run.setStyleSheet(
            "QPushButton { background-color: #0066cc; color: white; font-weight: bold; font-size: 13px; padding: 10px; border-radius: 5px; }"
            "QPushButton:hover { background-color: #0052a3; }"
            "QPushButton:disabled { background-color: #cccccc; }"
        )
        self.btn_run.clicked.connect(self._start_simulation)
        left_layout.addWidget(self.btn_run)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        left_layout.addWidget(self.progress_bar)

        self.txt_log = QTextEdit()
        self.txt_log.setMaximumHeight(110)
        self.txt_log.setReadOnly(True)
        self.txt_log.setFont(QFont("Consolas", 8))
        left_layout.addWidget(self.txt_log)

        left_scroll.setWidget(left_container)
        splitter.addWidget(left_scroll)

        # ---------------------------------------------------------------------
        # PANNELLO DESTRO: Grafici e Risultati (Tab Widget)
        # ---------------------------------------------------------------------
        self.tabs = QTabWidget()
        splitter.addWidget(self.tabs)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        # Tab 1: Curve Triassiali Monotoniche (TX-CID + TX-CIU)
        self.tab_tx = QWidget()
        layout_tab_tx = QVBoxLayout(self.tab_tx)
        self.fig_tx = Figure(figsize=(11, 7), dpi=100)
        self.canvas_tx = FigureCanvasQTAgg(self.fig_tx)
        self.toolbar_tx = NavigationToolbar2QT(self.canvas_tx, self.tab_tx)
        layout_tab_tx.addWidget(self.toolbar_tx)
        layout_tab_tx.addWidget(self.canvas_tx)
        self.tabs.addTab(self.tab_tx, "Prove Triassiali (TX-CID + TX-CIU)")

        # Tab 2: Curve Dinamiche (G/G0 e D)
        self.tab_cy = QWidget()
        layout_tab_cy = QVBoxLayout(self.tab_cy)
        self.fig_cy = Figure(figsize=(11, 5), dpi=100)
        self.canvas_cy = FigureCanvasQTAgg(self.fig_cy)
        self.toolbar_cy = NavigationToolbar2QT(self.canvas_cy, self.tab_cy)
        layout_tab_cy.addWidget(self.toolbar_cy)
        layout_tab_cy.addWidget(self.canvas_cy)
        self.tabs.addTab(self.tab_cy, "Geotecnica Sismica (G/G0, D)")

        # Tab 3: Cicli Isteretici tau - gamma
        self.tab_hyst = QWidget()
        layout_tab_hyst = QVBoxLayout(self.tab_hyst)
        h_hyst_ctrl = QHBoxLayout()
        h_hyst_ctrl.addWidget(QLabel("Seleziona Ampiezza di Scorrimento gamma_a:"))
        self.combo_amplitudes = QComboBox()
        self.combo_amplitudes.currentIndexChanged.connect(self._update_hysteresis_plot)
        h_hyst_ctrl.addWidget(self.combo_amplitudes)
        h_hyst_ctrl.addStretch()
        layout_tab_hyst.addLayout(h_hyst_ctrl)

        self.fig_hyst = Figure(figsize=(8, 5), dpi=100)
        self.canvas_hyst = FigureCanvasQTAgg(self.fig_hyst)
        self.toolbar_hyst = NavigationToolbar2QT(self.canvas_hyst, self.tab_hyst)
        layout_tab_hyst.addWidget(self.toolbar_hyst)
        layout_tab_hyst.addWidget(self.canvas_hyst)
        self.tabs.addTab(self.tab_hyst, "Cicli di Isteresi (tau - gamma)")

        # Tab 4: Tabella Dati ed Esportazione
        self.tab_data = QWidget()
        layout_tab_data = QVBoxLayout(self.tab_data)

        # Sotto-tabella per switch tra TX-CID, TX-CIU, ciclico
        self.tabs_data = QTabWidget()
        layout_tab_data.addWidget(self.tabs_data)

        # Sotto-tab 1: TX-CID
        self.tab_data_cd = QWidget()
        lo_cd = QVBoxLayout(self.tab_data_cd)
        self.table_tx_cd = QTableWidget()
        lo_cd.addWidget(self.table_tx_cd)
        self.tabs_data.addTab(self.tab_data_cd, "TX-CID")

        # Sotto-tab 2: TX-CIU
        self.tab_data_cu = QWidget()
        lo_cu = QVBoxLayout(self.tab_data_cu)
        self.table_tx_cu = QTableWidget()
        lo_cu.addWidget(self.table_tx_cu)
        self.tabs_data.addTab(self.tab_data_cu, "TX-CIU")

        # Sotto-tab 3: Ciclico
        self.tab_data_cy = QWidget()
        lo_cy = QVBoxLayout(self.tab_data_cy)
        self.table_cy = QTableWidget()
        lo_cy.addWidget(self.table_cy)
        self.tabs_data.addTab(self.tab_data_cy, "Ciclico")

        # Pulsanti esportazione
        h_export = QHBoxLayout()
        btn_exp_tx = QPushButton("Esporta CSV Triassiale...")
        btn_exp_tx.clicked.connect(self._export_tx_csv)
        btn_exp_cy = QPushButton("Esporta CSV Dinamico (G & D)...")
        btn_exp_cy.clicked.connect(self._export_cy_csv)
        btn_exp_plots = QPushButton("Esporta Tutti i Grafici (PNG)...")
        btn_exp_plots.clicked.connect(self._export_all_plots)
        btn_open_excel = QPushButton("Genera & Apri Foglio Excel (.xlsx)")
        btn_open_excel.setStyleSheet("QPushButton { font-weight: bold; color: #1B365D; }")
        btn_open_excel.clicked.connect(self._open_excel_sheet)
        h_export.addWidget(btn_exp_tx)
        h_export.addWidget(btn_exp_cy)
        h_export.addWidget(btn_exp_plots)
        h_export.addWidget(btn_open_excel)
        h_export.addStretch()
        layout_tab_data.addLayout(h_export)

        self.tabs.addTab(self.tab_data, "Tabelle Risultati")

        self._init_empty_plots()

    # -------------------------------------------------------------------------
    # Inizializzazione Grafici Vuoti
    # -------------------------------------------------------------------------
    def _init_empty_plots(self):
        """Inizializza (o resetta) tutti i grafici a layout vuoto con etichette.
        Chiamato all'avvio e all'inizio di ogni nuova simulazione per evitare
        che diagrammi di run precedenti restino visibili (bug fix)."""
        # --- Triax (2x2: q-eps_s, q-p' (eff+tot), eps_v-eps_a, ∆u-eps_a) ---
        self.fig_tx.clear()
        axes_tx = self.fig_tx.subplots(2, 2)
        titles = [
            r"$q - \varepsilon_a$ (risposta deviatorica)",
            r"$q - p$ Percorso Tensionale (efficace + totale)",
            r"$\varepsilon_v$ vs $\varepsilon_a$ (TX-CID) / $\Delta u$ vs $\varepsilon_a$ (TX-CIU)",
            r"$p'$ vs $\varepsilon_a$ (evoluzione pressione efficace)",
        ]
        xlabels = [
            r"$\varepsilon_a$ [%]",
            r"$p$ (eff. o tot.) [kPa]",
            r"$\varepsilon_a$ [%]",
            r"$\varepsilon_a$ [%]",
        ]
        ylabels = [
            r"$q$ [kPa]",
            r"$q$ [kPa]",
            r"$\varepsilon_v$ [%] oppure $\Delta u$ [kPa]",
            r"$p'$ [kPa]",
        ]
        for ax, t, xl, yl in zip(axes_tx.flat, titles, xlabels, ylabels):
            ax.set_title(t, fontsize=10)
            ax.set_xlabel(xl)
            ax.set_ylabel(yl)
            ax.grid(True, ls=":", alpha=0.6)
        self.fig_tx.tight_layout()
        self.canvas_tx.draw_idle()

        # --- Dynamic (1x2: G/G0-gamma, D-gamma) ---
        self.fig_cy.clear()
        ax1, ax2 = self.fig_cy.subplots(1, 2)
        ax1.set_xscale("log")
        ax1.set_title(r"Decadimento del Modulo $G/G_0 - \gamma$")
        ax1.set_xlabel(r"Ampiezza di scorrimento $\gamma_a$ [-]")
        ax1.set_ylabel(r"$G / G_0$ [-]")
        ax1.grid(True, which="both", ls=":", alpha=0.6)

        ax2.set_xscale("log")
        ax2.set_title(r"Curva di Smorzamento Isteretico $D - \gamma$")
        ax2.set_xlabel(r"Ampiezza di scorrimento $\gamma_a$ [-]")
        ax2.set_ylabel(r"Rapporto di smorzamento $D$ [%]")
        ax2.grid(True, which="both", ls=":", alpha=0.6)
        self.fig_cy.tight_layout()
        self.canvas_cy.draw_idle()

        # --- Hysteresis ---
        self.fig_hyst.clear()
        ax_h = self.fig_hyst.add_subplot(1, 1, 1)
        ax_h.set_title(r"Ciclo di Isteresi $\tau - \gamma$")
        ax_h.set_xlabel(r"Deformazione di scorrimento $\gamma$ [-]")
        ax_h.set_ylabel(r"Tensione tangenziale $\tau$ [kPa]")
        ax_h.grid(True, ls=":", alpha=0.6)
        self.fig_hyst.tight_layout()
        self.canvas_hyst.draw_idle()

        # Reset combo ampiezze
        self.combo_amplitudes.clear()
        # Reset tabelle
        for tbl in (self.table_tx_cd, self.table_tx_cu, self.table_cy):
            tbl.clear()
            tbl.setRowCount(0)
            tbl.setColumnCount(0)

    # -------------------------------------------------------------------------
    # Gestione Preset e Parametri
    # -------------------------------------------------------------------------
    def _apply_preset(self, preset_name: str):
        if preset_name in PRESETS:
            data = PRESETS[preset_name]
            for k, v in data.items():
                if k in self.param_inputs:
                    self.param_inputs[k].setValue(v)
            self._log(f"Applicato preset: {preset_name}")

    def _get_current_params(self) -> dict:
        return {k: spin.value() for k, spin in self.param_inputs.items()}

    def _load_parameters_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Carica parameters.inp", "",
            "Input files (*.inp);;Tutti i file (*.*)"
        )
        if not file_path:
            return
        try:
            with open(file_path, "r") as f:
                lines = [l.strip() for l in f if l.strip() and not l.strip().startswith("#")]
            for i, name in enumerate(PARAM_NAMES):
                idx = 2 + i
                if idx < len(lines):
                    val = float(lines[idx].split()[0].replace("d", "e").replace("D", "E"))
                    if name in self.param_inputs:
                        self.param_inputs[name].setValue(val)
            self._log(f"Caricati parametri da: {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Impossibile leggere il file:\n{e}")

    def _save_parameters_file(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Salva parameters.inp", "parameters.inp",
            "Input files (*.inp);;Tutti i file (*.*)"
        )
        if not file_path:
            return
        try:
            params = self._get_current_params()
            with open(file_path, "w") as f:
                f.write("Hardening-Soil-MN-Bricks     cmname\n")
                f.write("16           nprops\n")
                for name in PARAM_NAMES:
                    val = params.get(name, 0.0)
                    f.write(f"{val:<16.6e} {name}\n")
            self._log(f"Salvati parametri in: {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Impossibile salvare il file:\n{e}")

    # -------------------------------------------------------------------------
    # Calibrazione Automatica di Alpha e Hpp
    # -------------------------------------------------------------------------
    def _run_cap_calibration(self):
        if not self.calib_exe or not self.calib_exe.is_file():
            QMessageBox.warning(
                self, "Avviso",
                "numgeo-hs-bricks-calibration.exe non trovato nel repository."
            )
            return

        temp_dir = get_project_root() / "temp_calibration"
        temp_dir.mkdir(parents=True, exist_ok=True)

        params = self._get_current_params()
        with open(temp_dir / "parameters.inp", "w") as f:
            f.write("Hardening-Soil-MN-Bricks     cmname\n")
            f.write("16           nprops\n")
            for name in PARAM_NAMES:
                f.write(f"{params.get(name, 0.0):<16.6e} {name}\n")

        env = get_intel_rt_env()
        try:
            self._log("Esecuzione calibrazione cap (alpha & Hpp) in corso...")
            res = subprocess.run(
                [str(self.calib_exe)], cwd=temp_dir,
                input="parameters.inp\n", text=True, capture_output=True, env=env
            )
            stdout = res.stdout

            alpha_val, hpp_val = None, None
            for line in stdout.splitlines():
                if "alpha (props(13))" in line:
                    alpha_val = float(line.split("=")[1].strip())
                elif "Hpp   (props(14))" in line:
                    hpp_val = float(line.split("=")[1].strip())

            if alpha_val is not None and hpp_val is not None:
                self.param_inputs["alpha"].setValue(alpha_val)
                self.param_inputs["Hpp"].setValue(hpp_val)
                self._log(f"-> Calibrazione completata: alpha = {alpha_val:.4f}, Hpp = {hpp_val:.1f} kPa")
                QMessageBox.information(
                    self, "Calibrazione Riuscita",
                    f"Calibrazione completata con successo!\n\n"
                    f"alpha = {alpha_val:.5f}\n"
                    f"Hpp   = {hpp_val:.2f} kPa\n\n"
                    f"I valori sono stati inseriti automaticamente nei campi del modello."
                )
            else:
                QMessageBox.warning(
                    self, "Attenzione",
                    f"Impossibile interpretare l'output di calibrazione:\n{stdout}"
                )
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Errore durante l'esecuzione:\n{e}")

    # -------------------------------------------------------------------------
    # Dati Sperimentali di Laboratorio (Overlay)
    # -------------------------------------------------------------------------
    def _load_exp_triaxial(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Carica CSV Triassiale", "",
            "CSV Files (*.csv);;All Files (*.*)"
        )
        if not file_path:
            return
        try:
            self.exp_tx_df = pd.read_csv(file_path)
            self.lbl_exp_tx.setText(Path(file_path).name)
            self.lbl_exp_tx.setStyleSheet("color: green; font-weight: bold;")
            self._log(f"Caricati dati triassiali da: {file_path}")
            if self.sim_results and ("df_tx_cd" in self.sim_results or "df_tx_cu" in self.sim_results):
                self._plot_triaxial()
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Impossibile caricare il file:\n{e}")

    def _load_exp_dynamic(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Carica CSV Dinamico", "",
            "CSV Files (*.csv);;All Files (*.*)"
        )
        if not file_path:
            return
        try:
            self.exp_cy_df = pd.read_csv(file_path)
            self.lbl_exp_cy.setText(Path(file_path).name)
            self.lbl_exp_cy.setStyleSheet("color: green; font-weight: bold;")
            self._log(f"Caricati dati dinamici da: {file_path}")
            if self.sim_results and "df_cy" in self.sim_results:
                self._plot_dynamic(self.sim_results["df_cy"])
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Impossibile caricare il file:\n{e}")

    def _clear_exp_data(self):
        self.exp_tx_df = None
        self.exp_cy_df = None
        self.lbl_exp_tx.setText("Nessun file")
        self.lbl_exp_tx.setStyleSheet("color: gray;")
        self.lbl_exp_cy.setText("Nessun file")
        self.lbl_exp_cy.setStyleSheet("color: gray;")
        self._log("Dati sperimentali rimossi.")
        if self.sim_results:
            if "df_tx_cd" in self.sim_results or "df_tx_cu" in self.sim_results:
                self._plot_triaxial()
            if "df_cy" in self.sim_results:
                self._plot_dynamic(self.sim_results["df_cy"])

    # -------------------------------------------------------------------------
    # Esecuzione Simulazione
    # -------------------------------------------------------------------------
    def _start_simulation(self):
        if not self.driver_exe or not self.driver_exe.is_file():
            QMessageBox.critical(
                self, "Errore",
                "IncrementalDriver.exe non trovato. Verificare il file."
            )
            return

        run_tx_cd = self.chk_tx_cd.isChecked()
        run_tx_cu = self.chk_tx_cu.isChecked()
        run_cy = self.chk_cy.isChecked()

        if not (run_tx_cd or run_tx_cu or run_cy):
            QMessageBox.warning(
                self, "Attenzione",
                "Selezionare almeno una prova da eseguire (TX-CID, TX-CIU o Ciclico)."
            )
            return

        # Bug fix: cancella tutti i grafici e resetta lo stato visivo PRIMA
        # di avviare una nuova simulazione. In questo modo non rimangono
        # plot di run precedenti se la prova corrispondente non viene eseguita.
        self._init_empty_plots()
        self.sim_results = None
        self.txt_log.clear()

        self.btn_run.setEnabled(False)
        self.progress_bar.setValue(0)
        work_dir = get_project_root() / "gui_work_dir"

        self.worker = SimulationWorker(
            driver_exe=self.driver_exe,
            params=self._get_current_params(),
            run_tx_cd=run_tx_cd,
            run_tx_cu=run_tx_cu,
            run_cy=run_cy,
            p0=self.spin_p0.value(),
            eps1_target=self.spin_eps1.value(),
            ninc_tx=self.spin_ninc_tx.value(),
            n_cycles=self.spin_n_cycles.value(),
            gamma_min=1.0e-6,
            gamma_max=1.0e-2,
            ninc_cy=self.spin_ninc_cy.value(),
            work_dir=work_dir
        )
        self.worker.progress_changed.connect(self._on_progress)
        self.worker.log_emitted.connect(self._log)
        self.worker.finished_simulation.connect(self._on_simulation_finished)
        self.worker.error_occurred.connect(self._on_simulation_error)
        self.worker.start()

    def _on_progress(self, val: int, msg: str):
        self.progress_bar.setValue(val)
        self.statusBar().showMessage(msg)

    def _on_simulation_error(self, err_msg: str):
        self.btn_run.setEnabled(True)
        self.progress_bar.setValue(0)
        self.statusBar().showMessage("Errore durante la simulazione.")
        QMessageBox.critical(
            self, "Errore di Simulazione",
            f"Si e' verificato un errore:\n{err_msg}"
        )

    def _on_simulation_finished(self, results: dict):
        self.btn_run.setEnabled(True)
        self.sim_results = results
        self.statusBar().showMessage("Simulazione completata!")

        # Plot Triassiali (TX-CID e/o TX-CIU, sovrapposti)
        if "df_tx_cd" in results or "df_tx_cu" in results:
            self._plot_triaxial()

        # Plot Dinamico
        if "df_cy" in results:
            self._plot_dynamic(results["df_cy"])

        # Aggiorna combo ampiezze per cicli di isteresi
        if "cycles_dict" in results:
            self.combo_amplitudes.blockSignals(True)
            self.combo_amplitudes.clear()
            for gam_a in results["cycles_dict"].keys():
                self.combo_amplitudes.addItem(f"{gam_a:.2e}")
            self.combo_amplitudes.blockSignals(False)
            if self.combo_amplitudes.count() > 0:
                # Seleziona un'ampiezza intermedia (es. 1e-4 o 1e-3)
                mid_idx = min(len(results["cycles_dict"]) // 2, self.combo_amplitudes.count() - 1)
                self.combo_amplitudes.setCurrentIndex(mid_idx)
                self._update_hysteresis_plot()

        # Popola tabelle
        if "df_tx_cd" in results:
            self._populate_tx_table(self.table_tx_cd, results["df_tx_cd"], tx_type="CD")
        if "df_tx_cu" in results:
            self._populate_tx_table(self.table_tx_cu, results["df_tx_cu"], tx_type="CU")
        if "df_cy" in results:
            self._populate_table_cy(results["df_cy"])

        QMessageBox.information(
            self, "Successo",
            "Simulazione completata con successo!\n"
            "Tutti i grafici e le tabelle sono stati aggiornati."
        )

    # -------------------------------------------------------------------------
    # Visualizzazione Grafici
    # -------------------------------------------------------------------------
    def _plot_triaxial(self):
        """Disegna i 4 pannelli delle prove triassiali.
        Se sia TX-CID che TX-CIU sono presenti, vengono sovrapposte con colori
        diversi per confronto diretto.
        """
        self.fig_tx.clear()
        axes = self.fig_tx.subplots(2, 2)

        df_cd = self.sim_results.get("df_tx_cd") if self.sim_results else None
        df_cu = self.sim_results.get("df_tx_cu") if self.sim_results else None

        # Colori e label
        cd_color = "#1f77b4"  # blu
        cu_color = "#d62728"  # rosso
        cu_tot_color = "#ff7f0e"  # arancio (per p totale)

        # Pannello 1: q vs eps_a (deviatorica)
        ax = axes[0, 0]
        if df_cd is not None:
            ax.plot(df_cd["eps_s_pct"], df_cd["q_kPa"], color=cd_color,
                    lw=2, label="TX-CID (sim)")
        if df_cu is not None:
            ax.plot(df_cu["eps_s_pct"], df_cu["q_kPa"], color=cu_color,
                    lw=2, label="TX-CIU (sim)")
        ax.set_title(r"$q - \varepsilon_s$ Risposta Deviatorica", fontsize=10)
        ax.set_xlabel(r"Deformazione deviatorica $\varepsilon_s$ [%]")
        ax.set_ylabel(r"Tensione deviatrice $q$ [kPa]")
        ax.grid(True, ls=":", alpha=0.6)
        ax.legend(loc="best", fontsize=8)

        # Pannello 2: q vs p (percorso tensionale)
        ax = axes[0, 1]
        if df_cd is not None:
            # Per TX-CID: p' = p (totale = efficace in drenato)
            ax.plot(df_cd["p_eff_kPa"], df_cd["q_kPa"], color=cd_color,
                    lw=2, label="TX-CID: p' (eff.)")
        if df_cu is not None:
            ax.plot(df_cu["p_eff_kPa"], df_cu["q_kPa"], color=cu_color,
                    lw=2, label="TX-CIU: p' (eff.)")
            ax.plot(df_cu["p_total_kPa"], df_cu["q_kPa"], color=cu_tot_color,
                    lw=1.5, ls="--", label="TX-CIU: p (tot.)")
            # Linea di rottura (M = 6 sin(phi)/(3-sin(phi)) per MN non e' qui
            # applicato direttamente; mostriamo la TSP = p0 + q/3)
        ax.set_title(r"$q - p$ Percorso Tensionale", fontsize=10)
        ax.set_xlabel(r"Tensione media $p$ (efficace o totale) [kPa]")
        ax.set_ylabel(r"Tensione deviatrice $q$ [kPa]")
        ax.grid(True, ls=":", alpha=0.6)
        ax.legend(loc="best", fontsize=8)

        # Pannello 3: eps_v (TX-CID) e ∆u (TX-CIU) vs eps_a
        ax = axes[1, 0]
        if df_cd is not None:
            ax.plot(df_cd["eps_s_pct"], df_cd["eps_v_pct"], color=cd_color,
                    lw=2, label=r"TX-CID: $\varepsilon_v$")
        if df_cu is not None:
            # Usa asse secondario per ∆u (kPa) che ha unita' diversa da eps_v (%)
            ax2 = ax.twinx()
            ax2.plot(df_cu["eps_s_pct"], df_cu["delta_u_kPa"], color=cu_color,
                     lw=2, ls="-", label=r"TX-CIU: $\Delta u$")
            ax2.set_ylabel(r"Pressione di poro $\Delta u$ [kPa]", color=cu_color)
            ax2.tick_params(axis="y", colors=cu_color)
            ax2.grid(False)
            # Unione delle legende
            h1, l1 = ax.get_legend_handles_labels()
            h2, l2 = ax2.get_legend_handles_labels()
            ax.legend(h1 + h2, l1 + l2, loc="best", fontsize=8)
        else:
            ax.legend(loc="best", fontsize=8)
        ax.set_title(r"Risposta Volumetrica (CD) / Pressione di Poro (CU)", fontsize=10)
        ax.set_xlabel(r"Deformazione deviatorica $\varepsilon_s$ [%]")
        ax.set_ylabel(r"Deformazione volumetrica $\varepsilon_v$ [%]", color=cd_color)
        ax.tick_params(axis="y", colors=cd_color)
        ax.grid(True, ls=":", alpha=0.6)

        # Pannello 4: p' vs eps_a (evoluzione pressione efficace)
        ax = axes[1, 1]
        if df_cd is not None:
            ax.plot(df_cd["eps_s_pct"], df_cd["p_eff_kPa"], color=cd_color,
                    lw=2, label="TX-CID: p'")
        if df_cu is not None:
            ax.plot(df_cu["eps_s_pct"], df_cu["p_eff_kPa"], color=cu_color,
                    lw=2, label="TX-CIU: p'")
            ax.axhline(self.spin_p0.value(), color="gray", ls=":", lw=1,
                       label=r"$p_0'$ iniziale")
        ax.set_title(r"Evoluzione di $p'$ (pressione efficace)", fontsize=10)
        ax.set_xlabel(r"Deformazione deviatorica $\varepsilon_s$ [%]")
        ax.set_ylabel(r"Tensione media efficace $p'$ [kPa]")
        ax.grid(True, ls=":", alpha=0.6)
        ax.legend(loc="best", fontsize=8)

        # Overlay dati sperimentali di laboratorio (se disponibili)
        if self.exp_tx_df is not None:
            ex = self.exp_tx_df
            if "eps_s_pct" in ex and "q_kPa" in ex:
                axes[0, 0].plot(ex["eps_s_pct"], ex["q_kPa"], "ko", ms=4, label="Lab")
            if "p_eff_kPa" in ex and "q_kPa" in ex:
                axes[0, 1].plot(ex["p_eff_kPa"], ex["q_kPa"], "ko", ms=4, label="Lab")
            if "eps_s_pct" in ex and "eps_v_pct" in ex:
                axes[1, 0].plot(ex["eps_s_pct"], ex["eps_v_pct"], "ko", ms=4, label="Lab")
            if "eps_s_pct" in ex and "p_eff_kPa" in ex:
                axes[1, 1].plot(ex["eps_s_pct"], ex["p_eff_kPa"], "ko", ms=4, label="Lab")
            for ax in axes.flat:
                ax.legend(loc="best", fontsize=8)

        self.fig_tx.tight_layout()
        self.canvas_tx.draw_idle()
        self.canvas_tx.draw()

    def _plot_dynamic(self, df_cy: pd.DataFrame):
        self.fig_cy.clear()
        ax1, ax2 = self.fig_cy.subplots(1, 2)

        gamma07 = self.param_inputs["gamma07"].value()
        gam_theory = np.logspace(-6, -2, 200)
        # Formula della curva target backbone di Hardening Soil small-strain
        # G/G0 = 1 / (1 + (3/7)*(gamma/gamma_0.7))
        G_G0_theory = 1.0 / (1.0 + (3.0 / 7.0) * (gam_theory / gamma07))

        # Pannel 1: G/G0
        ax1.plot(df_cy["gamma_a"], df_cy["G_over_G0"], "bs-", lw=1.8, ms=5,
                 label="HS-MN-Bricks (Driver)")
        ax1.plot(gam_theory, G_G0_theory, "k--", lw=1.2,
                 label=rf"Target Backbone ($\gamma_{{0.7}}={gamma07:.1e}$)")
        ax1.set_xscale("log")
        ax1.set_title(r"Decadimento Modulo di Taglio $G/G_0 - \gamma$")
        ax1.set_xlabel(r"Ampiezza di scorrimento $\gamma_a$ [-]")
        ax1.set_ylabel(r"$G / G_0$ [-]")
        ax1.set_ylim(0, 1.05)
        ax1.grid(True, which="both", ls=":", alpha=0.6)

        # Pannel 2: Damping D [%]
        ax2.plot(df_cy["gamma_a"], df_cy["damping_pct"], "rs-", lw=1.8, ms=5,
                 label="HS-MN-Bricks (Driver)")
        ax2.set_xscale("log")
        ax2.set_title(r"Curva di Smorzamento Isteretico $D - \gamma$")
        ax2.set_xlabel(r"Ampiezza di scorrimento $\gamma_a$ [-]")
        ax2.set_ylabel(r"Smorzamento $D$ [%]")
        ax2.set_ylim(0, max(50.0, df_cy["damping_pct"].max() * 1.15))
        ax2.grid(True, which="both", ls=":", alpha=0.6)

        # Overlay Dati Sperimentali
        if self.exp_cy_df is not None:
            ex = self.exp_cy_df
            if "gamma" in ex and "G_over_G0" in ex:
                ax1.plot(ex["gamma"], ex["G_over_G0"], "k^", ms=6,
                         label="Colonna Risonante (Lab)")
            if "gamma" in ex and "damping_pct" in ex:
                ax2.plot(ex["gamma"], ex["damping_pct"], "k^", ms=6,
                         label="Colonna Risonante (Lab)")

        ax1.legend(loc="best", fontsize=8)
        ax2.legend(loc="best", fontsize=8)

        self.fig_cy.tight_layout()
        self.canvas_cy.draw_idle()
        self.canvas_cy.draw()

    def _update_hysteresis_plot(self):
        if not self.sim_results or "cycles_dict" not in self.sim_results:
            return

        text = self.combo_amplitudes.currentText()
        if not text:
            return

        try:
            target_gam = float(text)
        except ValueError:
            return

        cycles_dict = self.sim_results["cycles_dict"]
        # Trova la chiave piu' vicina
        keys = list(cycles_dict.keys())
        closest_key = min(keys, key=lambda k: abs(k - target_gam))
        gamma, tau, G_sec, D_pct = cycles_dict[closest_key]

        self.fig_hyst.clear()
        ax = self.fig_hyst.add_subplot(1, 1, 1)

        ax.plot(gamma, tau, "b-", lw=2,
                label=rf"Ciclo HS-Bricks ($\gamma_a={closest_key:.2e}$)")
        ax.fill(gamma, tau, color="lightblue", alpha=0.35,
                label=rf"Area Dissipata $\Delta W$ ($D={D_pct:.1f}\%$)")

        # Linea secante
        g_max, t_max = gamma.max(), tau.max()
        g_min, t_min = gamma.min(), tau.min()
        ax.plot([g_min, g_max], [t_min, t_max], "r--", lw=1.2,
                label=rf"Pendenza Secante $G_{{sec}} = {G_sec:.0f}\,$kPa")

        ax.set_title(rf"Ciclo di Isteresi $\tau - \gamma$ per $\gamma_a = {closest_key:.2e}$")
        ax.set_xlabel(r"Deformazione di scorrimento $\gamma$ [-]")
        ax.set_ylabel(r"Tensione tangenziale $\tau$ [kPa]")
        ax.grid(True, ls=":", alpha=0.6)
        ax.legend(loc="best", fontsize=8)

        self.fig_hyst.tight_layout()
        self.canvas_hyst.draw_idle()
        self.canvas_hyst.draw()

    # -------------------------------------------------------------------------
    # Dati Tabellari ed Esportazione
    # -------------------------------------------------------------------------
    def _populate_tx_table(self, table: QTableWidget, df: pd.DataFrame, tx_type: str):
        """Popola la tabella risultati per TX-CID o TX-CIU."""
        table.clear()
        # Scegli colonne in base al tipo
        if tx_type == "CD":
            cols = [
                ("eps_1_pct", r"$\varepsilon_1$ [%]"),
                ("eps_s_pct", r"$\varepsilon_s$ [%]"),
                ("eps_v_pct", r"$\varepsilon_v$ [%]"),
                ("p_eff_kPa", r"$p'$ [kPa]"),
                ("q_kPa", r"$q$ [kPa]"),
            ]
        else:  # CU
            cols = [
                ("eps_1_pct", r"$\varepsilon_1$ [%]"),
                ("eps_s_pct", r"$\varepsilon_s$ [%]"),
                ("p_eff_kPa", r"$p'$ [kPa]"),
                ("p_total_kPa", r"$p$ (tot.) [kPa]"),
                ("q_kPa", r"$q$ [kPa]"),
                ("delta_u_kPa", r"$\Delta u$ [kPa]"),
            ]
        table.setColumnCount(len(cols))
        table.setHorizontalHeaderLabels([lbl for _, lbl in cols])
        table.setRowCount(len(df))
        for row, (_, r) in enumerate(df.iterrows()):
            for c, (key, _) in enumerate(cols):
                val = r[key]
                if "pct" in key:
                    table.setItem(row, c, QTableWidgetItem(f"{val:.4f}"))
                else:
                    table.setItem(row, c, QTableWidgetItem(f"{val:.2f}"))
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

    def _populate_table_cy(self, df_cy: pd.DataFrame):
        self.table_cy.clear()
        self.table_cy.setColumnCount(5)
        self.table_cy.setHorizontalHeaderLabels([
            "gamma_a [-]", "tau_a [kPa]", "G_sec [kPa]", "G/G0 [-]", "Damping D [%]"
        ])
        self.table_cy.setRowCount(len(df_cy))
        for row, r in df_cy.iterrows():
            self.table_cy.setItem(row, 0, QTableWidgetItem(f"{r['gamma_a']:.3e}"))
            self.table_cy.setItem(row, 1, QTableWidgetItem(f"{r['tau_a_kPa']:.3f}"))
            self.table_cy.setItem(row, 2, QTableWidgetItem(f"{r['G_sec_kPa']:.1f}"))
            self.table_cy.setItem(row, 3, QTableWidgetItem(f"{r['G_over_G0']:.4f}"))
            self.table_cy.setItem(row, 4, QTableWidgetItem(f"{r['damping_pct']:.2f}"))
        self.table_cy.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

    def _export_tx_csv(self):
        """Esporta CSV combinato con TX-CID e TX-CIU se disponibili."""
        if not self.sim_results or ("df_tx_cd" not in self.sim_results and "df_tx_cu" not in self.sim_results):
            QMessageBox.warning(self, "Attenzione", "Nessun risultato triassiale disponibile.")
            return
        p, _ = QFileDialog.getSaveFileName(
            self, "Salva CSV Triassiale", "triaxial_curves.csv", "CSV Files (*.csv)"
        )
        if not p:
            return
        try:
            # Salva i due dataset (se presenti) in due file separati ma con nome correlato
            base = Path(p).with_suffix("")
            n_written = 0
            if "df_tx_cd" in self.sim_results:
                fn = f"{base}_TX-CD.csv"
                self.sim_results["df_tx_cd"].to_csv(fn, index=False)
                self._log(f"Esportati dati TX-CID in: {fn}")
                n_written += 1
            if "df_tx_cu" in self.sim_results:
                fn = f"{base}_TX-CU.csv"
                self.sim_results["df_tx_cu"].to_csv(fn, index=False)
                self._log(f"Esportati dati TX-CIU in: {fn}")
                n_written += 1
            if n_written == 0:
                QMessageBox.warning(self, "Attenzione", "Nessun dato triassiale da esportare.")
            else:
                QMessageBox.information(self, "Esportazione", f"Esportati {n_written} file CSV.")
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Impossibile esportare:\n{e}")

    def _export_cy_csv(self):
        if not self.sim_results or "df_cy" not in self.sim_results:
            QMessageBox.warning(self, "Attenzione", "Nessun risultato dinamico disponibile.")
            return
        p, _ = QFileDialog.getSaveFileName(
            self, "Salva CSV Dinamico", "cyclic_dynamic_curves.csv", "CSV Files (*.csv)"
        )
        if p:
            self.sim_results["df_cy"].to_csv(p, index=False)
            self._log(f"Esportati dati dinamici in: {p}")

    def _export_all_plots(self):
        out_folder = QFileDialog.getExistingDirectory(self, "Seleziona Cartella di Destinazione")
        if not out_folder:
            return
        try:
            p_out = Path(out_folder)
            self.fig_tx.savefig(p_out / "triaxial_curves.png", dpi=300, bbox_inches="tight")
            self.fig_cy.savefig(p_out / "dynamic_curves_G_D.png", dpi=300, bbox_inches="tight")
            self.fig_hyst.savefig(p_out / "hysteresis_loop.png", dpi=300, bbox_inches="tight")
            self._log(f"Salvati tutti i grafici in: {out_folder}")
            QMessageBox.information(
                self, "Esportazione Riuscita",
                f"Grafici esportati in alta risoluzione (300 DPI) in:\n{out_folder}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Impossibile salvare i grafici:\n{e}")

    def _open_excel_sheet(self):
        excel_path = get_project_root() / "Calibrazione_HS_Bricks_Curve_Dinamiche.xlsx"
        try:
            from scripts.generate_excel_calibration import build_excel_calibration_sheet
            build_excel_calibration_sheet(excel_path)
            self._log(f"Foglio Excel aggiornato: {excel_path}")
            if sys.platform == "win32":
                os.startfile(str(excel_path))
            else:
                import subprocess
                subprocess.run(["xdg-open", str(excel_path)])
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Impossibile aprire il file Excel:\n{e}")

    def _log(self, text: str):
        self.txt_log.append(text)
        # Auto-scroll to end
        sb = self.txt_log.verticalScrollBar()
        sb.setValue(sb.maximum())


# -----------------------------------------------------------------------------
# Main Application Entry Point
# -----------------------------------------------------------------------------
def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Font di sistema pulito
    font = QFont("Segoe UI", 9)
    app.setFont(font)

    window = HSBricksMainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
