# API Documentation AppFlow

Cette documentation décrit l'API REST exposée par le serveur Flask d'AppFlow.

## Informations générales

- Base URL: `http://localhost:5000/api`
- Format de réponse: JSON
- Authentification: Non requise (version locale uniquement)

## Liste des endpoints

### Status du moteur

#### GET /api/engine/status

Retourne l'état actuel du moteur AppFlow.

**Réponse**

```json
{
  "running": true,
  "uptime": 3600,
  "activeRules": 3,
  "totalRules": 5,
  "memory_usage": 25.4,
  "cpu_usage": 10.2,
  "last_error": null
}
```

#### POST /api/engine/start

Démarre le moteur AppFlow.

**Réponse**

```json
{
  "success": true,
  "message": "Engine started successfully"
}
```

#### POST /api/engine/stop

Arrête le moteur AppFlow.

**Réponse**

```json
{
  "success": true,
  "message": "Engine stopped successfully"
}
```

#### POST /api/engine/restart

Redémarre le moteur AppFlow.

**Réponse**

```json
{
  "success": true,
  "message": "Engine restarted successfully"
}
```

### Règles

#### GET /api/rules

Liste toutes les règles configurées.

**Paramètres**

- `enabled` (optionnel): Filtrer par état d'activation (true/false)
- `type` (optionnel): Filtrer par type de déclencheur (time, cpu, battery, etc.)

**Réponse**

```json
[
  {
    "id": "rule1",
    "name": "Navigateur au démarrage",
    "description": "Lance Chrome au démarrage du système",
    "trigger_type": "system",
    "enabled": true,
    "last_triggered": "2023-06-24T10:30:45"
  },
  {
    "id": "rule2",
    "name": "Fermeture de nuit",
    "description": "Ferme les applications non utilisées la nuit",
    "trigger_type": "time",
    "enabled": true,
    "last_triggered": "2023-06-23T22:30:00"
  }
]
```

#### GET /api/rules/{id}

Récupère les détails d'une règle spécifique.

**Réponse**

```json
{
  "id": "rule1",
  "name": "Navigateur au démarrage",
  "description": "Lance Chrome au démarrage du système",
  "enabled": true,
  "trigger": {
    "type": "system",
    "event": "startup",
    "delay": 10
  },
  "condition": {
    "time_range": {
      "start": "08:00",
      "end": "20:00"
    },
    "weekday": [1, 2, 3, 4, 5]
  },
  "actions": {
    "launch": {
      "app": "chrome",
      "args": ["--start-maximized"]
    }
  },
  "last_triggered": "2023-06-24T10:30:45",
  "created_at": "2023-06-01T09:00:00",
  "updated_at": "2023-06-15T14:22:30"
}
```

#### POST /api/rules

Crée une nouvelle règle.

**Corps de la requête**

```json
{
  "name": "Nouvelle règle",
  "description": "Description de la règle",
  "enabled": true,
  "trigger": {
    "type": "time",
    "schedule": "09:00"
  },
  "condition": {
    "weekday": [1, 2, 3, 4, 5]
  },
  "actions": {
    "launch": {
      "app": "notepad",
      "args": []
    }
  }
}
```

**Réponse**

```json
{
  "id": "rule3",
  "name": "Nouvelle règle",
  "message": "Rule created successfully"
}
```

#### PUT /api/rules/{id}

Met à jour une règle existante.

**Corps de la requête**

Même format que pour la création.

**Réponse**

```json
{
  "id": "rule1",
  "message": "Rule updated successfully"
}
```

#### DELETE /api/rules/{id}

Supprime une règle.

**Réponse**

```json
{
  "success": true,
  "message": "Rule deleted successfully"
}
```

#### POST /api/rules/{id}/toggle

Active ou désactive une règle.

**Corps de la requête**

```json
{
  "enabled": false
}
```

**Réponse**

```json
{
  "id": "rule1",
  "enabled": false,
  "message": "Rule disabled successfully"
}
```

### Logs

#### GET /api/logs

Récupère les logs du système.

**Paramètres**

- `level` (optionnel): Filtrer par niveau de log (debug, info, warning, error, critical)
- `source` (optionnel): Filtrer par source (rule_engine, action_executor, etc.)
- `from` (optionnel): Date de début (format ISO)
- `to` (optionnel): Date de fin (format ISO)
- `limit` (optionnel): Nombre maximum de logs à retourner (défaut: 100)
- `filter` (optionnel): Filtrer les messages contenant cette chaîne

**Réponse**

