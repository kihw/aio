/**
 * LogViewer - Composant de visualisation des logs en temps réel
 * 
 * Ce composant affiche les logs du système AppFlow en temps réel
 * et permet de filtrer par niveau d'importance, source, etc.
 */

import React, { useState, useEffect, useRef } from 'react';
import { Card, Button, Select, Input, Tooltip, Space, Typography, List, Tag } from 'antd';
import { ReloadOutlined, ClearOutlined, DownloadOutlined, PauseOutlined, PlayOutlined } from '@ant-design/icons';
import { fetchLogs, streamLogs } from '../services/api';

const { Option } = Select;
const { Search } = Input;
const { Text } = Typography;

const LogViewer = () => {
    const [logs, setLogs] = useState([]);
    const [streaming, setStreaming] = useState(true);
    const [filter, setFilter] = useState('');
    const [logLevel, setLogLevel] = useState('all');
    const [source, setSource] = useState('all');
    const logEndRef = useRef(null);

    // Options pour les filtres
    const logLevels = ['all', 'debug', 'info', 'warning', 'error', 'critical'];
    const logSources = ['all', 'rule_engine', 'action_executor', 'trigger_manager', 'process_manager', 'system_monitor', 'api'];

    // Couleurs par niveau de log
    const levelColors = {
        debug: '#8c8c8c',
        info: '#1890ff',
        warning: '#faad14',
        error: '#ff4d4f',
        critical: '#722ed1',
    };

    useEffect(() => {
        // Charger les logs initiaux
        loadInitialLogs();

        // Configuration du streaming des logs
        let stream;
        if (streaming) {
            stream = streamLogs((newLog) => {
                if (passesFilter(newLog)) {
                    setLogs((prevLogs) => [...prevLogs, newLog].slice(-1000)); // Garder max 1000 logs
                }
            });
        }

        return () => {
            if (stream && stream.close) {
                stream.close();
            }
        };
    }, [streaming, logLevel, source, filter]);

    useEffect(() => {
        // Scroll vers le bas quand de nouveaux logs arrivent si le scroll était déjà en bas
        if (logEndRef.current) {
            logEndRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [logs]);

    const loadInitialLogs = async () => {
        try {
            const logData = await fetchLogs({
                level: logLevel !== 'all' ? logLevel : undefined,
                source: source !== 'all' ? source : undefined,
                filter: filter || undefined,
                limit: 200
            });

            setLogs(logData);
        } catch (error) {
            console.error('Erreur lors du chargement des logs:', error);
        }
    };

    const passesFilter = (log) => {
        if (logLevel !== 'all' && log.level !== logLevel) return false;
        if (source !== 'all' && log.source !== source) return false;
        if (filter && !log.message.toLowerCase().includes(filter.toLowerCase())) return false;
        return true;
    };

    const handleClearLogs = () => {
        setLogs([]);
    };

    const handleDownloadLogs = () => {
        const logText = logs.map(log =>
            `${new Date(log.timestamp).toISOString()} [${log.level.toUpperCase()}] ${log.source}: ${log.message}`
        ).join('\n');

        const blob = new Blob([logText], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `appflow-logs-${new Date().toISOString().split('T')[0]}.log`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
    };

    const toggleStreaming = () => {
        setStreaming(!streaming);
    };

    return (
        <Card
            title="Logs du Système"
            className="log-viewer"
            extra={
                <Space>
                    <Tooltip title={streaming ? "Pause" : "Reprendre le streaming"}>
                        <Button
                            icon={streaming ? <PauseOutlined /> : <PlayOutlined />}
                            onClick={toggleStreaming}
                            type={streaming ? "primary" : "default"}
                        />
                    </Tooltip>
                    <Tooltip title="Rafraîchir">
                        <Button icon={<ReloadOutlined />} onClick={loadInitialLogs} />
                    </Tooltip>
                    <Tooltip title="Effacer">
                        <Button icon={<ClearOutlined />} onClick={handleClearLogs} />
                    </Tooltip>
                    <Tooltip title="Télécharger">
                        <Button icon={<DownloadOutlined />} onClick={handleDownloadLogs} />
                    </Tooltip>
                </Space>
            }
        >
            <div className="log-filters" style={{ marginBottom: 16 }}>
                <Space wrap>
                    <Select
                        value={logLevel}
                        onChange={setLogLevel}
                        style={{ width: 120 }}
                    >
                        {logLevels.map(level => (
                            <Option key={level} value={level}>
                                {level.charAt(0).toUpperCase() + level.slice(1)}
                            </Option>
                        ))}
                    </Select>

                    <Select
                        value={source}
                        onChange={setSource}
                        style={{ width: 150 }}
                    >
                        {logSources.map(src => (
                            <Option key={src} value={src}>
                                {src === 'all' ? 'Toutes Sources' : src}
                            </Option>
                        ))}
                    </Select>

                    <Search
                        placeholder="Filtrer les messages"
                        allowClear
                        onSearch={setFilter}
                        style={{ width: 250 }}
                    />
                </Space>
            </div>

            <div className="log-container" style={{
                height: '60vh',
                overflowY: 'auto',
                backgroundColor: '#f5f5f5',
                padding: '10px',
                borderRadius: '4px',
                fontFamily: 'monospace'
            }}>
                <List
                    dataSource={logs}
                    renderItem={(log) => (
                        <div className="log-entry" style={{ marginBottom: '4px' }}>
                            <Text type="secondary" style={{ marginRight: '8px' }}>
                                {new Date(log.timestamp).toLocaleTimeString()}
                            </Text>
                            <Tag color={levelColors[log.level] || '#d9d9d9'}>
                                {log.level.toUpperCase()}
                            </Tag>
                            <Text strong style={{ marginRight: '8px', marginLeft: '8px' }}>
                                {log.source}:
                            </Text>
                            <Text>{log.message}</Text>
                        </div>
                    )}
                />
                <div ref={logEndRef} />
            </div>
        </Card>
    );
};

export default LogViewer;
