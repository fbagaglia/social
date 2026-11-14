@echo off
title Social Studio
cd /d "%~dp0"
set PORTA=8796

echo ============================================================
echo  Avvio di Social Studio
echo ============================================================
echo.
echo  Indirizzo: http://127.0.0.1:%PORTA%/
echo  Per chiudere: chiudi questa finestra, oppure lancia
echo  ferma_social_studio.bat
echo.

start "Social Studio - servizio" cmd /k "py -3.14 backend\server.py"

echo  Attendo che il servizio risponda...
set /a giri=0
:attesa
set /a giri+=1
timeout /t 2 >nul
curl -s -o nul http://127.0.0.1:%PORTA%/health
if errorlevel 1 goto :ancora
goto :pronto

:ancora
if %giri% GEQ 20 goto :lento
goto :attesa

:pronto
echo  Servizio pronto. Apro la pagina.
start "" "http://127.0.0.1:%PORTA%/"
goto :fine

:lento
echo.
echo  Il servizio non ha risposto in tempo. Guarda la finestra
echo  "Social Studio - servizio": li' c'e' il messaggio d'errore.
echo.

:fine
echo.
pause
