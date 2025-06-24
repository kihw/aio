/**
 * API Service - Communication avec le backend Flask
 * 
 * Ce fichier contient toutes les fonctions pour communiquer avec l'API backend
 * d'AppFlow, notamment la gestion des règles, le contrôle du moteur et les logs.
 */

const API_BASE_URL = 'http://localhost:5000/api';

/**
 * Configuration de base pour les requêtes fetch
 */
const defaultOptions = {
    headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
};

/**
 * Fonction utilitaire pour les appels à l'API
 */
const apiCall = async (endpoint, method = 'GET', data = null) => {
    const url = `${API_BASE_URL}${endpoint}`;

    const options = {
        ...defaultOptions,
        method,
    };

    if (data && (method === 'POST' || method === 'PUT' || method === 'PATCH')) {
        options.body = JSON.stringify(data);
    }

    try {
        const response = await fetch(url, options);

        // Si la réponse n'est pas ok
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({
                message: `HTTP Error: ${response.status} ${response.statusText}`
            }));
            throw new Error(errorData.message || `HTTP Error: ${response.status}`);
        }

        // Si la réponse est vide ou pas du JSON
        if (response.status === 204 || response.headers.get('content-length') === '0') {
            return null;
        }

        // Sinon retourner le JSON
        return await response.json();
    } catch (error) {
        console.error(`API Error (${method} ${endpoint}):`, error);
        throw error;
    }
};

/**
 * API Engine - Contrôle du moteur
 */
export const fetchEngineStatus = () => apiCall('/engine/status');
export const startEngine = () => apiCall('/engine/start', 'POST');
export const stopEngine = () => apiCall('/engine/stop', 'POST');
export const restartEngine = () => apiCall('/engine/restart', 'POST');

/**
 * API Rules - Gestion des règles
 */
export const fetchRules = () => apiCall('/rules');
export const fetchRule = (id) => apiCall(`/rules/${id}`);
export const createRule = (rule) => apiCall('/rules', 'POST', rule);
export const updateRule = (id, rule) => apiCall(`/rules/${id}`, 'PUT', rule);
export const deleteRule = (id) => apiCall(`/rules/${id}`, 'DELETE');
export const toggleRule = (id, enabled) => apiCall(`/rules/${id}/toggle`, 'POST', { enabled });

/**
 * API Logs - Gestion des logs
 */
export const fetchLogs = (params = {}) => {
    const queryParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) {
            queryParams.append(key, value);
        }
    });

    return apiCall(`/logs?${queryParams.toString()}`);
};

/**
 * Streaming des logs en temps réel via EventSource
 */
export const streamLogs = (onLogReceived) => {
    if (!window.EventSource) {
        console.error('EventSource n\'est pas supporté par ce navigateur');
        return null;
    }

    const source = new EventSource(`${API_BASE_URL}/logs/stream`);

    source.addEventListener('log', (event) => {
        try {
            const logData = JSON.parse(event.data);
            onLogReceived(logData);
        } catch (err) {
            console.error('Erreur lors du parsing des données de log:', err);
        }
    });

    source.addEventListener('error', (event) => {
        console.error('Erreur sur le stream de logs:', event);
        if (event.target.readyState === EventSource.CLOSED) {
            console.log('Stream de logs fermé par le serveur');
        }
    });

    return source; // Retourner la source pour permettre sa fermeture
};

/**
 * API Metrics - Métriques système
 */
export const fetchSystemMetrics = () => apiCall('/metrics/system');
export const fetchProcessMetrics = () => apiCall('/metrics/processes');

/**
 * API Processes - Gestion des processus
 */
export const fetchRunningProcesses = () => apiCall('/processes');
export const fetchProcessDetails = (pid) => apiCall(`/processes/${pid}`);
export const killProcess = (pid) => apiCall(`/processes/${pid}/kill`, 'POST');
export const startProcess = (command, args = []) => apiCall('/processes/start', 'POST', { command, args });

/**
 * API Config - Gestion de la configuration
 */
export const fetchConfig = () => apiCall('/config');
export const updateConfig = (config) => apiCall('/config', 'PUT', config);
export const reloadConfig = () => apiCall('/config/reload', 'POST');
