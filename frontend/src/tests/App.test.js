import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from '../App';

// Mock des services d'API
jest.mock('../services/api', () => ({
    fetchEngineStatus: jest.fn().mockResolvedValue({
        running: true,
        uptime: 3600,
        activeRules: 3,
        totalRules: 5,
        memory_usage: 25,
        cpu_usage: 10
    }),
    fetchRules: jest.fn().mockResolvedValue([
        {
            id: '1',
            name: 'Test Rule',
            description: 'Rule for testing',
            trigger_type: 'time',
            enabled: true
        }
    ]),
    fetchLogs: jest.fn().mockResolvedValue([
        {
            timestamp: '2023-06-24T10:00:00',
            level: 'info',
            source: 'rule_engine',
            message: 'Test log message'
        }
    ])
}));

describe('App Component', () => {
    test('renders application title', () => {
        render(<App />);
        const titleElement = screen.getByText(/AppFlow/i);
        expect(titleElement).toBeInTheDocument();
    });

    test('renders main navigation components', async () => {
        render(<App />);

        // Vérifier que les éléments de navigation principaux sont présents
        expect(screen.getByText(/Tableau de bord/i)).toBeInTheDocument();
        expect(screen.getByText(/Règles/i)).toBeInTheDocument();
        expect(screen.getByText(/Logs/i)).toBeInTheDocument();
        expect(screen.getByText(/Processus/i)).toBeInTheDocument();
        expect(screen.getByText(/Configuration/i)).toBeInTheDocument();
    });

    test('switches between pages when navigation is clicked', async () => {
        render(<App />);

        // Cliquer sur l'onglet Règles
        userEvent.click(screen.getByText(/Règles/i));

        // Attendre que la page des règles soit affichée
        await waitFor(() => {
            expect(screen.getByText(/Nouvelle Règle/i)).toBeInTheDocument();
        });

        // Cliquer sur l'onglet Logs
        userEvent.click(screen.getByText(/Logs/i));

        // Attendre que la page des logs soit affichée
        await waitFor(() => {
            expect(screen.getByText(/Logs du Système/i)).toBeInTheDocument();
        });
    });

    test('displays engine status information', async () => {
        render(<App />);

        // Attendre que les données du moteur soient chargées et affichées
        await waitFor(() => {
            expect(screen.getByText(/État du Moteur/i)).toBeInTheDocument();
            expect(screen.getByText(/Actif/i)).toBeInTheDocument();
        });
    });

    test('displays rules information', async () => {
        render(<App />);

        // Aller à l'onglet Règles
        userEvent.click(screen.getByText(/Règles/i));

        // Attendre que les données des règles soient chargées et affichées
        await waitFor(() => {
            expect(screen.getByText(/Test Rule/i)).toBeInTheDocument();
            expect(screen.getByText(/Rule for testing/i)).toBeInTheDocument();
        });
    });

    test('handles errors gracefully', async () => {
        // Émuler une erreur d'API
        require('../services/api').fetchEngineStatus.mockRejectedValueOnce(
            new Error('Failed to fetch engine status')
        );

        render(<App />);

        // Attendre que le message d'erreur soit affiché
        await waitFor(() => {
            expect(screen.getByText(/Erreur/i)).toBeInTheDocument();
        });
    });
});
