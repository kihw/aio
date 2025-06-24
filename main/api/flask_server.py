"""
Flask Server - Serveur API Flask
------------------------------
Ce module fournit une API REST pour la communication avec le frontend.
Il expose les fonctionnalités d'AppFlow pour le contrôle et la surveillance à distance.
"""

import os
import json
import logging
import time
from typing import Dict, Any, List, Optional, Union
from flask import Flask, request, jsonify, g, abort, Response, Blueprint
from functools import wraps

logger = logging.getLogger(__name__)

def create_app(app_instance=None):
    """
    Crée l'application Flask avec les routes pour l'API AppFlow.
    
    Args:
        app_instance: Instance de l'application AppFlow
        
    Returns:
        Flask: Application Flask configurée
    """
    app = Flask("AppFlow API")
    
    # Configuration
    app.config['JSON_SORT_KEYS'] = False
    app.config['APPFLOW_INSTANCE'] = app_instance
    
    # Middlewares
    @app.before_request
    def before_request():
        # Stocker l'instance AppFlow dans g pour accès dans les routes
        g.appflow = app.config['APPFLOW_INSTANCE']
        
        # Vérifier si l'API est protégée
        if g.appflow and g.appflow.config.get('network', {}).get('require_auth', True):
            api_key = g.appflow.config.get('network', {}).get('api_key')
            if api_key:
                auth_header = request.headers.get('Authorization')
                if not auth_header or not auth_header.startswith('Bearer ') or auth_header[7:] != api_key:
                    abort(401, description='Unauthorized: Invalid API key')
    
    # Fonction d'aide pour vérifier si AppFlow est disponible
    def require_appflow(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not g.appflow:
                abort(503, description='AppFlow instance not available')
            return f(*args, **kwargs)
        return decorated
    
    # Routes pour l'API
    api = Blueprint('api', __name__)
    
    @api.route('/status', methods=['GET'])
    @require_appflow
    def status():
        return jsonify({
            'status': 'running' if g.appflow.running else 'stopped',
            'version': g.appflow.version,
            'uptime': time.time() - g.appflow.system_monitor.get_system_uptime() if g.appflow.system_monitor else 0
        })
    
    @api.route('/metrics', methods=['GET'])
    @require_appflow
    def metrics():
        if not g.appflow.system_monitor:
            abort(503, description='System monitor not available')
            
        return jsonify({
            'cpu': {
                'usage': g.appflow.system_monitor.get_cpu_usage(),
                'history': g.appflow.system_monitor.get_cpu_history()
            },
            'memory': g.appflow.system_monitor.get_memory_usage(),
            'battery': g.appflow.system_monitor.get_battery_info(),
            'network': g.appflow.system_monitor.get_network_info(),
            'disk': g.appflow.system_monitor.get_disk_info()
        })
    
    @api.route('/rules', methods=['GET'])
    @require_appflow
    def get_rules():
        if not g.appflow.rule_engine or not hasattr(g.appflow.rule_engine, 'rules'):
            abort(503, description='Rule engine not available')
            
        rules_dict = {}
        for rule_id, rule in g.appflow.rule_engine.rules.items():
            rules_dict[rule_id] = {
                'id': rule.id,
                'name': rule.name,
                'description': rule.description,
                'enabled': rule.enabled,
                'priority': rule.priority
            }
            
        return jsonify({
            'rules': rules_dict
        })
    
    @api.route('/rules/<rule_id>', methods=['GET'])
    @require_appflow
    def get_rule(rule_id):
        if not g.appflow.rule_engine:
            abort(503, description='Rule engine not available')
            
        rule = g.appflow.rule_engine.get_rule_by_id(rule_id)
        if not rule:
            abort(404, description=f'Rule {rule_id} not found')
            
        return jsonify({
            'id': rule.id,
            'name': rule.name,
            'description': rule.description,
            'enabled': rule.enabled,
            'priority': rule.priority,
            'conditions': [vars(cond) for cond in rule.conditions],
            'condition_logic': rule.condition_logic,
            'actions': rule.actions,
            'triggers': rule.triggers
        })
    
    @api.route('/rules/<rule_id>/toggle', methods=['POST'])
    @require_appflow
    def toggle_rule(rule_id):
        if not g.appflow.rule_engine:
            abort(503, description='Rule engine not available')
            
        rule = g.appflow.rule_engine.get_rule_by_id(rule_id)
        if not rule:
            abort(404, description=f'Rule {rule_id} not found')
            
        # Inverser l'état d'activation de la règle
        new_state = not rule.enabled
        
        if new_state:
            success = g.appflow.rule_engine.enable_rule(rule_id)
        else:
            success = g.appflow.rule_engine.disable_rule(rule_id)
            
        return jsonify({
            'success': success,
            'rule_id': rule_id,
            'enabled': new_state
        })
    
    @api.route('/engine/start', methods=['POST'])
    @require_appflow
    def start_engine():
        if g.appflow.running:
            return jsonify({'status': 'already_running'})
            
        success = g.appflow.start()
        return jsonify({
            'success': success,
            'status': 'running' if success else 'error'
        })
    
    @api.route('/engine/stop', methods=['POST'])
    @require_appflow
    def stop_engine():
        if not g.appflow.running:
            return jsonify({'status': 'already_stopped'})
            
        success = g.appflow.stop()
        return jsonify({
            'success': success,
            'status': 'stopped' if success else 'error'
        })
    
    @api.route('/processes', methods=['GET'])
    @require_appflow
    def get_processes():
        if not g.appflow.process_manager:
            abort(503, description='Process manager not available')
            
        processes = g.appflow.process_manager.get_running_processes()
        return jsonify({
            'processes': processes
        })
    
    @api.route('/processes/search', methods=['GET'])
    @require_appflow
    def search_processes():
        if not g.appflow.process_manager:
            abort(503, description='Process manager not available')
            
        name = request.args.get('name')
        if not name:
            abort(400, description='Name parameter required')
            
        processes = g.appflow.process_manager.find_processes_by_name(name)
        return jsonify({
            'processes': processes
        })
    
    @api.route('/processes/<int:pid>/kill', methods=['POST'])
    @require_appflow
    def kill_process(pid):
        if not g.appflow.process_manager:
            abort(503, description='Process manager not available')
            
        success = g.appflow.process_manager.kill_process_by_pid(pid)
        return jsonify({
            'success': success,
            'pid': pid
        })
    
    @api.route('/processes/launch', methods=['POST'])
    @require_appflow
    def launch_process():
        if not g.appflow.process_manager:
            abort(503, description='Process manager not available')
            
        data = request.json
        if not data or 'path' not in data:
            abort(400, description='Path required in JSON body')
            
        path = data['path']
        args = data.get('args', [])
        working_dir = data.get('working_dir')
        as_admin = data.get('as_admin', False)
        
        success = g.appflow.process_manager.launch_process(
            path=path,
            args=args,
            working_dir=working_dir,
            as_admin=as_admin
        )
        
        return jsonify({
            'success': success,
            'path': path
        })
    
    @api.route('/logs', methods=['GET'])
    @require_appflow
    def get_logs():
        # Paramètres de requête
        level = request.args.get('level', 'INFO')
        count = request.args.get('count')
        if count:
            try:
                count = int(count)
            except ValueError:
                abort(400, description='Count must be an integer')
                
        start_time = request.args.get('start')
        if start_time:
            try:
                start_time = float(start_time)
            except ValueError:
                abort(400, description='Start time must be a timestamp')
        
        log_level = getattr(logging, level.upper(), logging.INFO)
        
        # Vérifier si le logger AppFlow est configuré
        if hasattr(g.appflow, 'logger') and hasattr(g.appflow.logger, 'get_log_history'):
            logs = g.appflow.logger.get_log_history(
                level=log_level,
                count=count,
                start_time=start_time
            )
            return jsonify({'logs': logs})
        else:
            # Retourner juste un message si la capture de logs n'est pas disponible
            return jsonify({
                'logs': [],
                'message': 'Log history capture not enabled'
            })
    
    @api.route('/config', methods=['GET'])
    @require_appflow
    def get_config():
        # Retourner la configuration sans les informations sensibles
        config_copy = g.appflow.config.copy() if g.appflow.config else {}
        
        # Supprimer les informations sensibles
        if 'network' in config_copy and 'api_key' in config_copy['network']:
            config_copy['network']['api_key'] = '********'
            
        return jsonify(config_copy)
    
    @api.route('/rules_files', methods=['GET'])
    @require_appflow
    def list_rules_files():
        if not g.appflow.config_loader:
            abort(503, description='Config loader not available')
            
        files = g.appflow.config_loader.list_rules_files()
        return jsonify({'files': files})
    
    @api.route('/rules_files/<filename>', methods=['GET'])
    @require_appflow
    def get_rules_file(filename):
        if not g.appflow.config_loader:
            abort(503, description='Config loader not available')
        
        try:
            rules = g.appflow.config_loader.load_rules_file(filename)
            return jsonify(rules)
        except FileNotFoundError:
            abort(404, description=f'Rules file {filename} not found')
        except Exception as e:
            abort(500, description=f'Error loading rules file: {e}')
    
    @api.route('/evaluate_rules', methods=['POST'])
    @require_appflow
    def evaluate_rules():
        if not g.appflow.rule_engine:
            abort(503, description='Rule engine not available')
            
        matched_rules = g.appflow.rule_engine.evaluate_all_rules()
        
        # Convertir les objets Rule en dictionnaires
        matched_dicts = []
        for rule in matched_rules:
            matched_dicts.append({
                'id': rule.id,
                'name': rule.name,
                'priority': rule.priority
            })
            
        return jsonify({
            'matched_rules': matched_dicts,
            'count': len(matched_dicts)
        })
    
    # Gestion des erreurs
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            'error': 'bad_request',
            'message': error.description
        }), 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({
            'error': 'unauthorized',
            'message': error.description
        }), 401
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'error': 'not_found',
            'message': error.description
        }), 404
    
    @app.errorhandler(500)
    def server_error(error):
        return jsonify({
            'error': 'server_error',
            'message': error.description if hasattr(error, 'description') else str(error)
        }), 500
    
    @app.errorhandler(503)
    def service_unavailable(error):
        return jsonify({
            'error': 'service_unavailable',
            'message': error.description
        }), 503
    
    # Enregistrer le blueprint
    app.register_blueprint(api, url_prefix='/api')
    
    # Route racine
    @app.route('/')
    def index():
        return jsonify({
            'app': 'AppFlow API',
            'version': app.config['APPFLOW_INSTANCE'].version if app.config['APPFLOW_INSTANCE'] else '0.1.0',
            'endpoints': {
                'status': '/api/status',
                'metrics': '/api/metrics',
                'rules': '/api/rules',
                'processes': '/api/processes',
                'logs': '/api/logs',
                'config': '/api/config'
            }
        })
    
    return app


if __name__ == '__main__':
    # Pour tests autonomes
    logging.basicConfig(level=logging.INFO)
    app = create_app()
    app.run(debug=True, host='127.0.0.1', port=5000)
