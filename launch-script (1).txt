@echo off
title Systeme de Pointage
echo ====================================
echo    SYSTEME DE POINTAGE - LANCEUR
echo ====================================
echo.

REM Vérifier si Python est installé
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python n'est pas installe sur votre systeme.
    echo Veuillez installer Python depuis https://www.python.org/downloads/
    pause
    exit /b
)

REM Créer l'environnement virtuel si nécessaire
if not exist venv (
    echo Creation de l'environnement virtuel...
    python -m venv venv
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate.bat
)

REM Créer les dossiers nécessaires
if not exist data mkdir data

REM Lancer l'application
echo Lancement de l'application...
streamlit run app.py

deactivate
