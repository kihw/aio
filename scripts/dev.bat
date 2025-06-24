@echo off
rem Script de développement pour Windows

setlocal EnableDelayedExpansion

rem Couleurs pour la sortie console
set "GREEN=[32m"
set "YELLOW=[33m"
set "RED=[31m"
set "BLUE=[34m"
set "NC=[0m"

rem Fonction pour afficher les messages avec couleurs
:log
set "level=%~1"
set "message=%~2"

if "%level%"=="info" (
    echo %BLUE%[INFO]%NC% %message%
) else if "%level%"=="success" (
    echo %GREEN%[SUCCESS]%NC% %message%
) else if "%level%"=="warning" (
    echo %YELLOW%[WARNING]%NC% %message%
) else if "%level%"=="error" (
    echo %RED%[ERROR]%NC% %message%
) else (
    echo %message%
)
exit /b

rem Vérifier si Python est installé
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    call :log "error" "Python 3 n'est pas installe. Veuillez l'installer avant de continuer."
    exit /b 1
)

rem Vérifier si Node.js est installé
node --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    call :log "error" "Node.js n'est pas installe. Veuillez l'installer avant de continuer."
    exit /b 1
)

rem Vérifier si npm est installé
npm --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    call :log "error" "npm n'est pas installe. Veuillez l'installer avant de continuer."
    exit /b 1
)

rem Répertoire racine du projet
set "PROJECT_ROOT=%~dp0.."
set "BACKEND_DIR=%PROJECT_ROOT%\main"
set "FRONTEND_DIR=%PROJECT_ROOT%\frontend"

rem Configuration des processus
set "BACKEND_PID_FILE=%TEMP%\appflow_backend.pid"
set "FRONTEND_PID_FILE=%TEMP%\appflow_frontend.pid"

rem Fonction pour installer les dépendances Python
:setup_python
call :log "info" "Installation des dependances Python..."

rem Créer un environnement virtuel s'il n'existe pas
if not exist "%PROJECT_ROOT%\venv" (
    call :log "info" "Creation de l'environnement virtuel Python..."
    python -m venv "%PROJECT_ROOT%\venv"
)

rem Activer l'environnement virtuel
call "%PROJECT_ROOT%\venv\Scripts\activate.bat"

rem Installer les dépendances
pip install -r "%BACKEND_DIR%\requirements.txt"

if %ERRORLEVEL% equ 0 (
    call :log "success" "Dependances Python installees avec succes."
) else (
    call :log "error" "Erreur lors de l'installation des dependances Python."
    exit /b 1
)
exit /b

rem Fonction pour installer les dépendances Node.js
:setup_node
call :log "info" "Installation des dependances Node.js..."

cd /d "%FRONTEND_DIR%"
npm install

if %ERRORLEVEL% equ 0 (
    call :log "success" "Dependances Node.js installees avec succes."
) else (
    call :log "error" "Erreur lors de l'installation des dependances Node.js."
    exit /b 1
)

cd /d "%PROJECT_ROOT%"
exit /b

rem Fonction pour démarrer le backend
:start_backend
call :log "info" "Demarrage du backend Python..."

rem Activer l'environnement virtuel
call "%PROJECT_ROOT%\venv\Scripts\activate.bat"

rem Démarrer le serveur Flask en arrière-plan
start /b "" cmd /c "python "%BACKEND_DIR%\appflow.py" --server --debug > %TEMP%\appflow_backend.log 2>&1"
set "BACKEND_PID=%ERRORLEVEL%"

rem Stocker le PID dans un fichier
echo %BACKEND_PID% > "%BACKEND_PID_FILE%"

call :log "success" "Backend demarre"
exit /b

rem Fonction pour démarrer le frontend
:start_frontend
call :log "info" "Demarrage du frontend Electron/React..."

cd /d "%FRONTEND_DIR%"
start /b "" cmd /c "npm run dev > %TEMP%\appflow_frontend.log 2>&1"
set "FRONTEND_PID=%ERRORLEVEL%"

rem Stocker le PID dans un fichier
echo %FRONTEND_PID% > "%FRONTEND_PID_FILE%"

call :log "success" "Frontend demarre"

cd /d "%PROJECT_ROOT%"
exit /b

rem Fonction pour nettoyer les processus
:cleanup
call :log "info" "Arret des processus..."

rem Arrêter les processus
if exist "%BACKEND_PID_FILE%" (
    for /f %%i in (%BACKEND_PID_FILE%) do (
        taskkill /pid %%i /f /t >nul 2>&1
    )
    del "%BACKEND_PID_FILE%" >nul 2>&1
)

if exist "%FRONTEND_PID_FILE%" (
    for /f %%i in (%FRONTEND_PID_FILE%) do (
        taskkill /pid %%i /f /t >nul 2>&1
    )
    del "%FRONTEND_PID_FILE%" >nul 2>&1
)

call :log "success" "Processus arretes. Au revoir!"
exit /b

rem Fonction principale
:main
call :log "info" "====== AppFlow - Mode Developpement ======"

rem Vérifier les arguments
if "%~1"=="--backend" (
    call :setup_python
    call :start_backend
) else if "%~1"=="--frontend" (
    call :setup_node
    call :start_frontend
) else if "%~1"=="--install" (
    call :setup_python
    call :setup_node
    call :log "success" "Installation des dependances terminee."
    goto :eof
) else (
    rem Par défaut, démarrer le backend et le frontend
    call :setup_python
    call :setup_node
    call :start_backend
    call :start_frontend
)

call :log "info" "AppFlow est en cours d'execution. Pressez Ctrl+C pour arreter."

rem Créer un script pour gérer CTRL+C
echo @echo off > "%TEMP%\appflow_cleanup.bat"
echo call "%~f0" cleanup >> "%TEMP%\appflow_cleanup.bat"

rem Attendre l'entrée de l'utilisateur
echo Appuyez sur une touche pour arreter l'application...
pause >nul
call :cleanup

:end
endlocal
