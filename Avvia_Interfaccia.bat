@echo off
title numgeo - Hardening Soil Small (Bricks) Studio
cd /d "%~dp0"
echo ========================================================
echo  Avvio Interfaccia Grafica HS-MN-Bricks (numgeo)...
echo ========================================================
set PATH=C:\Users\uso\anaconda3\Library\bin;C:\Users\uso\anaconda3\bin;%PATH%
python gui_hs_bricks.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Si e verificato un errore durante l'avvio della GUI.
    pause
)
