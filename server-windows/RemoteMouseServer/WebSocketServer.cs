using System;
using System.Collections.Concurrent;
using System.Net;
using System.Net.WebSockets;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using RemoteMouseServer.Config;
using RemoteMouseServer.Models;
using RemoteMouseServer.Security;

namespace RemoteMouseServer
{
    /// <summary>
    /// Serveur WebSocket multi-client pour Remote Mouse & Keyboard
    /// Gère les connexions, l'authentification et le routage des messages
    /// </summary>
    public class WebSocketServer
    {
        private readonly ILogger<WebSocketServer> _logger;
        private readonly AppSettings _settings;
        private readonly AuthManager _authManager;
        private readonly InputController _inputController;
        
        private HttpListener? _httpListener;
        private CancellationTokenSource? _cancellationTokenSource;
        private readonly ConcurrentDictionary<string, ConnectedClient> _clients = new();
        private bool _isRunning;

        // Statistiques
        private long _totalConnections;
        private long _totalMessages;
        private DateTime _startTime;

        public WebSocketServer(
            ILogger<WebSocketServer> logger,
            IOptions<AppSettings> settings,
            AuthManager authManager,
            InputController inputController)
        {
            _logger = logger;
            _settings = settings.Value;
            _authManager = authManager;
            _inputController = inputController;
        }

        /// <summary>
        /// Démarre le serveur WebSocket
        /// </summary>
        public async Task StartAsync(int port, CancellationToken cancellationToken = default)
        {
            if (_isRunning)
            {
                _logger.LogWarning("Server is already running");
                return;
            }

            try
            {
                _cancellationTokenSource = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
                _httpListener = new HttpListener();
                
                var prefix = $"http://+:{port}/";
                _httpListener.Prefixes.Add(prefix);
                
                _logger.LogInformation("Starting WebSocket server on {Prefix}", prefix);
                
                _httpListener.Start();
                _isRunning = true;
                _startTime = DateTime.UtcNow;
                
                _logger.LogInformation("WebSocket server started successfully");

                // Démarrer l'acceptation des connexions
                _ = Task.Run(() => AcceptConnectionsAsync(_cancellationTokenSource.Token), 
                           _cancellationTokenSource.Token);

                // Démarrer le nettoyage périodique
                _ = Task.Run(() => CleanupClientsAsync(_cancellationTokenSource.Token), 
                           _cancellationTokenSource.Token);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Failed to start WebSocket server");
                await StopAsync();
                throw;
            }
        }

        /// <summary>
        /// Arrête le serveur WebSocket
        /// </summary>
        public async Task StopAsync()
        {
            if (!_isRunning)
                return;

            _logger.LogInformation("Stopping WebSocket server");
            _isRunning = false;

            try
            {
                // Annuler toutes les opérations
                _cancellationTokenSource?.Cancel();

                // Fermer toutes les connexions clients
                var disconnectTasks = new List<Task>();
                foreach (var client in _clients.Values)
                {
                    disconnectTasks.Add(DisconnectClientAsync(client, "Server shutdown"));
                }
                
                await Task.WhenAll(disconnectTasks);
                _clients.Clear();

                // Arrêter le listener HTTP
                _httpListener?.Stop();
                _httpListener?.Close();
                _httpListener = null;

                _cancellationTokenSource?.Dispose();
                _cancellationTokenSource = null;

                _logger.LogInformation("WebSocket server stopped");
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error while stopping WebSocket server");
            }
        }

        /// <summary>
        /// Accepte les nouvelles connexions WebSocket
        /// </summary>
        private async Task AcceptConnectionsAsync(CancellationToken cancellationToken)
        {
            while (!cancellationToken.IsCancellationRequested && _isRunning)
            {
                try
                {
                    var context = await _httpListener!.GetContextAsync();
                    
                    if (context.Request.IsWebSocketRequest)
                    {
                        // Traiter la connexion WebSocket en arrière-plan
                        _ = Task.Run(() => ProcessWebSocketConnectionAsync(context, cancellationToken), 
                                   cancellationToken);
                    }
                    else
                    {
                        // Rejeter les requêtes non-WebSocket
                        context.Response.StatusCode = 400;
                        context.Response.Close();
                    }
                }
                catch (ObjectDisposedException)
                {
                    // Listener fermé, c'est normal
                    break;
                }
                catch (Exception ex)
                {
                    _logger.LogError(ex, "Error accepting WebSocket connection");
                }
            }
        }

