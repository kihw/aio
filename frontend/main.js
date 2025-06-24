/**
 * AppFlow - Point d'entrée Electron
 * 
 * Ce fichier est le point d'entrée principal pour l'application Electron.
 * Il gère la création de la fenêtre principale, la communication IPC avec le backend,
 * et les comportements spécifiques à l'application.
 */

const { app, BrowserWindow, Tray, Menu, ipcMain, shell, dialog } = require('electron');
const path = require('path');
const url = require('url');
const fs = require('fs');
const axios = require('axios');
const isDev = require('electron-is-dev');
const log = require('electron-log');
const { spawn } = require('child_process');
const Store = require('electron-store');

// Configuration du logger
log.transports.file.level = 'info';
log.info('Application starting...');

// Configuration du stockage des préférences
const store = new Store({
    name: 'preferences',
    defaults: {
        windowBounds: { width: 1200, height: 800 },
        startMinimized: false,
        minimizeToTray: true,
        autoStartEngine: true,
        apiPort: 5000,
        darkMode: false,
        firstRun: true,
        pythonPath: null
    }
});

// Variables globales
let mainWindow = null;
let tray = null;
let pythonProcess = null;
let apiBaseUrl = `http://127.0.0.1:${store.get('apiPort')}`;
let isQuitting = false;
let engineRunning = false;

/**
 * Crée la fenêtre principale de l'application
 */
function createWindow() {
    const { width, height } = store.get('windowBounds');

    mainWindow = new BrowserWindow({
        width,
        height,
        minWidth: 800,
        minHeight: 600,
        title: 'AppFlow',
        icon: path.join(__dirname, 'assets', 'icon.png'),
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            enableRemoteModule: false,
            preload: path.join(__dirname, 'preload.js')
        }
    });

    // Sauvegarder la taille et la position de la fenêtre
    mainWindow.on('resize', () => {
        const { width, height } = mainWindow.getBounds();
        store.set('windowBounds', { width, height });
    });

    // Charger l'interface
    const startUrl = isDev
        ? 'http://localhost:3000'  // Serveur de développement React
        : url.format({
            pathname: path.join(__dirname, 'build/index.html'),
            protocol: 'file:',
            slashes: true
        });

    mainWindow.loadURL(startUrl);

    // Ouvrir les DevTools en mode développement
    if (isDev) {
        mainWindow.webContents.openDevTools({ mode: 'detach' });
    }

    // Gérer la fermeture de la fenêtre
    mainWindow.on('close', (event) => {
        if (!isQuitting && store.get('minimizeToTray')) {
            event.preventDefault();
            mainWindow.hide();
            return false;
        }
    });

    // Événement de fermeture définitive
    mainWindow.on('closed', () => {
        mainWindow = null;
    });
}

/**
 * Crée l'icône dans la zone de notification
 */
function createTray() {
    tray = new Tray(path.join(__dirname, 'assets', 'icon.png'));

    const contextMenu = Menu.buildFromTemplate([
        {
            label: 'Ouvrir AppFlow',
            click: () => {
                if (mainWindow) {
                    mainWindow.show();
                } else {
                    createWindow();
                }
            }
        },
        {
            label: 'Démarrer le moteur',
            id: 'startEngine',
            click: startEngine,
            enabled: !engineRunning
        },
        {
            label: 'Arrêter le moteur',
            id: 'stopEngine',
            click: stopEngine,
            enabled: engineRunning
        },
        { type: 'separator' },
        {
            label: 'Quitter',
            click: () => {
                isQuitting = true;
                app.quit();
            }
        }
    ]);

    tray.setToolTip('AppFlow');
    tray.setContextMenu(contextMenu);

    tray.on('click', () => {
        if (mainWindow) {
            if (mainWindow.isVisible()) {
                mainWindow.focus();
            } else {
                mainWindow.show();
            }
        } else {
            createWindow();
        }
    });
}

/**
 * Démarre le processus Python du backend
 */
