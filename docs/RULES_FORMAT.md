# Format des règles YAML dans AppFlow

Ce document décrit la structure et la syntaxe des règles YAML utilisées par AppFlow pour automatiser la gestion des applications.

## Structure générale

Chaque fichier de règles YAML comprend:

1. Des métadonnées du fichier
2. Des paramètres globaux
3. Une liste de règles individuelles

Exemple de structure:

```yaml
version: '1.0'
description: 'Mon ensemble de règles AppFlow'
author: 'Nom'
last_modified: '2023-06-24'

# Paramètres globaux
global:
  restart_on_crash: true
  notification_level: 'info'

# Liste des règles
rules:
  - name: 'Règle 1'
    # détails de la règle...
  
  - name: 'Règle 2'
    # détails de la règle...
```

## Métadonnées du fichier

Ces informations sont facultatives mais recommandées pour la maintenance du fichier.

| Champ | Description | Type | Obligatoire |
|-------|-------------|------|-------------|
| version | Version du format de règles | string | Non |
| description | Description du fichier | string | Non |
| author | Auteur du fichier | string | Non |
| last_modified | Date de dernière modification | string (YYYY-MM-DD) | Non |

## Paramètres globaux

Les paramètres globaux affectent toutes les règles du fichier.

| Paramètre | Description | Type | Valeur par défaut |
|-----------|-------------|------|------------------|
| restart_on_crash | Redémarrer les applications qui se crashent | boolean | false |
| notification_level | Niveau de notification | string (none, error, warning, info, all) | 'info' |
| log_level | Niveau de journalisation | string (debug, info, warning, error, critical) | 'info' |

## Structure d'une règle

Chaque règle est définie comme un élément dans la liste `rules` et comprend:

1. Informations de base
2. Déclencheur (trigger)
3. Conditions (facultatives)
4. Actions

### Informations de base

| Champ | Description | Type | Obligatoire |
|-------|-------------|------|-------------|
| name | Nom de la règle | string | Oui |
| description | Description détaillée | string | Non |
| enabled | État d'activation | boolean | Oui |
| priority | Priorité d'exécution (plus petit = plus prioritaire) | integer (1-100) | Non (défaut: 50) |

### Déclencheurs (Triggers)

Le déclencheur définit quand une règle est évaluée. Chaque règle doit avoir exactement un type de déclencheur.

#### Types de déclencheurs

##### 1. Déclencheur temporel (time)

```yaml
trigger:
  type: 'time'
  schedule: '09:00'  # Format HH:MM
```

ou avec une syntaxe cron:

```yaml
trigger:
  type: 'time'
  cron: '0 9 * * 1-5'  # Format cron: minute heure jour_du_mois mois jour_de_la_semaine
```

##### 2. Déclencheur système (system)

```yaml
trigger:
  type: 'system'
  event: 'startup'  # ou 'shutdown', 'login', 'logout', 'idle', 'resume'
  delay: 30  # délai en secondes (facultatif)
```

##### 3. Déclencheur CPU

```yaml
trigger:
  type: 'cpu'
  level: 'above'  # ou 'below'
  threshold: 80  # pourcentage
  duration: 60  # durée en secondes pendant laquelle le seuil doit être dépassé
```

##### 4. Déclencheur mémoire

```yaml
trigger:
  type: 'memory'
  level: 'above'  # ou 'below'
  threshold: 90  # pourcentage
  duration: 60  # durée en secondes
```

##### 5. Déclencheur batterie

```yaml
trigger:
  type: 'battery'
  level: 'below'  # ou 'above'
  threshold: 20  # pourcentage
```

##### 6. Déclencheur réseau

```yaml
trigger:
  type: 'network'
  status: 'connected'  # ou 'disconnected'
  interface: 'wifi'  # facultatif, peut être 'wifi', 'ethernet', 'any'
```

##### 7. Déclencheur processus

```yaml
trigger:
  type: 'process'
  event: 'started'  # ou 'stopped'
  process: 'chrome.exe'  # nom du processus
```

### Conditions

Les conditions sont optionnelles et permettent d'affiner quand une règle doit être appliquée. Une règle est exécutée uniquement si toutes les conditions sont remplies.

#### Types de conditions

##### Plage horaire

```yaml
condition:
  time_range:
    start: '09:00'
    end: '17:00'
```

##### Jour de la semaine

```yaml
condition:
  weekday: [1, 2, 3, 4, 5]  # Lundi à Vendredi (0 = Dimanche, 6 = Samedi)
```

##### Niveau de batterie