        /// <summary>
        /// Traite une connexion WebSocket
        /// </summary>
        private async Task ProcessWebSocketConnectionAsync(HttpListenerContext context, CancellationToken cancellationToken)
        {
            WebSocket? webSocket = null;
            ConnectedClient? client = null;
            
            try
            {
                // Accepter la connexion WebSocket
                var webSocketContext = await context.AcceptWebSocketAsync(null);
                webSocket = webSocketContext.WebSocket;
                
                var clientId = Guid.NewGuid().ToString();
                var remoteEndpoint = context.Request.RemoteEndPoint?.ToString() ?? "unknown";
                
                Interlocked.Increment(ref _totalConnections);
                
                _logger.LogInformation("New WebSocket connection from {RemoteEndpoint} (ID: {ClientId})", 
                                     remoteEndpoint, clientId);

                // Créer l'objet client
                client = new ConnectedClient
                {
                    Id = clientId,
                    WebSocket = webSocket,
                    RemoteEndpoint = remoteEndpoint,
                    ConnectedAt = DateTime.UtcNow,
                    LastActivity = DateTime.UtcNow,
                    IsAuthenticated = false
                };

                _clients.TryAdd(clientId, client);

                // Traiter les messages
                await ProcessClientMessagesAsync(client, cancellationToken);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error processing WebSocket connection");
            }
            finally
            {
                if (client != null)
                {
                    _clients.TryRemove(client.Id, out _);
                    await DisconnectClientAsync(client, "Connection closed");
                }
            }
        }

        /// <summary>
        /// Traite les messages d'un client
        /// </summary>
        private async Task ProcessClientMessagesAsync(ConnectedClient client, CancellationToken cancellationToken)
        {
            var buffer = new byte[4096];
            
            while (client.WebSocket.State == WebSocketState.Open && !cancellationToken.IsCancellationRequested)
            {
                try
                {
                    var result = await client.WebSocket.ReceiveAsync(
                        new ArraySegment<byte>(buffer), cancellationToken);

                    if (result.MessageType == WebSocketMessageType.Close)
                    {
                        _logger.LogInformation("Client {ClientId} requested to close connection", client.Id);
                        break;
                    }

                    if (result.MessageType == WebSocketMessageType.Text)
                    {
                        var messageText = Encoding.UTF8.GetString(buffer, 0, result.Count);
                        client.LastActivity = DateTime.UtcNow;
                        Interlocked.Increment(ref _totalMessages);

                        await ProcessMessageAsync(client, messageText);
                    }
                }
                catch (OperationCanceledException)
                {
                    break;
                }
                catch (WebSocketException ex)
                {
                    _logger.LogWarning(ex, "WebSocket error for client {ClientId}", client.Id);
                    break;
                }
                catch (Exception ex)
                {
                    _logger.LogError(ex, "Error processing message from client {ClientId}", client.Id);
                }
            }
        }

