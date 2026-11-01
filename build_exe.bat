@echo off
REM ============================================================
REM  Genera MesaAyudaCUN.exe  (ejecutar en Windows con Python 3.10+)
REM  Doble clic o:  build_exe.bat
REM ============================================================
echo [1/3] Instalando PyInstaller...
python -m pip install --upgrade pyinstaller
if errorlevel 1 goto error

echo [2/3] Generando el ejecutable...
python -m PyInstaller --noconfirm --onefile --windowed --name MesaAyudaCUN main.py
if errorlevel 1 goto error

echo [3/3] Copiando la base de datos junto al .exe...
copy /Y cun_sistema.db dist\cun_sistema.db >nul

echo.
echo LISTO: dist\MesaAyudaCUN.exe
pause
exit /b 0

:error
echo.
echo Algo fallo. Revisa que Python este instalado y agregado al PATH.
pause
exit /b 1
