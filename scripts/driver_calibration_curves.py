#!/usr/bin/env python3
"""
driver_calibration_curves.py
============================
Automated execution of the IncrementalDriver for Hardening-Soil-MN-Bricks (numgeo).
Extracts monotonic triaxial curves (q-eps_s, q-p', p'-eps_v) and cyclic/dynamic curves
(G/G0-gamma, D-gamma damping ratio) for calibration against laboratory tests
(Resonant Column, Cyclic Simple Shear, Triaxial).

Usage:
  python scripts/driver_calibration_curves.py --params examples/IncrementalDriver/parameters.inp --p0 100 --run-all
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple, List, Dict

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


# -----------------------------------------------------------------------------
# Configuration and Environment Setup
# -----------------------------------------------------------------------------
def get_intel_rt_env() -> Dict[str, str]:
    """Ensures Intel Fortran runtime DLLs are available in PATH."""
    env = os.environ.copy()
    candidate_paths = [
        r"C:\Users\uso\anaconda3\Library\bin",
        r"C:\Users\uso\anaconda3\bin",
        r"C:\Program Files (x86)\Intel\oneAPI\compiler\latest\windows\bin",
    ]
    current_path = env.get("PATH", "")
    for p in candidate_paths:
        if os.path.exists(p) and p not in current_path:
            current_path = p + os.pathsep + current_path
    env["PATH"] = current_path
    return env


def find_driver_executable(custom_path: Optional[str] = None) -> Path:
    """Finds the IncrementalDriver.exe executable."""
    if custom_path and Path(custom_path).is_file():
        return Path(custom_path).resolve()

    project_root = Path(__file__).resolve().parent.parent
    candidates = [
        project_root / "examples" / "IncrementalDriver" / "IncrementalDriver.exe",
        project_root / "VisualStudio" / "IncrementalDriver" / "x64" / "Release" / "IncrementalDriver.exe",
        project_root / "VisualStudio" / "IncrementalDriver" / "x64" / "Debug" / "IncrementalDriver.exe",
    ]
    for cand in candidates:
        if cand.is_file():
            return cand.resolve()

    raise FileNotFoundError(
        "IncrementalDriver.exe not found. Please compile it or specify path with --driver."
    )


def read_parameters(params_file: Path) -> Tuple[dict, float]:
    """Reads parameters.inp and extracts parameters dictionary and G0."""
    with open(params_file, "r") as f:
        lines = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]

    # cmname is line 0, nprops is line 1
    # props start at line 2
    param_names = [
        "E50", "Eoed", "Eur", "m", "c", "phi", "psi", "nu",
        "pref", "K0nc", "Rf", "Ei", "alpha", "Hpp", "gamma07", "G0"
    ]
    params = {}
    for i, name in enumerate(param_names):
        idx = 2 + i
        if idx < len(lines):
            val_str = lines[idx].split()[0].replace("d", "e").replace("D", "E")
            params[name] = float(val_str)

    G0 = params.get("G0", 60000.0)
    return params, G0


# -----------------------------------------------------------------------------
# Parser for Driver Output
# -----------------------------------------------------------------------------
def parse_driver_output(out_file: Path) -> pd.DataFrame:
    """Parses output file from IncrementalDriver (87 columns)."""
    cols = (
        ["time1", "time2"]
        + [f"stran_{k}" for k in range(1, 7)]
        + [f"stress_{k}" for k in range(1, 7)]
        + [f"statev_{k}" for k in range(1, 74)]
    )
    df = pd.read_csv(out_file, sep=r"\s+", skiprows=1, names=cols)
    return df


# -----------------------------------------------------------------------------
# Monotonic Drained Triaxial Test (TX-CD)
# -----------------------------------------------------------------------------
def run_triaxial_cd(
    driver_exe: Path,
    params_file: Path,
    initial_p0: float = 100.0,
    target_strain: float = -0.20,
    ninc: int = 3000,
    work_dir: Optional[Path] = None,
) -> pd.DataFrame:
    """
    Executes a drained triaxial compression test (TX-CD).
    Returns DataFrame with:
      - eps_1: Axial strain (%)
      - eps_3: Radial strain (%)
      - eps_s: Deviatoric shear strain (%) = 2/3 * (eps_1 - eps_3)
      - eps_v: Volumetric strain (%) = eps_1 + 2*eps_3
      - p_eff: Mean effective stress p' (kPa)
      - q: Deviatoric stress q (kPa)
      - Gm: Small-strain stiffness degradation ratio
    """
    if work_dir is None:
        work_dir = Path("triaxial_work").resolve()
    work_dir.mkdir(parents=True, exist_ok=True)

    # 1. parameters.inp
    shutil.copy(params_file, work_dir / "parameters.inp")

    # 2. initialconditions.inp (isotropic confinement p0)
    # Compression is negative
    init_content = f""" 6        ntens
 -{initial_p0:.4f}     stress(1)
 -{initial_p0:.4f}     stress(2)
 -{initial_p0:.4f}     stress(3)
  0       stress(4)
  0       stress(5)
  0       stress(ntens)
  73      nstatv    number of state variables
