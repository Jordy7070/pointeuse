@echo off
echo Installation du Systeme de Pointage
echo ==================================

REM Vérifier si Python est installé
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python n'est pas installe sur votre systeme.
    echo Veuillez installer Python depuis https://www.python.org/downloads/
    echo Assurez-vous de cocher "Add Python to PATH" lors de l'installation.
    pause
    exit /b
)

REM Vérifier si pip est installé
pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo pip n'est pas installe.
    echo Installation de pip...
    python -m ensurepip --default-pip
)

REM Créer l'environnement virtuel
if not exist venv (
    echo Creation de l'environnement virtuel...
    python -m venv venv
)

REM Activer l'environnement virtuel et installer les dépendances
call venv\Scripts\activate.bat
echo Installation des dependances...
pip install -r requirements.txt

REM Créer les dossiers nécessaires
if not exist data mkdir data

REM Créer le raccourci de lancement
echo @echo off > launch.bat
echo call venv\Scripts\activate.bat >> launch.bat
echo streamlit run app.py >> launch.bat
echo pause >> launch.bat

echo Installation terminee!
echo Pour lancer l'application, double-cliquez sur launch.bat
pause
