#!/usr/bin/env python3
"""
generate_excel_calibration.py
=============================
Genera un foglio di calcolo Excel avanzato (.xlsx) per la calibrazione dinamica del modello
Hardening Soil con estensione BRICK (numgeo / Cudny & Truty 2020).

Caratteristiche:
- Tutte le curve (G/G0, Gs, Gt, tau, Smorzamento D%) sono generate tramite FORMULE EXCEL VIVE.
- Modificando qualsiasi parametro di input (G0_ref, gamma_0.7, Eur_ref, nu, p0, pref, m, c, phi),
  tutte le curve e i grafici si aggiornano istantaneamente in tempo reale.
- Include la discretizzazione analitica a 10 brick (Simpson 1992, Cudny & Truty 2020).
- Include colonne per inserire i dati sperimentali di laboratorio (Colonna Risonante / Taglio Ciclico).
- Include grafici a dispersione XY con asse X logaritmico incorporati direttamente nel foglio.
"""

from __future__ import annotations

import math
from pathlib import Path
import numpy as np
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.chart import ScatterChart, Reference, Series


def build_excel_calibration_sheet(output_path: Path):
    wb = openpyxl.Workbook()

    # =========================================================================
    # FOGLIO 1: Curva_G_G0_e_Smorzamento
    # =========================================================================
    ws = wb.active
    ws.title = "Curva_G_G0_e_Smorzamento"
    ws.views.sheetView[0].showGridLines = True

    # Stili
    font_title = Font(name="Segoe UI", size=14, bold=True, color="1B365D")
    font_subtitle = Font(name="Segoe UI", size=10, italic=True, color="4A607A")
    font_sec_hdr = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
    font_tbl_hdr = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")
    font_bold = Font(name="Segoe UI", size=10, bold=True)
    font_normal = Font(name="Segoe UI", size=10)
    font_italic = Font(name="Segoe UI", size=9, italic=True, color="555555")

    fill_hdr_dark = PatternFill(start_color="1B365D", end_color="1B365D", fill_type="solid")
    fill_hdr_blue = PatternFill(start_color="2A6F97", end_color="2A6F97", fill_type="solid")
    fill_hdr_green = PatternFill(start_color="2D6A4F", end_color="2D6A4F", fill_type="solid")
    fill_input = PatternFill(start_color="FFF3CD", end_color="FFF3CD", fill_type="solid")       # Giallo pastello per input editabili
    fill_calc = PatternFill(start_color="E8F4F8", end_color="E8F4F8", fill_type="solid")        # Azzurro pastello per valori calcolati
    fill_exp = PatternFill(start_color="FDE8E8", end_color="FDE8E8", fill_type="solid")         # Rosa pastello per dati lab

    thin_border_side = Side(style="thin", color="CCCCCC")
    border_cell = Border(left=thin_border_side, right=thin_border_side, top=thin_border_side, bottom=thin_border_side)
    thick_bottom = Border(bottom=Side(style="medium", color="1B365D"))

    # Titoli
    ws.merge_cells("A1:J1")
    ws["A1"] = "MODELLO COSTITUTIVO HARDENING SOIL SMALL (BRICKS) — CURVE DINAMICHE G/G0 E SMORZAMENTO D"
    ws["A1"].font = font_title
    ws["A1"].alignment = Alignment(vertical="center")

    ws.merge_cells("A2:J2")
    ws["A2"] = "Relazioni costitutive secondo Cudny & Truty (2020), Santos & Correia (2001) e Hardin & Drnevich (1972)"
    ws["A2"].font = font_subtitle

    # -------------------------------------------------------------------------
    # TABELLA 1: PARAMETRI DI INPUT (Colonne A..D, Righe 4..15)
    # -------------------------------------------------------------------------
    ws.merge_cells("A4:D4")
    ws["A4"] = "PARAMETRI DI INPUT DEL MATERIALE (Modificabili)"
    ws["A4"].font = font_sec_hdr
    ws["A4"].fill = fill_hdr_dark
    ws["A4"].alignment = Alignment(horizontal="center", vertical="center")

    input_headers = ["Simbolo", "Descrizione Geotecnica", "Valore Input", "Unità"]
    for col_idx, h in enumerate(input_headers, start=1):
        cell = ws.cell(row=5, column=col_idx, value=h)
        cell.font = font_tbl_hdr
        cell.fill = fill_hdr_blue
        cell.alignment = Alignment(horizontal="center", vertical="center")

    inputs_data = [
        ("G0_ref", "Modulo di taglio a piccolissime deformazioni a pref", 60000.0, "kPa", "0.0"),
        ("gamma_0.7", "Soglia di scorrimento al 72.2% di decadimento (G/G0=0.722)", 0.000300, "-", "0.000000"),
        ("Eur_ref", "Modulo di Young di scarico-ricarico a pref", 25750.0, "kPa", "0.0"),
        ("nu_ur", "Coefficiente di Poisson elastico (scarico/ricarico)", 0.29, "-", "0.00"),
        ("pref", "Pressione di riferimento di laboratorio", 100.0, "kPa", "0.0"),
        ("m", "Esponente della dipendenza dallo stato tensionale", 0.70, "-", "0.00"),
        ("c", "Coesione efficace del terreno", 6.0, "kPa", "0.0"),
        ("phi", "Angolo di attrito efficace (Matsuoka-Nakai)", 28.0, "deg", "0.0"),
        ("p0_eff", "Pressione media efficace iniziale (confinamento)", 100.0, "kPa", "0.0")
    ]

    for idx, (symb, desc, val, unit, num_fmt) in enumerate(inputs_data, start=6):
        c1 = ws.cell(row=idx, column=1, value=symb)
        c2 = ws.cell(row=idx, column=2, value=desc)
        c3 = ws.cell(row=idx, column=3, value=val)
        c4 = ws.cell(row=idx, column=4, value=unit)

        c1.font = font_bold
        c2.font = font_normal
        c3.font = font_bold
        c3.fill = fill_input
        c3.number_format = num_fmt
        c3.alignment = Alignment(horizontal="right")
        c4.font = font_italic
        c4.alignment = Alignment(horizontal="center")

        for c in [c1, c2, c3, c4]:
            c.border = border_cell

    # -------------------------------------------------------------------------
    # TABELLA 2: PARAMETRI CALCOLATI DAL MODELLO (Colonne E..H, Righe 4..15)
    # -------------------------------------------------------------------------
    ws.merge_cells("F4:I4")
    ws["F4"] = "PARAMETRI CALCOLATI DAL MODELLO (Formule Dinamiche)"
    ws["F4"].font = font_sec_hdr
    ws["F4"].fill = fill_hdr_dark
    ws["F4"].alignment = Alignment(horizontal="center", vertical="center")

    calc_headers = ["Simbolo", "Descrizione / Formula", "Valore Calcolato", "Unità"]
    for col_idx, h in enumerate(calc_headers, start=6):
        cell = ws.cell(row=5, column=col_idx, value=h)
        cell.font = font_tbl_hdr
        cell.fill = fill_hdr_green
        cell.alignment = Alignment(horizontal="center", vertical="center")

    calc_data = [
        ("apex", "Tensione equivalente coesiva c*cot(phi)", "=C12/TAN(RADIANS(C13))", "kPa", "0.00"),
        ("fac_stress", "Fattore di scala tensionale ((p0+apex)/(pref+apex))^m", "=((C14+H6)/(C10+H6))^C11", "-", "0.0000"),
        ("Gur_ref", "Modulo di taglio elastico scarico Eur/(2*(1+nu))", "=C8/(2*(1+C9))", "kPa", "0.0"),
        ("G0(p0)", "Modulo di taglio a piccolissime def. al confinamento p0", "=C6*H7", "kPa", "0.0"),
        ("Gur(p0)", "Modulo di taglio elastico al confinamento p0", "=H8*H7", "kPa", "0.0"),
        ("Gmin / G0", "Limite inferiore di degradazione Gur / G0", "=H8/C6", "-", "0.0000"),
        ("a", "Costante di curvatura Santos & Correia = 3/7", "=3/7", "-", "0.0000"),
        ("h1", "Parametro di corda Hardin-Drnevich = 7/3 * gamma0.7", "=(7/3)*C7", "-", "0.000000"),
        ("D_min", "Smorzamento isteretico a piccole deformazioni (stimato)", "0.50", "%", "0.00")
    ]

    for idx, (symb, desc, formula_val, unit, num_fmt) in enumerate(calc_data, start=6):
        c1 = ws.cell(row=idx, column=6, value=symb)
        c2 = ws.cell(row=idx, column=7, value=desc)
        c3 = ws.cell(row=idx, column=8, value=formula_val)
        c4 = ws.cell(row=idx, column=9, value=unit)

        c1.font = font_bold
        c2.font = font_normal
        c3.font = font_bold
        c3.fill = fill_calc
        c3.number_format = num_fmt
        c3.alignment = Alignment(horizontal="right")
        c4.font = font_italic
        c4.alignment = Alignment(horizontal="center")

        for c in [c1, c2, c3, c4]:
            c.border = border_cell

    # -------------------------------------------------------------------------
    # TABELLA 3: DISCRETIZZAZIONE 10 BRICK (Simpson 1992, Cudny & Truty 2020)
    # (Righe 17..28)
    # -------------------------------------------------------------------------
    ws.merge_cells("A16:I16")
    ws["A16"] = "DISCRETIZZAZIONE MULTI-SUPERFICIE A 10 BRICK (Cudny & Truty 2020, Eq. 18-20)"
    ws["A16"].font = font_sec_hdr
    ws["A16"].fill = fill_hdr_blue
    ws["A16"].alignment = Alignment(horizontal="center", vertical="center")

    brick_headers = ["Brick #", "Stiffness Range", "Delta_omega [-]", "gG_j [-]", "Lunghezza Corda sl_j [-]", "Corda sl_j [%]", "Note Meccaniche", "", ""]
    for col_idx in range(1, 8):
        cell = ws.cell(row=17, column=col_idx, value=brick_headers[col_idx-1])
        cell.font = font_tbl_hdr
        cell.fill = PatternFill(start_color="3D5A80", end_color="3D5A80", fill_type="solid")
        cell.alignment = Alignment(horizontal="center", vertical="center")

    for jb in range(1, 11):
        r = 17 + jb
        # Formule dei brick
        # Delta_omega = (1 - Gmin/G0) / 10 = (1 - $H$11)/10
        # gG_j = 1 - jb*Delta_omega + 0.5*Delta_omega
        # sl_j = h1 * (sqrt(1/gG_j) - 1)
        ws.cell(row=r, column=1, value=jb).font = font_bold
        ws.cell(row=r, column=2, value="=(1-$H$11)").number_format = "0.0000"
        ws.cell(row=r, column=3, value=f"=B{r}/10").number_format = "0.0000"
        ws.cell(row=r, column=4, value=f"=1 - {jb}*C{r} + 0.5*C{r}").number_format = "0.0000"
        ws.cell(row=r, column=5, value=f"=$H$13*(SQRT(1/D{r}) - 1)").number_format = "0.000000"
        ws.cell(row=r, column=6, value=f"=E{r}*100").number_format = "0.0000"
        ws.cell(row=r, column=7, value=f"Superficie di snervamento cinetico {jb}/10").font = font_italic

        for c_idx in range(1, 8):
            c = ws.cell(row=r, column=c_idx)
            c.border = border_cell
            c.alignment = Alignment(horizontal="center")

    # -------------------------------------------------------------------------
    # TABELLA 4: CURVE DINAMICHE G/G0 E SMORZAMENTO D vs GAMMA
    # (Righe 30..80)
    # -------------------------------------------------------------------------
    start_row = 30
    ws.merge_cells(f"A{start_row}:J{start_row}")
    ws[f"A{start_row}"] = "TABELLA CALCOLO CURVE DINAMICHE E CONFRONTO SPERIMENTALE"
    ws[f"A{start_row}"].font = font_sec_hdr
    ws[f"A{start_row}"].fill = fill_hdr_dark
    ws[f"A{start_row}"].alignment = Alignment(horizontal="center", vertical="center")

    table_cols = [
        ("gamma_s [-]", "Deformazione di scorrimento"),
        ("gamma_s [%]", "Scorrimento percentuale"),
        ("G_sec / G0 [-]", "Decadimento Modulo Secante Santos & Correia"),
        ("G_tan / G0 [-]", "Decadimento Modulo Tangente Santos & Correia"),
        ("G_sec [kPa]", "Modulo di taglio secante al confinamento p0"),
        ("tau [kPa]", "Tensione tangenziale mobilitata tau = G_sec * gamma"),
        ("Smorzamento D [%]", "Rapporto di smorzamento isteretico teorico (Masing)"),
        ("Lab G/G0 [-]", "Dati Sperimentali Colonna Risonante (Input Utente)"),
        ("Lab D [%]", "Dati Sperimentali Smorzamento (Input Utente)"),
        ("Delta (Sim-Lab)", "Errore residuo calibrazione (G/G0)")
    ]

    header_row = start_row + 1
    for c_idx, (col_name, tooltip) in enumerate(table_cols, start=1):
        cell = ws.cell(row=header_row, column=c_idx, value=col_name)
        cell.font = font_tbl_hdr
        if "Lab" in col_name:
            cell.fill = PatternFill(start_color="9D0208", end_color="9D0208", fill_type="solid")
        else:
            cell.fill = fill_hdr_blue
        cell.alignment = Alignment(horizontal="center", vertical="center")

    # Genera 50 punti di gamma_s da 1.0e-6 a 1.0e-1
    gammas = np.logspace(-6, -1, 51)
    
    # Dati sperimentali campione da pre-caricare a titolo esemplificativo
    exp_gammas = {
        1.0e-6: (1.000, 0.50),
        3.0e-6: (0.998, 0.60),
        1.0e-5: (0.992, 0.80),
        3.0e-5: (0.955, 1.80),
        1.0e-4: (0.875, 3.20),
        3.0e-4: (0.710, 9.50),
        1.0e-3: (0.380, 28.00),
        3.0e-3: (0.180, 38.50),
        1.0e-2: (0.075, 42.00)
    }

    for idx, gam in enumerate(gammas):
        r = header_row + 1 + idx

        # Colonna A: gamma_s [-]
        cA = ws.cell(row=r, column=1, value=float(gam))
        cA.number_format = "0.00E+00"
        cA.font = font_bold
        cA.alignment = Alignment(horizontal="right")

        # Colonna B: gamma_s [%] = gamma_s * 100
        cB = ws.cell(row=r, column=2, value=f"=A{r}*100")
        cB.number_format = "0.0000"
        cB.alignment = Alignment(horizontal="right")

        # Colonna C: G_sec / G0 = MAX(Gmin/G0, 1 / (1 + a * (gamma / gamma07)))
        # $H$11 = Gmin/G0, $H$12 = a (3/7), $C$7 = gamma07
        cC = ws.cell(row=r, column=3, value=f"=MAX($H$11, 1 / (1 + $H$12 * (A{r} / $C$7)))")
        cC.number_format = "0.0000"
        cC.font = font_bold
        cC.fill = fill_calc
        cC.alignment = Alignment(horizontal="right")

        # Colonna D: G_tan / G0 = MAX(Gmin/G0, 1 / (1 + a * (gamma / gamma07))^2)
        cD = ws.cell(row=r, column=4, value=f"=MAX($H$11, 1 / (1 + $H$12 * (A{r} / $C$7))^2)")
        cD.number_format = "0.0000"
        cD.alignment = Alignment(horizontal="right")

        # Colonna E: G_sec [kPa] = (G_sec/G0) * G0(p0)  where $H$9 = G0(p0)
        cE = ws.cell(row=r, column=5, value=f"=C{r} * $H$9")
        cE.number_format = "#,##0.0"
        cE.alignment = Alignment(horizontal="right")

        # Colonna F: tau [kPa] = G_sec * gamma_s = E{r} * A{r}
        cF = ws.cell(row=r, column=6, value=f"=E{r} * A{r}")
        cF.number_format = "0.000"
        cF.alignment = Alignment(horizontal="right")

        # Colonna G: Smorzamento D [%] teorico (Masing formula approssimata con D_min)
        # Formula Masing per curva iperbolica:
        # x = a * gamma / gamma07
        # D_masing = (4/PI) * ((1+x)/x) * (1 - LN(1+x)/x) - (2/PI)
        # in % moltiplicato per 100 + D_min ($H$14)
        # Con protezione per piccoli x (limite x->0 D_masing -> 0):
        # Per x < 0.01: D = D_min
        cG = ws.cell(row=r, column=7,
                     value=f"=IF(($H$12*(A{r}/$C$7))<0.01, $H$14, MIN(45, $H$14 + 100 * ((4/PI()) * ((1 + $H$12*(A{r}/$C$7))/($H$12*(A{r}/$C$7))) * (1 - LN(1 + $H$12*(A{r}/$C$7))/($H$12*(A{r}/$C$7))) - (2/PI()))))")
        cG.number_format = "0.00"
        cG.font = font_bold
        cG.fill = fill_calc
        cG.alignment = Alignment(horizontal="right")

        # Colonna H & I: Dati Sperimentali Lab
        # Se gamma è vicino a uno dei valori sperimentali, pre-popola
        cH = ws.cell(row=r, column=8)
        cI = ws.cell(row=r, column=9)
        cH.fill = fill_exp
        cI.fill = fill_exp
        cH.alignment = Alignment(horizontal="right")
        cI.alignment = Alignment(horizontal="right")
        cH.number_format = "0.000"
        cI.number_format = "0.00"

        # Trova se c'è un dato sperimentale vicino
        closest_exp = None
        for eg, (eg_val, ed_val) in exp_gammas.items():
            if abs(math.log10(gam) - math.log10(eg)) < 0.04:
                closest_exp = (eg_val, ed_val)
                break
        if closest_exp:
            cH.value = closest_exp[0]
            cI.value = closest_exp[1]

        # Colonna J: Residuo Delta = IF(ISBLANK(H{r}), "", C{r} - H{r})
        cJ = ws.cell(row=r, column=10, value=f'=IF(ISBLANK(H{r}), "", C{r} - H{r})')
        cJ.number_format = "0.000"
        cJ.alignment = Alignment(horizontal="right")

        for c in [cA, cB, cC, cD, cE, cF, cG, cH, cI, cJ]:
            c.border = border_cell

    last_row = header_row + len(gammas)

    # -------------------------------------------------------------------------
    # GRAFICI EXCEL INCORPORATI
    # -------------------------------------------------------------------------
    # 1. Grafico Decadimento Modulo di Taglio G/G0 vs gamma
    chart_g = ScatterChart()
    chart_g.title = "Curva di Decadimento del Modulo di Taglio G/G0 - gamma"
    chart_g.style = 13
    chart_g.x_axis.title = "Deformazione di scorrimento gamma_s [-]"
    chart_g.y_axis.title = "Modulo normalizzato G / G0 [-]"
    chart_g.x_axis.scaling.logBase = 10
    chart_g.y_axis.scaling.min = 0.0
    chart_g.y_axis.scaling.max = 1.05
    chart_g.width = 16
    chart_g.height = 11

    xvalues = Reference(ws, min_col=1, min_row=header_row+1, max_row=last_row)
    yvalues_model = Reference(ws, min_col=3, min_row=header_row, max_row=last_row)
    series_model = Series(yvalues_model, xvalues, title_from_data=True)
    series_model.graphicalProperties.line.solidFill = "00509D"
    series_model.graphicalProperties.line.width = 25000
    chart_g.series.append(series_model)

    # Serie dati di laboratorio
    yvalues_lab = Reference(ws, min_col=8, min_row=header_row, max_row=last_row)
    series_lab = Series(yvalues_lab, xvalues, title_from_data=True)
    series_lab.marker.symbol = "triangle"
    series_lab.marker.graphicalProperties.solidFill = "9D0208"
    series_lab.marker.graphicalProperties.line.solidFill = "9D0208"
    series_lab.graphicalProperties.line.noFill = True
    chart_g.series.append(series_lab)

    ws.add_chart(chart_g, "L4")

    # 2. Grafico Smorzamento Isteretico D [%] vs gamma
    chart_d = ScatterChart()
    chart_d.title = "Curva di Smorzamento Isteretico D [%] - gamma"
    chart_d.style = 13
    chart_d.x_axis.title = "Deformazione di scorrimento gamma_s [-]"
    chart_d.y_axis.title = "Rapporto di smorzamento D [%]"
    chart_d.x_axis.scaling.logBase = 10
    chart_d.y_axis.scaling.min = 0.0
    chart_d.y_axis.scaling.max = 50.0
    chart_d.width = 16
    chart_d.height = 11

    yvalues_d_model = Reference(ws, min_col=7, min_row=header_row, max_row=last_row)
    series_d_model = Series(yvalues_d_model, xvalues, title_from_data=True)
    series_d_model.graphicalProperties.line.solidFill = "DC2F02"
    series_d_model.graphicalProperties.line.width = 25000
    chart_d.series.append(series_d_model)

    # Serie dati lab smorzamento
    yvalues_d_lab = Reference(ws, min_col=9, min_row=header_row, max_row=last_row)
    series_d_lab = Series(yvalues_d_lab, xvalues, title_from_data=True)
    series_d_lab.marker.symbol = "circle"
    series_d_lab.marker.graphicalProperties.solidFill = "1B365D"
    series_d_lab.marker.graphicalProperties.line.solidFill = "1B365D"
    series_d_lab.graphicalProperties.line.noFill = True
    chart_d.series.append(series_d_lab)

    ws.add_chart(chart_d, "L26")

    # 3. Grafico Curva Scheletro Sforzo-Deformazione tau vs gamma
    chart_tau = ScatterChart()
    chart_tau.title = "Curva Scheletro Tensione-Deformazione tau - gamma"
    chart_tau.style = 13
    chart_tau.x_axis.title = "Deformazione di scorrimento gamma_s [-]"
    chart_tau.y_axis.title = "Tensione tangenziale tau [kPa]"
    chart_tau.width = 16
    chart_tau.height = 11

    yvalues_tau = Reference(ws, min_col=6, min_row=header_row, max_row=last_row)
    series_tau = Series(yvalues_tau, xvalues, title_from_data=True)
    series_tau.graphicalProperties.line.solidFill = "2D6A4F"
    series_tau.graphicalProperties.line.width = 25000
    chart_tau.series.append(series_tau)

    ws.add_chart(chart_tau, "L48")

    # Larghezza colonne
    col_widths = {
        "A": 16, "B": 15, "C": 18, "D": 18, "E": 16,
        "F": 15, "G": 20, "H": 16, "I": 16, "J": 16,
        "K": 4, "L": 20
    }
    for col_letter, width in col_widths.items():
        ws.column_dimensions[col_letter].width = width

    # =========================================================================
    # FOGLIO 2: Dati_Simulazione_Driver
    # =========================================================================
    ws2 = wb.create_sheet(title="Dati_Simulazione_Driver")
    ws2.views.sheetView[0].showGridLines = True

    ws2.merge_cells("A1:G1")
    ws2["A1"] = "RISULTATI SIMULAZIONE CON IL DRIVER MECCANICO (IncrementalDriver.exe)"
    ws2["A1"].font = font_title

    ws2.merge_cells("A2:G2")
    ws2["A2"] = "Dati integrati ciclo per ciclo tramite ritorno plastico a 10 brick e calcolo isteretico dW"
    ws2["A2"].font = font_subtitle

    driver_csv = output_path.parent / "calibration_results" / "cyclic_dynamic_curves.csv"
    if driver_csv.is_file():
        import pandas as pd
        df_driver = pd.read_csv(driver_csv)
        headers_driver = ["gamma_a [-]", "tau_a [kPa]", "G_sec [kPa]", "G / G0 [-]", "Damping Ratio [-]", "Damping D [%]"]
        for c_idx, h in enumerate(headers_driver, start=1):
            cell = ws2.cell(row=4, column=c_idx, value=h)
            cell.font = font_tbl_hdr
            cell.fill = fill_hdr_dark
            cell.alignment = Alignment(horizontal="center")

        for r_idx, row in df_driver.iterrows():
            curr_r = 5 + r_idx
            ws2.cell(row=curr_r, column=1, value=float(row["gamma_a"])).number_format = "0.00E+00"
            ws2.cell(row=curr_r, column=2, value=float(row["tau_a_kPa"])).number_format = "0.000"
            ws2.cell(row=curr_r, column=3, value=float(row["G_sec_kPa"])).number_format = "#,##0.0"
            ws2.cell(row=curr_r, column=4, value=float(row["G_over_G0"])).number_format = "0.0000"
            ws2.cell(row=curr_r, column=5, value=float(row["damping_ratio"])).number_format = "0.0000"
            ws2.cell(row=curr_r, column=6, value=float(row["damping_pct"])).number_format = "0.00"

            for c_idx in range(1, 7):
                cell = ws2.cell(row=curr_r, column=c_idx)
                cell.border = border_cell
                cell.alignment = Alignment(horizontal="right")

        for c_idx in range(1, 7):
            col_letter = get_column_letter(c_idx)
            ws2.column_dimensions[col_letter].width = 18

    # Salva il file Excel
    wb.save(output_path)
    print(f"File Excel generato con successo: {output_path}")


if __name__ == "__main__":
    out_file = Path(__file__).resolve().parent.parent / "Calibrazione_HS_Bricks_Curve_Dinamiche.xlsx"
    build_excel_calibration_sheet(out_file)