function startPythonBackend() {
    // Chercher le chemin Python approprié
    let pythonPath = store.get('pythonPath');
    if (!pythonPath) {
        // Utiliser 'python' par défaut si aucun chemin spécifique n'est défini
        pythonPath = 'python';
    }

    log.info(`Starting Python backend with: ${pythonPath}`);

    // Chemin vers le script principal Python
    const scriptPath = isDev
        ? path.join(__dirname, '..', 'main', 'appflow.py')
        : path.join(process.resourcesPath, 'app', 'main', 'appflow.py');

    // Vérifier si le fichier Python existe
    if (!fs.existsSync(scriptPath)) {
        log.error(`Python script not found at: ${scriptPath}`);
        dialog.showErrorBox(
            'Backend Error',
            `Le script Python n'a pas été trouvé à: ${scriptPath}\nL'application ne fonctionnera pas correctement.`
        );
        return;
    }

    // Démarrer le processus Python
    try {
        pythonProcess = spawn(pythonPath, [scriptPath, '--log-level', isDev ? 'DEBUG' : 'INFO']);

        pythonProcess.stdout.on('data', (data) => {
            log.info(`Python stdout: ${data}`);
        });

        pythonProcess.stderr.on('data', (data) => {
            log.error(`Python stderr: ${data}`);
        });

        pythonProcess.on('error', (error) => {
            log.error(`Failed to start Python process: ${error}`);
            dialog.showErrorBox(
                'Backend Error',
                `Impossible de démarrer le backend Python: ${error.message}`
            );
        });

        pythonProcess.on('close', (code) => {
            log.info(`Python process exited with code ${code}`);
            pythonProcess = null;
        });

        log.info('Python backend started successfully');
        return true;

    } catch (error) {
        log.error(`Exception starting Python process: ${error}`);
        dialog.showErrorBox(
            'Backend Error',
            `Une erreur est survenue lors du démarrage du backend Python: ${error.message}`
        );
        return false;
    }
}

/**
 * Démarre le moteur AppFlow
 */
async function startEngine() {
    try {
        const response = await axios.post(`${apiBaseUrl}/api/engine/start`);

        if (response.data.success) {
            engineRunning = true;
            updateTrayMenu();

            if (mainWindow) {
                mainWindow.webContents.send('engine-state-changed', { running: true });
            }

            log.info('Engine started successfully');
        } else {
            log.error(`Failed to start engine: ${response.data.status}`);
            dialog.showErrorBox(
                'Engine Error',
                `Impossible de démarrer le moteur: ${response.data.status}`
            );
        }
    } catch (error) {
        log.error(`Error starting engine: ${error}`);
        dialog.showErrorBox(
            'Engine Error',
            `Erreur lors du démarrage du moteur: ${error.message}`
        );
    }
}

/**
 * Arrête le moteur AppFlow
 */
async function stopEngine() {
    try {
        const response = await axios.post(`${apiBaseUrl}/api/engine/stop`);

        if (response.data.success) {
            engineRunning = false;
            updateTrayMenu();

            if (mainWindow) {
                mainWindow.webContents.send('engine-state-changed', { running: false });
            }

            log.info('Engine stopped successfully');
        } else {
            log.error(`Failed to stop engine: ${response.data.status}`);
        }
    } catch (error) {
        log.error(`Error stopping engine: ${error}`);
    }
}

/**
 * Met à jour le menu contextuel de l'icône de notification
 */
function updateTrayMenu() {
    if (!tray) return;

    const contextMenu = Menu.buildFromTemplate([
        {
            label: 'Ouvrir AppFlow',
            click: () => {
                if (mainWindow) {
                    mainWindow.show();
                } else {
                    createWindow();
                }
            }
        },
        {
            label: 'Démarrer le moteur',
            id: 'startEngine',
            click: startEngine,
            enabled: !engineRunning
        },
        {
            label: 'Arrêter le moteur',
            id: 'stopEngine',
            click: stopEngine,
            enabled: engineRunning
        },
        { type: 'separator' },
        {
            label: 'Quitter',
            click: () => {
                isQuitting = true;
                app.quit();
            }
        }
    ]);

    tray.setContextMenu(contextMenu);
}