"""
    with open(work_dir / "initialconditions.inp", "w") as f:
        f.write(init_content)

    # 3. test.inp
    out_name = "output_CD.out"
    test_content = f"""{out_name}
*TriaxialE1
{ninc} 100 1.0
{target_strain:.6f}
*End
"""
    with open(work_dir / "test.inp", "w") as f:
        f.write(test_content)

    # Run driver
    env = get_intel_rt_env()
    res = subprocess.run([str(driver_exe)], cwd=work_dir, capture_output=True, text=True, env=env)
    out_file = work_dir / out_name
    if not out_file.is_file():
        raise RuntimeError(f"IncrementalDriver failed to produce {out_name}.\nStderr: {res.stderr}")

    raw_df = parse_driver_output(out_file)

    # Convert to standard soil mechanics conventions (Compression Positive)
    eps1 = -raw_df["stran_1"].values * 100.0  # %
    eps2 = -raw_df["stran_2"].values * 100.0  # %
    eps3 = -raw_df["stran_3"].values * 100.0  # %
    s1 = -raw_df["stress_1"].values           # kPa
    s2 = -raw_df["stress_2"].values           # kPa
    s3 = -raw_df["stress_3"].values           # kPa

    epsv = eps1 + eps2 + eps3                 # Volumetric strain (%)
    epss = (2.0 / 3.0) * (eps1 - eps3)        # Deviatoric shear strain (%)
    p_eff = (s1 + s2 + s3) / 3.0              # Mean effective stress (kPa)
    q = s1 - s3                               # Deviatoric stress (kPa)
    Gm = raw_df["statev_6"].values            # Stiffness ratio Gm

    res_df = pd.DataFrame({
        "eps_1_pct": eps1,
        "eps_3_pct": eps3,
        "eps_s_pct": epss,
        "eps_v_pct": epsv,
        "p_eff_kPa": p_eff,
        "q_kPa": q,
        "Gm": Gm,
    })
    return res_df


# -----------------------------------------------------------------------------
# Cyclic Simple Shear Amplitude Sweep (G/G0 and D vs gamma)
# -----------------------------------------------------------------------------
def run_cyclic_sweep(
    driver_exe: Path,
    params_file: Path,
    initial_p0: float = 100.0,
    amplitudes: Optional[np.ndarray] = None,
    ninc_per_cycle: int = 250,
    work_dir: Optional[Path] = None,
) -> pd.DataFrame:
    """
    Runs cyclic shear simulations across amplitudes gamma_a to determine:
      - G_sec: Secant shear modulus (kPa)
      - G/G0: Normalized shear modulus
      - D: Hysteretic damping ratio (%) from loop area dW / (2*pi*tau_a*gamma_a)
    """
    if work_dir is None:
        work_dir = Path("cyclic_work").resolve()
    work_dir.mkdir(parents=True, exist_ok=True)

    params, G0 = read_parameters(params_file)

    if amplitudes is None:
        # Range typical for Resonant Column and Cyclic Simple Shear: 10^-6 to 10^-2
        amplitudes = np.logspace(-6, -2, 13)

    shutil.copy(params_file, work_dir / "parameters.inp")

    init_content = f""" 6        ntens
 -{initial_p0:.4f}     stress(1)
 -{initial_p0:.4f}     stress(2)
 -{initial_p0:.4f}     stress(3)
  0       stress(4)
  0       stress(5)
  0       stress(ntens)
  73      nstatv    number of state variables
