@echo off
cd /d "%~dp0"
py -m pip install -r requirements.txt
py -m PyInstaller --noconfirm --clean --onedir --windowed --add-data "bloc_marque_rf_france_travail.jpg;." --name "Perspectives Emploi" app.py
echo.
echo Compilation terminee. Le logiciel se trouve dans dist\Perspectives Emploi\
pause