        /// <summary>
        /// Traite un message reçu d'un client
        /// </summary>
        private async Task ProcessMessageAsync(ConnectedClient client, string messageText)
        {
            try
            {
                _logger.LogDebug("Received message from {ClientId}: {Message}", 
                               client.Id, messageText.Substring(0, Math.Min(100, messageText.Length)));

                var baseMessage = JsonSerializer.Deserialize<BaseMessage>(messageText);
                if (baseMessage == null)
                {
                    await SendErrorAsync(client, "INVALID_MESSAGE", "Invalid message format");
                    return;
                }

                // Vérifier l'authentification pour tous les messages sauf AUTH_REQUEST
                if (baseMessage.Type != "AUTH_REQUEST" && !client.IsAuthenticated)
                {
                    await SendErrorAsync(client, "AUTHENTICATION_REQUIRED", "Authentication required");
                    return;
                }

                // Traiter selon le type de message
                switch (baseMessage.Type)
                {
                    case "AUTH_REQUEST":
                        await HandleAuthRequestAsync(client, baseMessage);
                        break;

                    case "MOUSE_MOVE":
                        await HandleMouseMoveAsync(client, baseMessage);
                        break;

                    case "MOUSE_CLICK":
                        await HandleMouseClickAsync(client, baseMessage);
                        break;

                    case "MOUSE_SCROLL":
                        await HandleMouseScrollAsync(client, baseMessage);
                        break;

                    case "KEY_EVENT":
                        await HandleKeyEventAsync(client, baseMessage);
                        break;

                    case "TEXT_INPUT":
                        await HandleTextInputAsync(client, baseMessage);
                        break;

                    case "GESTURE_EVENT":
                        await HandleGestureEventAsync(client, baseMessage);
                        break;

                    case "CONFIG_UPDATE":
                        await HandleConfigUpdateAsync(client, baseMessage);
                        break;

                    case "HEARTBEAT":
                        await HandleHeartbeatAsync(client, baseMessage);
                        break;

                    default:
                        await SendErrorAsync(client, "UNSUPPORTED_MESSAGE", $"Message type '{baseMessage.Type}' not supported");
                        break;
                }
            }
            catch (JsonException ex)
            {
                _logger.LogWarning(ex, "Invalid JSON from client {ClientId}", client.Id);
                await SendErrorAsync(client, "INVALID_JSON", "Invalid JSON format");
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error processing message from client {ClientId}", client.Id);
                await SendErrorAsync(client, "SERVER_ERROR", "Internal server error");
            }
        }