```yaml
condition:
  battery_level:
    min: 20
    max: 80
  power_connected: false  # ou true
```

##### Inactivité utilisateur

```yaml
condition:
  user_idle: true
  idle_time: 15  # minutes minimum d'inactivité
```

##### Processus en cours

```yaml
condition:
  process_running: 'chrome.exe'  # ou liste: ['chrome.exe', 'firefox.exe']
```

##### Utilisation CPU/Mémoire

```yaml
condition:
  cpu_usage:
    min: 0
    max: 50
  memory_usage:
    min: 0
    max: 80
```

##### Combinaison de conditions

Toutes les conditions spécifiées doivent être satisfaites (logique ET):

```yaml
condition:
  weekday: [1, 2, 3, 4, 5]
  time_range:
    start: '09:00'
    end: '17:00'
  power_connected: true
```

### Actions

Les actions définissent ce qu'il faut faire lorsque le déclencheur est activé et que les conditions sont satisfaites.

#### Types d'actions

##### Lancement d'application

```yaml
actions:
  launch:
    app: 'chrome'
    args: ['--start-maximized', '--new-window', 'https://example.com']
    working_dir: 'C:\\Program Files\\Google\\Chrome\\Application'  # facultatif
```

##### Fermeture d'application

```yaml
actions:
  close:
    apps: ['chrome', 'spotify', 'discord']
    force: false  # true pour forcer la fermeture (équivalent kill)
```

##### Notification

```yaml
actions:
  notify:
    title: 'Titre de la notification'
    message: 'Message détaillé'
    level: 'info'  # peut être 'info', 'warning', 'error'
```

##### Attente

```yaml
actions:
  wait:
    duration: 30  # secondes
```

##### Ajustement de priorité

```yaml
actions:
  prioritize:
    target_apps: ['code', 'intellij']
    priority: 'high'  # peut être 'realtime', 'high', 'above_normal', 'normal', 'below_normal', 'low'
```

##### Actions multiples

Les actions sont exécutées dans l'ordre spécifié:

```yaml
actions:
  close:
    apps: ['chrome']
  wait:
    duration: 5
  launch:
    app: 'chrome'
    args: ['--incognito']
  notify:
    title: 'Chrome redémarré'
    message: 'Chrome a été redémarré en mode navigation privée'
```

## Exemples complets

### Exemple 1: Démarrage d'applications au login

```yaml
version: '1.0'
description: 'Règles de démarrage auto'

rules:
  - name: 'Démarrer applications de travail'
    description: 'Lance les applications de travail en semaine'
    enabled: true
    trigger:
      type: 'system'
      event: 'login'
      delay: 10
    condition:
      weekday: [1, 2, 3, 4, 5]
      time_range:
        start: '08:00'
        end: '10:00'
    actions:
      launch:
        app: 'outlook'
      wait:
        duration: 5
      launch:
        app: 'teams'
      notify:
        title: 'Applications de travail'
        message: 'Applications de travail démarrées'
        level: 'info'
```

### Exemple 2: Économie d'énergie sur batterie faible

```yaml
version: '1.0'
description: 'Règles de gestion de la batterie'

rules:
  - name: 'Économie batterie'
    description: 'Ferme les applications gourmandes quand la batterie est faible'
    enabled: true
    trigger:
      type: 'battery'
      level: 'below'
      threshold: 15
    condition:
      power_connected: false
    actions:
      close:
        apps: ['chrome', 'spotify', 'discord']
        force: false
      notify:
        title: 'Batterie faible'
        message: 'Applications fermées pour économiser la batterie'
        level: 'warning'
```

### Exemple 3: Gestion des ressources système

```yaml
version: '1.0'
description: 'Règles de gestion des ressources'

rules:
  - name: 'Gestion CPU élevé'
    description: 'Ajuste les priorités quand le CPU est surchargé'
    enabled: true
    trigger:
      type: 'cpu'
      level: 'above'
      threshold: 90
      duration: 30
    actions:
      prioritize:
        target_apps: ['code', 'intellij']
        priority: 'high'
      prioritize:
        target_apps: ['chrome', 'teams']
        priority: 'below_normal'
      notify:
        title: 'CPU surchargé'
        message: 'Priorités des applications ajustées'
        level: 'info'
```

## Validation

AppFlow vérifie automatiquement la validité des règles lors du chargement:

1. Syntax YAML correcte
2. Structure de règles conforme au schéma
3. Types de données valides
4. Cohérence des déclencheurs et actions

Les erreurs de validation sont enregistrées dans les logs et les règles invalides sont ignorées.
