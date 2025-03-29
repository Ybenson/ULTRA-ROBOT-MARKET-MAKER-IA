@echo off
REM Script d'installation pour ULTRA-ROBOT MARKET MAKER IA sous Windows
REM Ce script configure l'environnement et installe toutes les dépendances nécessaires

echo ===================================================
echo   INSTALLATION D'ULTRA-ROBOT MARKET MAKER IA
echo ===================================================
echo.

REM Vérifier si Python est installé
python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo Python n'est pas installé ou n'est pas dans le PATH.
    echo Veuillez installer Python 3.8 ou supérieur depuis https://www.python.org/downloads/
    echo Assurez-vous de cocher l'option "Add Python to PATH" lors de l'installation.
    pause
    exit /b 1
)

REM Vérifier la version de Python
python -c "import sys; sys.exit(0) if sys.version_info >= (3,8) else sys.exit(1)"
if %errorlevel% neq 0 (
    echo La version de Python est inférieure à 3.8.
    echo Veuillez installer Python 3.8 ou supérieur.
    pause
    exit /b 1
)

echo Python est correctement installé.
echo.

REM Créer les répertoires nécessaires
if not exist logs mkdir logs
if not exist data mkdir data
if not exist models mkdir models

echo Répertoires créés: logs, data, models
echo.

REM Créer un environnement virtuel
if not exist venv (
    echo Création de l'environnement virtuel...
    python -m venv venv
) else (
    echo L'environnement virtuel existe déjà.
)

REM Activer l'environnement virtuel
echo Activation de l'environnement virtuel...
call venv\Scripts\activate.bat

REM Mettre à jour pip
echo Mise à jour de pip...
python -m pip install --upgrade pip

REM Installer les dépendances
echo Installation des dépendances...
pip install -r requirements.txt

REM Installer le package en mode développement
echo Installation du package en mode développement...
pip install -e .

REM Vérifier si le fichier .env existe
if not exist src\config\.env (
    echo Création du fichier .env à partir du modèle...
    copy src\config\.env.example src\config\.env
    echo Veuillez éditer le fichier src\config\.env pour configurer vos clés API.
) else (
    echo Le fichier .env existe déjà.
)

echo.
echo ===================================================
echo   INSTALLATION TERMINÉE AVEC SUCCÈS
echo ===================================================
echo.
echo Pour démarrer le bot en mode simulation:
echo   python run_bot.py --mode simulation
echo.
echo Pour démarrer le bot avec Docker:
echo   docker-compose up -d
echo.
echo Pour plus d'options:
echo   python run_bot.py --help
echo.

pause
