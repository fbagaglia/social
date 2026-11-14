@echo off
title Ferma Social Studio
set PORTA=8796

echo ============================================================
echo  Chiusura di Social Studio (porta %PORTA%)
echo ============================================================
echo.

for /f "tokens=5" %%p in ('netstat -ano ^| findstr :%PORTA% ^| findstr LISTENING') do (
  echo  Chiudo il processo %%p
  taskkill /F /PID %%p
)

echo.
echo  Fatto: la porta %PORTA% non e' piu' in ascolto.
rem La finestra "Social Studio - servizio" resta aperta: chiudila con la X.
echo.
pause
