import React, { useState, useEffect } from 'react';
import { MantineProvider, AppShell, ColorSchemeProvider, Group } from '@mantine/core';
import { NotificationsProvider } from '@mantine/notifications';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';

// Components
import AppHeader from './components/AppHeader';
import AppNavbar from './components/AppNavbar';
import Dashboard from './pages/Dashboard';
import RulesManager from './pages/RulesManager';
import ProcessesViewer from './pages/ProcessesViewer';
import LogViewer from './pages/LogViewer';
import Settings from './pages/Settings';
import AboutPage from './pages/AboutPage';

// API Service
import ApiService from './services/api';

function App() {
    const [colorScheme, setColorScheme] = useState('light');
    const [engineStatus, setEngineStatus] = useState({ running: false, loading: true });
    const [navbarOpened, setNavbarOpened] = useState(true);

    // Vérification de l'état du moteur au démarrage
    useEffect(() => {
        const checkEngineStatus = async () => {
            try {
                const status = await window.electronAPI.getEngineStatus();
                setEngineStatus({ running: status.running, loading: false });
            } catch (error) {
                console.error('Error checking engine status:', error);
                setEngineStatus({ running: false, loading: false });
            }
        };

        checkEngineStatus();

        // Écouter les changements d'état du moteur
        const handleEngineStateChange = (event, state) => {
            setEngineStatus({ running: state.running, loading: false });
        };

        window.electronAPI.onEngineStateChanged(handleEngineStateChange);

        return () => {
            window.electronAPI.removeEngineStateListener(handleEngineStateChange);
        };
    }, []);

    // Basculer entre les thèmes clair et sombre
    const toggleColorScheme = () => {
        setColorScheme(colorScheme === 'dark' ? 'light' : 'dark');
    };

    // Démarre le moteur AppFlow
    const startEngine = async () => {
        setEngineStatus({ ...engineStatus, loading: true });
        try {
            const result = await window.electronAPI.startEngine();
            setEngineStatus({ running: result.success, loading: false });
        } catch (error) {
            console.error('Error starting engine:', error);
            setEngineStatus({ ...engineStatus, loading: false });
        }
    };

    // Arrête le moteur AppFlow
    const stopEngine = async () => {
        setEngineStatus({ ...engineStatus, loading: true });
        try {
            const result = await window.electronAPI.stopEngine();
            setEngineStatus({ running: !result.success, loading: false });
        } catch (error) {
            console.error('Error stopping engine:', error);
            setEngineStatus({ ...engineStatus, loading: false });
        }
    };

    return (
        <ColorSchemeProvider colorScheme={colorScheme} toggleColorScheme={toggleColorScheme}>
            <MantineProvider
                theme={{ colorScheme, primaryColor: 'blue' }}
                withGlobalStyles
                withNormalizeCSS
            >
                <NotificationsProvider>
                    <Router>
                        <AppShell
                            padding="md"
                            navbar={
                                <AppNavbar
                                    opened={navbarOpened}
                                    engineStatus={engineStatus}
                                    startEngine={startEngine}
                                    stopEngine={stopEngine}
                                />
                            }
                            header={
                                <AppHeader
                                    colorScheme={colorScheme}
                                    toggleColorScheme={toggleColorScheme}
                                    navbarOpened={navbarOpened}
                                    setNavbarOpened={setNavbarOpened}
                                    engineStatus={engineStatus}
                                />
                            }
                            styles={(theme) => ({
                                main: { backgroundColor: theme.colorScheme === 'dark' ? theme.colors.dark[8] : theme.colors.gray[0] }
                            })}
                        >
                            <Routes>
                                <Route path="/" element={<Dashboard />} />
                                <Route path="/rules" element={<RulesManager />} />
                                <Route path="/processes" element={<ProcessesViewer />} />
                                <Route path="/logs" element={<LogViewer />} />
                                <Route path="/settings" element={<Settings />} />
                                <Route path="/about" element={<AboutPage />} />
                            </Routes>
                        </AppShell>
                    </Router>
                </NotificationsProvider>
            </MantineProvider>
        </ColorSchemeProvider>
    );
}

export default App;