"""
    with open(work_dir / "initialconditions.inp", "w") as f:
        f.write(init_content)

    env = get_intel_rt_env()
    trapz_fn = getattr(np, "trapezoid", getattr(np, "trapz", None))

    records = []
    print(f"--> Starting cyclic sweep over {len(amplitudes)} shear strain amplitudes...")

    for i, gam_a in enumerate(amplitudes):
        out_name = f"cyclic_{i}.out"
        # Pure harmonic shear strain on component 4 (stran 4 = gamma_12)
        test_content = f"""{out_name}
*CirculatingLoad
{ninc_per_cycle} 100 1.0
*Cartesian
1 0.0 0.0 0.0
1 0.0 0.0 0.0
1 0.0 0.0 0.0
0 {gam_a:.8e} 0.0 0.0
0 0.0 0.0 0.0
0 0.0 0.0 0.0
*End
"""
        with open(work_dir / "test.inp", "w") as f:
            f.write(test_content)

        subprocess.run([str(driver_exe)], cwd=work_dir, capture_output=True, env=env)
        out_file = work_dir / out_name
        if not out_file.is_file():
            print(f"Warning: cycle {i} (gamma={gam_a:.2e}) failed to compute.")
            continue

        raw_df = parse_driver_output(out_file)
        gamma = raw_df["stran_4"].values
        tau = raw_df["stress_4"].values

        # Peak values
        g_ampl = (gamma.max() - gamma.min()) / 2.0
        t_ampl = (tau.max() - tau.min()) / 2.0
        G_sec = t_ampl / g_ampl if g_ampl > 0 else G0

        # Loop area \Delta W = \oint \tau d\gamma
        dW = abs(trapz_fn(tau, gamma))
        # Damping ratio D = \Delta W / (4*pi * W_elastic) = \Delta W / (2*pi * tau_a * gamma_a)
        if t_ampl > 0 and g_ampl > 0:
            D = dW / (2.0 * np.pi * t_ampl * g_ampl)
        else:
            D = 0.0

        records.append({
            "gamma_a": g_ampl,
            "tau_a_kPa": t_ampl,
            "G_sec_kPa": G_sec,
            "G_over_G0": G_sec / G0,
            "damping_ratio": D,
            "damping_pct": D * 100.0,
        })
        print(f"   gamma_a = {g_ampl:9.2e} | G/G0 = {G_sec/G0:6.3f} | D = {D*100:5.2f}%")

    res_df = pd.DataFrame(records)
    return res_df


# -----------------------------------------------------------------------------
# Plotting Helpers
# -----------------------------------------------------------------------------
def plot_triaxial_curves(
    df_tx: pd.DataFrame,
    exp_file: Optional[Path] = None,
    save_path: Optional[Path] = None,
) -> None:
    """Plots q-eps_s, q-p', and p'-eps_v curves."""
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5), dpi=200)

    # 1. q vs eps_s
    axes[0].plot(df_tx["eps_s_pct"], df_tx["q_kPa"], "b-", lw=2, label="HS-MN-Bricks (Driver)")
    axes[0].set_xlabel(r"Deviatoric strain $\varepsilon_s$ [%]")
    axes[0].set_ylabel(r"Deviatoric stress $q$ [kPa]")
    axes[0].set_title(r"$q - \varepsilon_s$ Response")
    axes[0].grid(True, ls=":", alpha=0.6)

    # 2. q vs p' (Stress path)
    axes[1].plot(df_tx["p_eff_kPa"], df_tx["q_kPa"], "b-", lw=2, label="HS-MN-Bricks (Driver)")
    axes[1].set_xlabel(r"Mean effective stress $p'$ [kPa]")
    axes[1].set_ylabel(r"Deviatoric stress $q$ [kPa]")
    axes[1].set_title(r"$q - p'$ Stress Path")
    axes[1].grid(True, ls=":", alpha=0.6)

    # 3. p' vs eps_v (Volumetric response)
    axes[2].plot(df_tx["p_eff_kPa"], df_tx["eps_v_pct"], "b-", lw=2, label="HS-MN-Bricks (Driver)")
    axes[2].set_xlabel(r"Mean effective stress $p'$ [kPa]")
    axes[2].set_ylabel(r"Volumetric strain $\varepsilon_v$ [%]")
    axes[2].set_title(r"$p' - \varepsilon_v$ Response")
    axes[2].grid(True, ls=":", alpha=0.6)

    # Optional experimental data overlay
    if exp_file and exp_file.is_file():
        try:
            exp_df = pd.read_csv(exp_file)
            if "eps_s_pct" in exp_df and "q_kPa" in exp_df:
                axes[0].plot(exp_df["eps_s_pct"], exp_df["q_kPa"], "ro", ms=4, label="Lab Data")
            if "p_eff_kPa" in exp_df and "q_kPa" in exp_df:
                axes[1].plot(exp_df["p_eff_kPa"], exp_df["q_kPa"], "ro", ms=4, label="Lab Data")
            if "p_eff_kPa" in exp_df and "eps_v_pct" in exp_df:
                axes[2].plot(exp_df["p_eff_kPa"], exp_df["eps_v_pct"], "ro", ms=4, label="Lab Data")
        except Exception as e:
            print(f"Note: Could not parse experimental file {exp_file}: {e}")

    for ax in axes:
        ax.legend(loc="best")

    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, bbox_inches="tight")
        print(f"Saved triaxial figure to: {save_path}")
    plt.close(fig)


def plot_dynamic_curves(
    df_cyclic: pd.DataFrame,
    gamma07: float = 3e-4,
    exp_file: Optional[Path] = None,
    save_path: Optional[Path] = None,
) -> None:
    """Plots G/G0-gamma and D-gamma curves against laboratory test data."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.8), dpi=200)

    # Analytical Hardin-Drnevich / Santos-Correia curve for comparison
    gam_theory = np.logspace(-6, -2, 200)
    G_G0_theory = 1.0 / (1.0 + (3.0 / 7.0) * (gam_theory / gamma07))

    # Panel 1: Modulus degradation G/G0 vs gamma
    ax1.plot(df_cyclic["gamma_a"], df_cyclic["G_over_G0"], "bs-", lw=1.5, ms=5, label="HS-MN-Bricks (Driver)")
    ax1.plot(gam_theory, G_G0_theory, "k--", lw=1.2, label=rf"Target Backbone ($\gamma_{{0.7}}={gamma07:.1e}$)")
    ax1.set_xscale("log")
    ax1.set_xlabel(r"Shear strain amplitude $\gamma_a$ [-]")
    ax1.set_ylabel(r"Stiffness ratio $G / G_0$ [-]")
    ax1.set_title(r"Shear Modulus Degradation $G/G_0 - \gamma$")
    ax1.set_ylim(0, 1.05)
    ax1.grid(True, which="both", ls=":", alpha=0.6)

    # Panel 2: Damping ratio D vs gamma
    ax2.plot(df_cyclic["gamma_a"], df_cyclic["damping_pct"], "rs-", lw=1.5, ms=5, label="HS-MN-Bricks (Driver)")
    ax2.set_xscale("log")
    ax2.set_xlabel(r"Shear strain amplitude $\gamma_a$ [-]")
    ax2.set_ylabel(r"Hysteretic damping ratio $D$ [%]")
    ax2.set_title(r"Damping Ratio Curve $D - \gamma$")
    ax2.set_ylim(0, max(50.0, df_cyclic["damping_pct"].max() * 1.1))
    ax2.grid(True, which="both", ls=":", alpha=0.6)

    # Optional experimental data overlay
    if exp_file and exp_file.is_file():
        try:
            exp_df = pd.read_csv(exp_file)
            if "gamma" in exp_df and "G_over_G0" in exp_df:
                ax1.plot(exp_df["gamma"], exp_df["G_over_G0"], "k^", ms=6, label="Resonant Column Data")
            if "gamma" in exp_df and "damping_pct" in exp_df:
                ax2.plot(exp_df["gamma"], exp_df["damping_pct"], "k^", ms=6, label="Resonant Column Data")
        except Exception as e:
            print(f"Note: Could not parse experimental dynamic file {exp_file}: {e}")

    ax1.legend(loc="best")
    ax2.legend(loc="best")

    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, bbox_inches="tight")
        print(f"Saved dynamic figure to: {save_path}")
    plt.close(fig)