/**
 * Vérifie l'état du moteur auprès de l'API
 */
async function checkEngineStatus() {
    try {
        const response = await axios.get(`${apiBaseUrl}/api/status`);
        engineRunning = response.data.status === 'running';
        updateTrayMenu();

        if (mainWindow) {
            mainWindow.webContents.send('engine-state-changed', { running: engineRunning });
        }

        log.info(`Engine status checked: ${engineRunning ? 'running' : 'stopped'}`);
        return true;
    } catch (error) {
        log.error(`Error checking engine status: ${error}`);
        return false;
    }
}

// Empêcher de lancer plusieurs instances de l'application
const gotTheLock = app.requestSingleInstanceLock();
if (!gotTheLock) {
    app.quit();
} else {
    app.on('second-instance', () => {
        // Si une deuxième instance est lancée, mettre en avant la fenêtre principale
        if (mainWindow) {
            if (mainWindow.isMinimized()) mainWindow.restore();
            mainWindow.show();
            mainWindow.focus();
        }
    });
}

// Événements d'application
app.on('ready', () => {
    log.info('Application ready');

    // Créer la fenêtre et l'icône
    if (!store.get('startMinimized')) {
        createWindow();
    }
    createTray();

    // Démarrer le backend Python
    const backendStarted = startPythonBackend();

    // Attendre que l'API soit disponible
    if (backendStarted) {
        setTimeout(async () => {
            const statusOk = await checkEngineStatus();

            // Démarrer automatiquement le moteur si configuré
            if (statusOk && store.get('autoStartEngine') && !engineRunning) {
                await startEngine();
            }
        }, 2000);  // Attendre 2 secondes pour que le backend démarre
    }
});

app.on('activate', () => {
    // Sur macOS, recréer une fenêtre quand l'icône du dock est cliquée
    if (mainWindow === null) {
        createWindow();
    }
});

app.on('window-all-closed', () => {
    // Sur macOS, l'application reste active jusqu'à ce que l'utilisateur quitte explicitement
    if (process.platform !== 'darwin' || isQuitting) {
        app.quit();
    }
});

app.on('before-quit', () => {
    isQuitting = true;

    // Arrêter proprement le processus Python
    if (pythonProcess) {
        log.info('Stopping Python backend...');
        pythonProcess.kill();
    }
});

// Gestionnaire de messages IPC (Inter-Process Communication)
ipcMain.handle('get-engine-status', async () => {
    await checkEngineStatus();
    return { running: engineRunning };
});

ipcMain.handle('start-engine', async () => {
    await startEngine();
    return { success: engineRunning };
});

ipcMain.handle('stop-engine', async () => {
    await stopEngine();
    return { success: !engineRunning };
});

ipcMain.handle('get-preferences', () => {
    return {
        startMinimized: store.get('startMinimized'),
        minimizeToTray: store.get('minimizeToTray'),
        autoStartEngine: store.get('autoStartEngine'),
        apiPort: store.get('apiPort'),
        darkMode: store.get('darkMode'),
        pythonPath: store.get('pythonPath')
    };
});

ipcMain.handle('set-preferences', (event, prefs) => {
    for (const [key, value] of Object.entries(prefs)) {
        store.set(key, value);
    }

    // Mettre à jour l'URL de l'API si le port a changé
    if (prefs.apiPort) {
        apiBaseUrl = `http://127.0.0.1:${prefs.apiPort}`;
    }

    return { success: true };
});

ipcMain.handle('open-external-link', (event, url) => {
    shell.openExternal(url);
});

ipcMain.handle('select-python-path', async () => {
    const result = await dialog.showOpenDialog({
        title: 'Sélectionner l\'exécutable Python',
        filters: [
            { name: 'Exécutables', extensions: ['exe'] }
        ],
        properties: ['openFile']
    });

    if (!result.canceled && result.filePaths.length > 0) {
        const pythonPath = result.filePaths[0];
        store.set('pythonPath', pythonPath);
        return pythonPath;
    }

    return null;
});
