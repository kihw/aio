/**
 * RulesList - Composant d'affichage et de gestion des règles
 * 
 * Ce composant affiche la liste des règles configurées dans AppFlow
 * et permet leur activation/désactivation ainsi que leur édition.
 */

import React, { useState, useEffect } from 'react';
import { Table, Button, Badge, Switch, Tooltip, message, Drawer, Form, Input, Select } from 'antd';
import { EditOutlined, DeleteOutlined, PlusOutlined } from '@ant-design/icons';
import RuleEditor from './RuleEditor';
import { fetchRules, toggleRule, deleteRule } from '../services/api';

const { Option } = Select;

const RulesList = () => {
    const [rules, setRules] = useState([]);
    const [loading, setLoading] = useState(true);
    const [editingRule, setEditingRule] = useState(null);
    const [drawerVisible, setDrawerVisible] = useState(false);

    useEffect(() => {
        loadRules();
        // Recharger les règles toutes les 10 secondes
        const interval = setInterval(loadRules, 10000);
        return () => clearInterval(interval);
    }, []);

    const loadRules = async () => {
        try {
            const data = await fetchRules();
            setRules(data);
            setLoading(false);
        } catch (error) {
            message.error('Erreur lors du chargement des règles: ' + error.message);
            setLoading(false);
        }
    };

    const handleToggleRule = async (ruleId, enabled) => {
        try {
            await toggleRule(ruleId, enabled);
            message.success(`Règle ${enabled ? 'activée' : 'désactivée'}`);
            loadRules();
        } catch (error) {
            message.error('Erreur lors de la modification: ' + error.message);
        }
    };

    const handleDeleteRule = async (ruleId) => {
        try {
            await deleteRule(ruleId);
            message.success('Règle supprimée avec succès');
            loadRules();
        } catch (error) {
            message.error('Erreur lors de la suppression: ' + error.message);
        }
    };

    const handleEditRule = (rule) => {
        setEditingRule(rule);
        setDrawerVisible(true);
    };

    const handleNewRule = () => {
        setEditingRule(null);
        setDrawerVisible(true);
    };

    const closeDrawer = () => {
        setDrawerVisible(false);
        setEditingRule(null);
    };

    const handleSaveRule = async () => {
        // Logique de sauvegarde gérée par le composant RuleEditor
        closeDrawer();
        await loadRules();
    };

    const columns = [
        {
            title: 'Nom',
            dataIndex: 'name',
            key: 'name',
        },
        {
            title: 'Description',
            dataIndex: 'description',
            key: 'description',
            ellipsis: true,
        },
        {
            title: 'Type',
            dataIndex: 'trigger_type',
            key: 'trigger_type',
            render: (type) => {
                let color = 'blue';
                switch (type) {
                    case 'time': color = 'green'; break;
                    case 'cpu': color = 'orange'; break;
                    case 'memory': color = 'purple'; break;
                    case 'battery': color = 'red'; break;
                    case 'network': color = 'cyan'; break;
                    default: color = 'blue';
                }
                return <Badge color={color} text={type} />;
            }
        },
        {
            title: 'Status',
            key: 'enabled',
            dataIndex: 'enabled',
            render: (enabled, record) => (
                <Switch
                    checked={enabled}
                    onChange={(checked) => handleToggleRule(record.id, checked)}
                />
            ),
        },
        {
            title: 'Actions',
            key: 'actions',
            render: (_, record) => (
                <>
                    <Tooltip title="Éditer">
                        <Button
                            type="text"
                            icon={<EditOutlined />}
                            onClick={() => handleEditRule(record)}
                        />
                    </Tooltip>
                    <Tooltip title="Supprimer">
                        <Button
                            type="text"
                            danger
                            icon={<DeleteOutlined />}
                            onClick={() => handleDeleteRule(record.id)}
                        />
                    </Tooltip>
                </>
            ),
        },
    ];

    return (
        <div className="rules-list">
            <div className="rules-header" style={{ marginBottom: 16 }}>
                <Button
                    type="primary"
                    icon={<PlusOutlined />}
                    onClick={handleNewRule}
                >
                    Nouvelle Règle
                </Button>
            </div>

            <Table
                columns={columns}
                dataSource={rules}
                rowKey="id"
                loading={loading}
                pagination={{ pageSize: 10 }}
            />

            <Drawer
                title={editingRule ? 'Éditer une règle' : 'Nouvelle règle'}
                placement="right"
                closable={true}
                onClose={closeDrawer}
                visible={drawerVisible}
                width={600}
            >
                {drawerVisible && (
                    <RuleEditor
                        rule={editingRule}
                        onSave={handleSaveRule}
                        onCancel={closeDrawer}
                    />
                )}
            </Drawer>
        </div>
    );
};

export default RulesList;
