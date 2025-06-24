import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import RulesList from '../../components/RulesList';

// Mock des services d'API
jest.mock('../../services/api', () => ({
    fetchRules: jest.fn().mockResolvedValue([
        {
            id: '1',
            name: 'Test Rule',
            description: 'Rule for testing',
            trigger_type: 'time',
            enabled: true
        },
        {
            id: '2',
            name: 'CPU Rule',
            description: 'CPU monitoring rule',
            trigger_type: 'cpu',
            enabled: false
        }
    ]),
    toggleRule: jest.fn().mockResolvedValue({ success: true }),
    deleteRule: jest.fn().mockResolvedValue({ success: true })
}));

// Mock pour antd
jest.mock('antd', () => {
    const antd = jest.requireActual('antd');

    // Mock des composants antd utilisés dans RulesList
    const mockMessage = {
        success: jest.fn(),
        error: jest.fn()
    };

    return {
        ...antd,
        message: mockMessage,
        Table: ({ dataSource, columns }) => (
            <div data-testid="mock-table">
                {dataSource?.map(item => (
                    <div key={item.id} data-testid={`rule-${item.id}`}>
                        <span>{item.name}</span>
                        <span>{item.description}</span>
                        <span>{item.trigger_type}</span>
                        <span>{item.enabled ? 'Activé' : 'Désactivé'}</span>
                        {columns
                            .filter(col => col.key === 'actions')
                            .map(col => (
                                <div key="actions">
                                    <button onClick={() => col.render(null, item)}>Actions</button>
                                </div>
                            ))}
                    </div>
                ))}
            </div>
        ),
        Button: ({ children, onClick, icon }) => (
            <button onClick={onClick} data-testid={`button-${children?.toString().toLowerCase()}`}>
                {icon && <span>{icon.type.render().props.children}</span>}
                {children}
            </button>
        ),
        Switch: ({ checked, onChange }) => (
            <input
                type="checkbox"
                checked={checked}
                onChange={e => onChange(e.target.checked)}
                data-testid="rule-toggle"
            />
        ),
        Tooltip: ({ children }) => children,
        Badge: ({ text }) => <span>{text}</span>,
        Drawer: ({ children, visible }) => visible ? <div>{children}</div> : null
    };
});

// Mock pour le composant RuleEditor qui est utilisé dans RulesList
jest.mock('../../components/RuleEditor', () => {
    return function MockRuleEditor({ rule, onSave, onCancel }) {
        return (
            <div data-testid="rule-editor">
                <span>Editing: {rule ? rule.name : 'New Rule'}</span>
                <button onClick={onSave} data-testid="save-button">Save</button>
                <button onClick={onCancel} data-testid="cancel-button">Cancel</button>
            </div>
        );
    };
});

describe('RulesList Component', () => {
    beforeEach(() => {
        jest.clearAllMocks();
    });

    test('displays rules from API', async () => {
        render(<RulesList />);

        // Vérifier que les règles sont affichées après chargement
        await waitFor(() => {
            expect(screen.getByText('Test Rule')).toBeInTheDocument();
            expect(screen.getByText('CPU Rule')).toBeInTheDocument();
        });
    });

    test('toggles rule status', async () => {
        const { fetchRules, toggleRule } = require('../../services/api');

        render(<RulesList />);

        // Attendre que les règles soient chargées
        await waitFor(() => {
            expect(screen.getByText('Test Rule')).toBeInTheDocument();
        });

        // Trouver et cliquer sur le switch pour la règle
        const toggleSwitch = screen.getByTestId('rule-toggle');
        userEvent.click(toggleSwitch);

        // Vérifier que l'API a été appelée
        expect(toggleRule).toHaveBeenCalledWith('1', false);

        // Vérifier que les règles sont rechargées
        await waitFor(() => {
            expect(fetchRules).toHaveBeenCalledTimes(2);
        });
    });

    test('opens rule editor when creating new rule', async () => {
        render(<RulesList />);

        // Attendre que le composant soit chargé
        await waitFor(() => {
            expect(screen.getByText('Test Rule')).toBeInTheDocument();
        });

        // Cliquer sur le bouton Nouvelle Règle
        const newRuleButton = screen.getByTestId('button-nouvelle règle');
        userEvent.click(newRuleButton);

        // Vérifier que l'éditeur de règle s'affiche
        await waitFor(() => {
            expect(screen.getByTestId('rule-editor')).toBeInTheDocument();
            expect(screen.getByText('Editing: New Rule')).toBeInTheDocument();
        });
    });

    test('opens rule editor when editing existing rule', async () => {
        render(<RulesList />);

        // Attendre que le composant soit chargé
        await waitFor(() => {
            expect(screen.getByText('Test Rule')).toBeInTheDocument();
        });

        // Cliquer sur le bouton Actions de la première règle
        const actionButton = screen.getByText('Actions');
        userEvent.click(actionButton);

        // Vérifier que l'éditeur de règle s'affiche
        await waitFor(() => {
            expect(screen.getByTestId('rule-editor')).toBeInTheDocument();
            expect(screen.getByText(/Editing: .+/)).toBeInTheDocument();
        });
    });

    test('handles API errors gracefully', async () => {
        // Émuler une erreur d'API
        const { fetchRules } = require('../../services/api');
        fetchRules.mockRejectedValueOnce(new Error('Failed to fetch rules'));

        const { message } = require('antd');

        render(<RulesList />);

        // Attendre que l'erreur soit traitée
        await waitFor(() => {
            expect(message.error).toHaveBeenCalledWith('Erreur lors du chargement des règles: Failed to fetch rules');
        });
    });
});
