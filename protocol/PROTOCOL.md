# Remote Mouse & Keyboard - Protocol Documentation

## Vue d'ensemble
Ce document définit le protocole de communication WebSocket entre l'application Android (client) et le serveur Windows pour le contrôle à distance de la souris et du clavier.

## Structure de base des messages

Tous les messages échangés via WebSocket utilisent le format JSON avec la structure suivante :

```json
{
  "type": "string",      // Type du message
  "timestamp": "number", // Timestamp Unix en millisecondes
  "sessionId": "string", // ID de session pour l'authentification
  "data": {}            // Données spécifiques au type de message
}
```

## Types de messages

### 1. Authentification

#### AUTH_REQUEST (Client → Serveur)
```json
{
  "type": "AUTH_REQUEST",
  "timestamp": 1640995200000,
  "sessionId": null,
  "data": {
    "pin": "1234",
    "deviceName": "Samsung Galaxy S21",
    "deviceId": "unique_device_identifier"
  }
}
```

#### AUTH_RESPONSE (Serveur → Client)
```json
{
  "type": "AUTH_RESPONSE",
  "timestamp": 1640995200000,
  "sessionId": "session_12345",
  "data": {
    "success": true,
    "message": "Authentication successful",
    "serverInfo": {
      "name": "DESKTOP-ABC123",
      "version": "1.0.0"
    }
  }
}
```

### 2. Contrôle de la souris

#### MOUSE_MOVE (Client → Serveur)
```json
{
  "type": "MOUSE_MOVE",
  "timestamp": 1640995200000,
  "sessionId": "session_12345",
  "data": {
    "deltaX": 10.5,
    "deltaY": -5.2,
    "sensitivity": 1.0
  }
}
```

#### MOUSE_CLICK (Client → Serveur)
```json
{
  "type": "MOUSE_CLICK",
  "timestamp": 1640995200000,
  "sessionId": "session_12345",
  "data": {
    "button": "left", // "left", "right", "middle"
    "action": "down"  // "down", "up", "click", "double_click"
  }
}
```

#### MOUSE_SCROLL (Client → Serveur)
```json
{
  "type": "MOUSE_SCROLL",
  "timestamp": 1640995200000,
  "sessionId": "session_12345",
  "data": {
    "deltaX": 0,
    "deltaY": 120,
    "horizontal": false
  }
}
```

### 3. Contrôle du clavier

#### KEY_EVENT (Client → Serveur)
```json
{
  "type": "KEY_EVENT",
  "timestamp": 1640995200000,
  "sessionId": "session_12345",
  "data": {
    "key": "a",           // Caractère ou nom de la touche
    "keyCode": 65,        // Code Windows de la touche
    "action": "press",    // "down", "up", "press"
    "modifiers": {
      "ctrl": false,
      "alt": false,
      "shift": false,
      "win": false
    }
  }
}
```

#### TEXT_INPUT (Client → Serveur)
```json
{
  "type": "TEXT_INPUT",
  "timestamp": 1640995200000,
  "sessionId": "session_12345",
  "data": {
    "text": "Hello World!"
  }
}
```

### 4. Gestes avancés

#### GESTURE_EVENT (Client → Serveur)
```json
{
  "type": "GESTURE_EVENT",
  "timestamp": 1640995200000,
  "sessionId": "session_12345",
  "data": {
    "gestureType": "pinch", // "pinch", "rotate", "swipe"
    "state": "ongoing",      // "start", "ongoing", "end"
    "parameters": {
      "scale": 1.5,         // Pour pinch
      "rotation": 45,       // Pour rotate (degrés)
      "velocity": 200       // Pour swipe (px/s)
    }
  }
}
```

### 5. Messages de statut

#### HEARTBEAT (Bidirectionnel)
```json
{
  "type": "HEARTBEAT",
  "timestamp": 1640995200000,
  "sessionId": "session_12345",
  "data": {
    "status": "alive"
  }
}
```

#### ERROR (Serveur → Client)
```json
{
  "type": "ERROR",
  "timestamp": 1640995200000,
  "sessionId": "session_12345",
  "data": {
    "code": "INVALID_SESSION",
    "message": "Session expired or invalid",
    "fatal": true
  }
}
```

#### STATUS_UPDATE (Serveur → Client)
```json
{
  "type": "STATUS_UPDATE",
  "timestamp": 1640995200000,
  "sessionId": "session_12345",
  "data": {
    "serverStatus": "active",
    "connectedClients": 1,
    "settings": {
      "sensitivity": 1.0,
      "scrollSpeed": 1.0
    }
  }
}
```

### 6. Configuration

#### CONFIG_UPDATE (Client → Serveur)
```json
{
  "type": "CONFIG_UPDATE",
  "timestamp": 1640995200000,
  "sessionId": "session_12345",
  "data": {
    "sensitivity": 1.2,
    "scrollSpeed": 0.8,
    "tapToClick": true
  }
}
```

## Codes d'erreur

| Code | Description | Action recommandée |
|------|-------------|-------------------|
| `INVALID_PIN` | PIN incorrect | Redemander le PIN |
| `INVALID_SESSION` | Session expirée | Réauthentification |
| `RATE_LIMIT` | Trop de messages | Ralentir l'envoi |
| `SERVER_ERROR` | Erreur serveur interne | Réessayer plus tard |
| `UNSUPPORTED_MESSAGE` | Type de message non supporté | Vérifier la version |

## Sécurité

### Authentification
- Utilisation d'un PIN à 4-6 chiffres
- Session token généré après authentification réussie
- Expiration automatique des sessions après inactivité

### Validation
- Validation de tous les champs obligatoires
- Limite de fréquence des messages (rate limiting)
- Validation des valeurs numériques (deltaX, deltaY, etc.)

## Performance

### Optimisations recommandées
- Batching des événements de mouvement souris
- Compression des messages répétitifs
- Heartbeat toutes les 30 secondes
- Timeout de connexion : 10 secondes

### Limites
- Fréquence maximale : 60 messages/seconde
- Taille maximale d'un message : 1KB
- Nombre maximal de clients simultanés : 5

## Versions

### Version 1.0 (Actuelle)
- Support des fonctionnalités de base
- Authentification par PIN
- Contrôle souris et clavier standard

### Version 1.1 (Planifiée)
- Chiffrement des communications
- Support des gestes multi-touch avancés
- Synchronisation bidirectionnelle