# -----------------------------------------------------------------------------
# Main CLI Function
# -----------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Run HS-MN-Bricks single element driver for calibration against lab tests."
    )
    parser.add_argument(
        "--params",
        type=str,
        default="examples/IncrementalDriver/parameters.inp",
        help="Path to parameters.inp file.",
    )
    parser.add_argument(
        "--driver",
        type=str,
        default=None,
        help="Path to IncrementalDriver.exe (default: auto-detected).",
    )
    parser.add_argument(
        "--p0",
        type=float,
        default=100.0,
        help="Initial isotropic effective confinement p0' in kPa (default: 100).",
    )
    parser.add_argument(
        "--outdir",
        type=str,
        default="calibration_results",
        help="Directory to save generated curves and figures.",
    )
    parser.add_argument(
        "--run-triaxial",
        action="store_true",
        help="Run monotonic drained triaxial test.",
    )
    parser.add_argument(
        "--run-cyclic",
        action="store_true",
        help="Run cyclic amplitude sweep for G/G0 and D curves.",
    )
    parser.add_argument(
        "--run-all",
        action="store_true",
        help="Run both triaxial and cyclic tests.",
    )
    parser.add_argument(
        "--exp-triaxial",
        type=str,
        default=None,
        help="Path to CSV with experimental triaxial data for overlay.",
    )
    parser.add_argument(
        "--exp-dynamic",
        type=str,
        default=None,
        help="Path to CSV with experimental dynamic (G/G0, D) data for overlay.",
    )

    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    params_path = Path(args.params)
    if not params_path.is_file():
        params_path = project_root / args.params
    if not params_path.is_file():
        print(f"Error: Parameter file not found at {args.params}")
        sys.exit(1)

    driver_exe = find_driver_executable(args.driver)
    outdir = Path(args.outdir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    params_dict, G0 = read_parameters(params_path)
    gamma07 = params_dict.get("gamma07", 3e-4)

    run_tx = args.run_triaxial or args.run_all
    run_cy = args.run_cyclic or args.run_all

    if not run_tx and not run_cy:
        print("No test selected. Specify --run-triaxial, --run-cyclic, or --run-all.")
        parser.print_help()
        sys.exit(0)

    if run_tx:
        print("\n=======================================================")
        print(f"1. RUNNING DRAINED TRIAXIAL TEST (p0' = {args.p0} kPa)...")
        print("=======================================================")
        tx_dir = outdir / "triaxial_work"
        df_tx = run_triaxial_cd(
            driver_exe=driver_exe,
            params_file=params_path,
            initial_p0=args.p0,
            target_strain=-0.25,
            ninc=3000,
            work_dir=tx_dir,
        )
        tx_csv = outdir / "triaxial_curves.csv"
        df_tx.to_csv(tx_csv, index=False)
        print(f"--> Triaxial data exported to: {tx_csv}")

        exp_tx = Path(args.exp_triaxial) if args.exp_triaxial else None
        plot_triaxial_curves(
            df_tx,
            exp_file=exp_tx,
            save_path=outdir / "triaxial_calibration_curves.png",
        )

    if run_cy:
        print("\n=======================================================")
        print(f"2. RUNNING CYCLIC SWEEP (G/G0 & DAMPING D) (p0' = {args.p0} kPa)...")
        print("=======================================================")
        cy_dir = outdir / "cyclic_work"
        df_cy = run_cyclic_sweep(
            driver_exe=driver_exe,
            params_file=params_path,
            initial_p0=args.p0,
            ninc_per_cycle=250,
            work_dir=cy_dir,
        )
        cy_csv = outdir / "cyclic_dynamic_curves.csv"
        df_cy.to_csv(cy_csv, index=False)
        print(f"--> Dynamic data exported to: {cy_csv}")

        exp_dyn = Path(args.exp_dynamic) if args.exp_dynamic else None
        plot_dynamic_curves(
            df_cy,
            gamma07=gamma07,
            exp_file=exp_dyn,
            save_path=outdir / "dynamic_curves_G_D.png",
        )

    print("\n=======================================================")
    print("ALL TESTS COMPLETED SUCCESSFULLY!")
    print(f"Results and plots are saved in: {outdir}")
    print("=======================================================\n")


if __name__ == "__main__":
    main()