```json
[
  {
    "timestamp": "2023-06-24T10:30:45",
    "level": "info",
    "source": "rule_engine",
    "message": "Rule 'Navigateur au démarrage' triggered"
  },
  {
    "timestamp": "2023-06-24T10:30:46",
    "level": "info",
    "source": "action_executor",
    "message": "Launching application 'chrome'"
  }
]
```

#### GET /api/logs/stream

Point d'accès pour le streaming de logs en temps réel (Server-Sent Events).

**Format d'événement**

```
event: log
data: {"timestamp":"2023-06-24T10:35:20","level":"info","source":"rule_engine","message":"Rule check completed"}

```

### Processus

#### GET /api/processes

Liste tous les processus en cours d'exécution.

**Réponse**

```json
[
  {
    "pid": 1234,
    "name": "chrome.exe",
    "cpu_percent": 5.2,
    "memory_percent": 10.5,
    "status": "running",
    "created": "2023-06-24T08:30:00"
  },
  {
    "pid": 5678,
    "name": "firefox.exe",
    "cpu_percent": 3.8,
    "memory_percent": 8.2,
    "status": "running",
    "created": "2023-06-24T09:15:30"
  }
]
```

#### GET /api/processes/{pid}

Récupère les détails d'un processus spécifique.

**Réponse**

```json
{
  "pid": 1234,
  "name": "chrome.exe",
  "cpu_percent": 5.2,
  "memory_percent": 10.5,
  "status": "running",
  "created": "2023-06-24T08:30:00",
  "command_line": ["C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe", "--profile-directory=Default"],
  "user": "username",
  "threads": 24
}
```

#### POST /api/processes/start

Démarre un nouveau processus.

**Corps de la requête**

```json
{
  "command": "notepad.exe",
  "args": ["C:\\test.txt"]
}
```

**Réponse**

```json
{
  "success": true,
  "pid": 9876,
  "message": "Process started successfully"
}
```

#### POST /api/processes/{pid}/kill

Termine un processus en cours d'exécution.

**Réponse**

```json
{
  "success": true,
  "message": "Process killed successfully"
}
```

### Métriques système

#### GET /api/metrics/system

Récupère les métriques du système.

**Réponse**

```json
{
  "cpu": {
    "usage_percent": 45.2,
    "cores": 8,
    "temperature": 65.0
  },
  "memory": {
    "total": 16384,
    "used": 8192,
    "percent": 50.0
  },
  "battery": {
    "percent": 75,
    "power_connected": true,
    "time_remaining": 120
  },
  "network": {
    "connected": true,
    "type": "wifi",
    "download_speed": 25.4,
    "upload_speed": 5.2
  },
  "disk": {
    "total": 500000,
    "used": 250000,
    "percent": 50.0
  }
}
```

#### GET /api/metrics/processes

Récupère les métriques d'utilisation des ressources par processus.

**Réponse**

```json
{
  "total_cpu": 65.3,
  "total_memory": 75.2,
  "processes": [
    {
      "pid": 1234,
      "name": "chrome.exe",
      "cpu_percent": 15.2,
      "memory_percent": 20.5
    },
    {
      "pid": 5678,
      "name": "firefox.exe",
      "cpu_percent": 10.8,
      "memory_percent": 15.2
    }
  ]
}
```

### Configuration

#### GET /api/config

Récupère la configuration actuelle.

**Réponse**

```json
{
  "engine": {
    "check_interval": 5,
    "max_concurrent_actions": 3
  },
  "ui": {
    "theme": "light",
    "refresh_interval": 3000
  },
  "notifications": {
    "enabled": true,
    "level": "info"
  },
  "logging": {
    "level": "info",
    "max_size": 10485760,
    "backup_count": 3
  },
  "rules_dir": "C:\\Users\\username\\AppData\\Local\\AppFlow\\rules"
}
```

#### PUT /api/config

Met à jour la configuration.

**Corps de la requête**

Format partial ou complet de la configuration.

**Réponse**

```json
{
  "success": true,
  "message": "Configuration updated successfully"
}
```

#### POST /api/config/reload

Recharge la configuration depuis le disque.

**Réponse**

```json
{
  "success": true,
  "message": "Configuration reloaded successfully"
}
```

## Codes d'erreur

- 400 Bad Request - Requête incorrecte
- 404 Not Found - Ressource non trouvée
- 500 Internal Server Error - Erreur serveur interne

**Format d'erreur**

```json
{
  "error": true,
  "code": 404,
  "message": "Rule not found"
}
```

## Limites d'utilisation

Cette API est conçue pour une utilisation locale uniquement et ne dispose pas de limites de requêtes spécifiques.