        /// <summary>
        /// Gère la demande d'authentification
        /// </summary>
        private async Task HandleAuthRequestAsync(ConnectedClient client, BaseMessage message)
        {
            try
            {
                var authData = JsonSerializer.Deserialize<AuthRequestData>(message.Data);
                if (authData == null)
                {
                    await SendErrorAsync(client, "INVALID_AUTH_DATA", "Invalid authentication data");
                    return;
                }

                var result = await _authManager.AuthenticateAsync(authData.Pin, authData.DeviceId);
                
                if (result.Success)
                {
                    client.IsAuthenticated = true;
                    client.SessionId = result.SessionId;
                    client.DeviceName = authData.DeviceName;
                    client.DeviceId = authData.DeviceId;

                    _logger.LogInformation("Client {ClientId} authenticated successfully as {DeviceName}", 
                                         client.Id, authData.DeviceName);

                    var response = new AuthResponseData
                    {
                        Success = true,
                        Message = "Authentication successful",
                        ServerInfo = new ServerInfo
                        {
                            Name = Environment.MachineName,
                            Version = "1.0.0"
                        }
                    };

                    await SendMessageAsync(client, "AUTH_RESPONSE", response, result.SessionId);
                }
                else
                {
                    _logger.LogWarning("Authentication failed for client {ClientId}: {Reason}", 
                                     client.Id, result.ErrorMessage);

                    var response = new AuthResponseData
                    {
                        Success = false,
                        Message = result.ErrorMessage ?? "Authentication failed"
                    };

                    await SendMessageAsync(client, "AUTH_RESPONSE", response);
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error handling auth request from client {ClientId}", client.Id);
                await SendErrorAsync(client, "AUTH_ERROR", "Authentication error");
            }
        }

        /// <summary>
        /// Gère les mouvements de souris
        /// </summary>
        private async Task HandleMouseMoveAsync(ConnectedClient client, BaseMessage message)
        {
            try
            {
                var moveData = JsonSerializer.Deserialize<MouseMoveData>(message.Data);
                if (moveData != null)
                {
                    await _inputController.MoveMouse(moveData.DeltaX, moveData.DeltaY, moveData.Sensitivity);
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error handling mouse move from client {ClientId}", client.Id);
            }
        }

        /// <summary>
        /// Gère les clics de souris
        /// </summary>
        private async Task HandleMouseClickAsync(ConnectedClient client, BaseMessage message)
        {
            try
            {
                var clickData = JsonSerializer.Deserialize<MouseClickData>(message.Data);
                if (clickData != null)
                {
                    await _inputController.ClickMouse(clickData.Button, clickData.Action);
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error handling mouse click from client {ClientId}", client.Id);
            }
        }

        /// <summary>
        /// Gère le scroll de souris
        /// </summary>
        private async Task HandleMouseScrollAsync(ConnectedClient client, BaseMessage message)
        {
            try
            {
                var scrollData = JsonSerializer.Deserialize<MouseScrollData>(message.Data);
                if (scrollData != null)
                {
                    await _inputController.ScrollMouse(scrollData.DeltaX, scrollData.DeltaY, scrollData.Horizontal);
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error handling mouse scroll from client {ClientId}", client.Id);
            }
        }

        /// <summary>
        /// Gère les événements clavier
        /// </summary>
        private async Task HandleKeyEventAsync(ConnectedClient client, BaseMessage message)
        {
            try
            {
                var keyData = JsonSerializer.Deserialize<KeyEventData>(message.Data);
                if (keyData != null)
                {
                    await _inputController.SendKey(keyData.Key, keyData.KeyCode, keyData.Action, keyData.Modifiers);
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error handling key event from client {ClientId}", client.Id);
            }
        }

        /// <summary>
        /// Gère la saisie de texte
        /// </summary>
        private async Task HandleTextInputAsync(ConnectedClient client, BaseMessage message)
        {
            try
            {
                var textData = JsonSerializer.Deserialize<TextInputData>(message.Data);
                if (textData != null && !string.IsNullOrEmpty(textData.Text))
                {
                    await _inputController.SendText(textData.Text);
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error handling text input from client {ClientId}", client.Id);
            }
        }

        /// <summary>
        /// Gère les événements de geste
        /// </summary>
        private async Task HandleGestureEventAsync(ConnectedClient client, BaseMessage message)
        {
            try
            {
                var gestureData = JsonSerializer.Deserialize<GestureEventData>(message.Data);
                if (gestureData != null)
                {
                    await _inputController.ProcessGesture(gestureData.GestureType, gestureData.State, gestureData.Parameters);
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error handling gesture event from client {ClientId}", client.Id);
            }
        }

        /// <summary>
        /// Gère les mises à jour de configuration
        /// </summary>
        private async Task HandleConfigUpdateAsync(ConnectedClient client, BaseMessage message)
        {
            try
            {
                var configData = JsonSerializer.Deserialize<ConfigUpdateData>(message.Data);
                if (configData != null)
                {
                    // Appliquer la configuration
                    if (configData.Sensitivity.HasValue)
                        _inputController.SetSensitivity(configData.Sensitivity.Value);
                    
                    if (configData.ScrollSpeed.HasValue)
                        _inputController.SetScrollSpeed(configData.ScrollSpeed.Value);

                    _logger.LogInformation("Configuration updated for client {ClientId}", client.Id);
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error handling config update from client {ClientId}", client.Id);
            }
        }

        /// <summary>
        /// Gère les heartbeats
        /// </summary>
        private async Task HandleHeartbeatAsync(ConnectedClient client, BaseMessage message)
        {
            // Répondre avec un heartbeat
            var heartbeatResponse = new HeartbeatData { Status = "alive" };
            await SendMessageAsync(client, "HEARTBEAT", heartbeatResponse, client.SessionId);
        }

        /// <summary>
        /// Envoie un message à un client
        /// </summary>
        private async Task SendMessageAsync<T>(ConnectedClient client, string messageType, T data, string? sessionId = null)
        {
            try
            {
                var message = new BaseMessage
                {
                    Type = messageType,
                    Timestamp = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds(),
                    SessionId = sessionId,
                    Data = JsonSerializer.Serialize(data)
                };

                var messageJson = JsonSerializer.Serialize(message);
                var messageBytes = Encoding.UTF8.GetBytes(messageJson);

                await client.WebSocket.SendAsync(
                    new ArraySegment<byte>(messageBytes),
                    WebSocketMessageType.Text,
                    true,
                    CancellationToken.None);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error sending message to client {ClientId}", client.Id);
            }
        }

        /// <summary>
        /// Envoie un message d'erreur à un client
        /// </summary>
        private async Task SendErrorAsync(ConnectedClient client, string errorCode, string errorMessage, bool fatal = false)
        {
            var errorData = new ErrorData
            {
                Code = errorCode,
                Message = errorMessage,
                Fatal = fatal
            };

            await SendMessageAsync(client, "ERROR", errorData, client.SessionId);
        }

        /// <summary>
        /// Déconnecte un client
        /// </summary>
        private async Task DisconnectClientAsync(ConnectedClient client, string reason)
        {
            try
            {
                _logger.LogInformation("Disconnecting client {ClientId}: {Reason}", client.Id, reason);

                if (client.WebSocket.State == WebSocketState.Open)
                {
                    await client.WebSocket.CloseAsync(
                        WebSocketCloseStatus.NormalClosure,
                        reason,
                        CancellationToken.None);
                }

                client.WebSocket.Dispose();
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error disconnecting client {ClientId}", client.Id);
            }
        }

        /// <summary>
        /// Nettoie périodiquement les clients inactifs
        /// </summary>
        private async Task CleanupClientsAsync(CancellationToken cancellationToken)
        {
            while (!cancellationToken.IsCancellationRequested)
            {
                try
                {
                    await Task.Delay(TimeSpan.FromMinutes(1), cancellationToken);

                    var now = DateTime.UtcNow;
                    var clientsToRemove = new List<ConnectedClient>();

                    foreach (var client in _clients.Values)
                    {
                        // Supprimer les clients inactifs ou déconnectés
                        if (client.WebSocket.State != WebSocketState.Open ||
                            now - client.LastActivity > TimeSpan.FromMinutes(_settings.ClientTimeoutMinutes))
                        {
                            clientsToRemove.Add(client);
                        }
                    }

                    foreach (var client in clientsToRemove)
                    {
                        _clients.TryRemove(client.Id, out _);
                        await DisconnectClientAsync(client, "Cleanup - inactive or disconnected");
                    }

                    if (clientsToRemove.Count > 0)
                    {
                        _logger.LogInformation("Cleaned up {Count} inactive clients", clientsToRemove.Count);
                    }
                }
                catch (OperationCanceledException)
                {
                    break;
                }
                catch (Exception ex)
                {
                    _logger.LogError(ex, "Error during client cleanup");
                }
            }
        }

        /// <summary>
        /// Obtient les statistiques du serveur
        /// </summary>
        public ServerStatistics GetStatistics()
        {
            return new ServerStatistics
            {
                IsRunning = _isRunning,
                ConnectedClients = _clients.Count,
                TotalConnections = _totalConnections,
                TotalMessages = _totalMessages,
                StartTime = _startTime,
                Uptime = _isRunning ? DateTime.UtcNow - _startTime : TimeSpan.Zero
            };
        }

        /// <summary>
        /// Obtient les clients connectés
        /// </summary>
        public IEnumerable<ConnectedClient> GetConnectedClients()
        {
            return _clients.Values.ToArray();
        }
    }

    /// <summary>
    /// Représente un client connecté
    /// </summary>
    public class ConnectedClient
    {
        public string Id { get; set; } = string.Empty;
        public WebSocket WebSocket { get; set; } = null!;
        public string RemoteEndpoint { get; set; } = string.Empty;
        public DateTime ConnectedAt { get; set; }
        public DateTime LastActivity { get; set; }
        public bool IsAuthenticated { get; set; }
        public string? SessionId { get; set; }
        public string? DeviceName { get; set; }
        public string? DeviceId { get; set; }
    }

    /// <summary>
    /// Statistiques du serveur
    /// </summary>
    public class ServerStatistics
    {
        public bool IsRunning { get; set; }
        public int ConnectedClients { get; set; }
        public long TotalConnections { get; set; }
        public long TotalMessages { get; set; }
        public DateTime StartTime { get; set; }
        public TimeSpan Uptime { get; set; }
    }
}
