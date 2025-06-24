/**
 * EngineController - Composant de contrôle du moteur AppFlow
 * 
 * Ce composant permet de démarrer, arrêter et redémarrer le moteur AppFlow,
 * ainsi que d'afficher son état actuel et des métriques de base.
 */

import React, { useState, useEffect } from 'react';
import { Card, Button, Statistic, Row, Col, Progress, Tooltip, Badge, Space, Alert } from 'antd';
import {
    PlayCircleOutlined,
    PauseCircleOutlined,
    ReloadOutlined,
    SettingOutlined,
    DashboardOutlined
} from '@ant-design/icons';
import { fetchEngineStatus, startEngine, stopEngine, restartEngine } from '../services/api';

const EngineController = () => {
    const [status, setStatus] = useState({
        running: false,
        uptime: 0,
        activeRules: 0,
        totalRules: 0,
        memory_usage: 0,
        cpu_usage: 0,
        last_error: null,
    });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    useEffect(() => {
        // Charger le statut initial
        loadStatus();

        // Mettre à jour le statut toutes les 3 secondes
        const interval = setInterval(loadStatus, 3000);
        return () => clearInterval(interval);
    }, []);

    const loadStatus = async () => {
        try {
            const data = await fetchEngineStatus();
            setStatus(data);
            setError(null);
        } catch (err) {
            console.error("Erreur lors du chargement du statut:", err);
            setError("Impossible de communiquer avec le serveur AppFlow");
        }
    };

    const handleStart = async () => {
        setLoading(true);
        try {
            await startEngine();
            await loadStatus();
        } catch (err) {
            setError("Erreur lors du démarrage: " + err.message);
        } finally {
            setLoading(false);
        }
    };

    const handleStop = async () => {
        setLoading(true);
        try {
            await stopEngine();
            await loadStatus();
        } catch (err) {
            setError("Erreur lors de l'arrêt: " + err.message);
        } finally {
            setLoading(false);
        }
    };

    const handleRestart = async () => {
        setLoading(true);
        try {
            await restartEngine();
            await loadStatus();
        } catch (err) {
            setError("Erreur lors du redémarrage: " + err.message);
        } finally {
            setLoading(false);
        }
    };

    const formatUptime = (seconds) => {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);

        return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    };

    return (
        <Card title="Contrôle du Moteur" className="engine-controller">
            {error && (
                <Alert
                    message="Erreur"
                    description={error}
                    type="error"
                    showIcon
                    closable
                    style={{ marginBottom: 16 }}
                />
            )}

            <Row gutter={16} style={{ marginBottom: 24 }}>
                <Col span={12}>
                    <Card bordered={false}>
                        <Statistic
                            title="État du Moteur"
                            value={status.running ? "Actif" : "Arrêté"}
                            valueStyle={{ color: status.running ? '#52c41a' : '#ff4d4f' }}
                            prefix={status.running ? <Badge status="processing" color="green" /> : <Badge status="default" />}
                        />
                    </Card>
                </Col>
                <Col span={12}>
                    <Card bordered={false}>
                        <Statistic
                            title="Temps d'Activité"
                            value={formatUptime(status.uptime)}
                            prefix={<DashboardOutlined />}
                        />
                    </Card>
                </Col>
            </Row>

            <Row gutter={16} style={{ marginBottom: 24 }}>
                <Col span={12}>
                    <Tooltip title="Utilisation CPU">
                        <Progress
                            type="dashboard"
                            percent={Math.round(status.cpu_usage)}
                            status={status.cpu_usage > 80 ? "exception" : "active"}
                            format={percent => `${percent}%`}
                        />
                    </Tooltip>
                </Col>
                <Col span={12}>
                    <Tooltip title="Utilisation Mémoire">
                        <Progress
                            type="dashboard"
                            percent={Math.round(status.memory_usage)}
                            status={status.memory_usage > 80 ? "exception" : "active"}
                            format={percent => `${percent}%`}
                        />
                    </Tooltip>
                </Col>
            </Row>

            <Row gutter={16}>
                <Col span={24}>
                    <Statistic
                        title="Règles Actives"
                        value={`${status.activeRules} / ${status.totalRules}`}
                        suffix="règles"
                    />
                </Col>
            </Row>

            <div className="controller-actions" style={{ marginTop: 24 }}>
                <Space size="middle">
                    <Tooltip title={status.running ? "Arrêter le Moteur" : "Démarrer le Moteur"}>
                        <Button
                            type="primary"
                            shape="round"
                            icon={status.running ? <PauseCircleOutlined /> : <PlayCircleOutlined />}
                            size="large"
                            loading={loading}
                            onClick={status.running ? handleStop : handleStart}
                        >
                            {status.running ? "Arrêter" : "Démarrer"}
                        </Button>
                    </Tooltip>

                    <Tooltip title="Redémarrer le Moteur">
                        <Button
                            type="default"
                            shape="round"
                            icon={<ReloadOutlined />}
                            size="large"
                            loading={loading}
                            onClick={handleRestart}
                            disabled={!status.running}
                        >
                            Redémarrer
                        </Button>
                    </Tooltip>

                    <Tooltip title="Configuration">
                        <Button
                            shape="circle"
                            icon={<SettingOutlined />}
                            size="large"
                        />
                    </Tooltip>
                </Space>
            </div>
        </Card>
    );
};

export default EngineController;
