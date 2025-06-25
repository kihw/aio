package com.remotemouse.android.network

import android.util.Log
import com.remotemouse.android.models.*
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.*
import org.java_websocket.client.WebSocketClient
import org.java_websocket.drafts.Draft_6455
import org.java_websocket.handshake.ServerHandshake
import java.net.URI
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicReference
import javax.net.ssl.SSLSocketFactory

/**
 * Client WebSocket robuste avec reconnexion automatique pour Remote Mouse & Keyboard
 */
class RemoteMouseWebSocketClient(
    private val scope: CoroutineScope = CoroutineScope(Dispatchers.IO + SupervisorJob())
) {
    
    companion object {
        private const val TAG = "WebSocketClient"
        private const val RECONNECT_DELAY_MS = 2000L
        private const val MAX_RECONNECT_ATTEMPTS = 10
        private const val HEARTBEAT_INTERVAL_MS = 30000L
        private const val CONNECTION_TIMEOUT_MS = 10000L
    }
    
    // États de connexion
    enum class ConnectionState {
        DISCONNECTED,
        CONNECTING,
        CONNECTED,
        RECONNECTING,
        FAILED
    }
    
    // Flows pour observer l'état
    private val _connectionState = MutableStateFlow(ConnectionState.DISCONNECTED)
    val connectionState: StateFlow<ConnectionState> = _connectionState.asStateFlow()
    
    private val _incomingMessages = MutableSharedFlow<BaseMessage>()
    val incomingMessages: SharedFlow<BaseMessage> = _incomingMessages.asSharedFlow()
    
    private val _errors = MutableSharedFlow<String>()
    val errors: SharedFlow<String> = _errors.asSharedFlow()
    
    // Variables internes
    private val isConnected = AtomicBoolean(false)
    private val shouldReconnect = AtomicBoolean(false)
    private val reconnectAttempts = AtomicReference(0)
    private var webSocket: WebSocketClient? = null
    private var heartbeatJob: Job? = null
    private var reconnectJob: Job? = null
    
    private val messageSerializer = MessageSerializer()
    private val messageBuilder = MessageBuilder(messageSerializer)
    
    private var currentUri: URI? = null
    private var sessionId: String? = null
    
    /**
     * Se connecte au serveur WebSocket
     */
    fun connect(serverAddress: String, port: Int = 8080) {
        if (isConnected.get()) {
            Log.w(TAG, "Already connected or connecting")
            return
        }
        
        try {
            currentUri = URI("ws://$serverAddress:$port")
            shouldReconnect.set(true)
            reconnectAttempts.set(0)
            _connectionState.value = ConnectionState.CONNECTING
            
            performConnection()
        } catch (e: Exception) {
            Log.e(TAG, "Error creating URI: ${e.message}")
            _errors.tryEmit("Invalid server address: $serverAddress:$port")
            _connectionState.value = ConnectionState.FAILED
        }
    }
    
    /**
     * Se déconnecte du serveur
     */
    fun disconnect() {
        Log.i(TAG, "Disconnecting...")
        shouldReconnect.set(false)
        
        heartbeatJob?.cancel()
        reconnectJob?.cancel()
        
        webSocket?.close()
        webSocket = null
        
        isConnected.set(false)
        sessionId = null
        _connectionState.value = ConnectionState.DISCONNECTED
    }
    
    /**
     * Envoie un message au serveur
     */
    fun sendMessage(message: String): Boolean {
        return try {
            if (isConnected.get() && webSocket?.isOpen == true) {
                webSocket?.send(message)
                Log.d(TAG, "Message sent: ${message.take(100)}...")
                true
            } else {
                Log.w(TAG, "Cannot send message: not connected")
                false
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error sending message: ${e.message}")
            false
        }
    }
    
    /**
     * Envoie une demande d'authentification
     */
    fun authenticate(pin: String, deviceName: String, deviceId: String): Boolean {
        val authMessage = messageBuilder.authRequest(pin, deviceName, deviceId)
        return sendMessage(authMessage)
    }
    
    /**
     * Envoie un mouvement de souris
     */
    fun sendMouseMove(deltaX: Float, deltaY: Float, sensitivity: Float = 1.0f): Boolean {
        sessionId?.let { session ->
            val moveMessage = messageBuilder.mouseMove(session, deltaX, deltaY, sensitivity)
            return sendMessage(moveMessage)
        }
        return false
    }
    
    /**
     * Envoie un clic de souris
     */
    fun sendMouseClick(button: MouseButton, action: MouseAction): Boolean {
        sessionId?.let { session ->
            val clickMessage = messageBuilder.mouseClick(session, button, action)
            return sendMessage(clickMessage)
        }
        return false
    }
    
    /**
     * Envoie un scroll de souris
     */
    fun sendMouseScroll(deltaX: Float, deltaY: Float, horizontal: Boolean = false): Boolean {
        sessionId?.let { session ->
            val scrollMessage = messageBuilder.mouseScroll(session, deltaX, deltaY, horizontal)
            return sendMessage(scrollMessage)
        }
        return false
    }
    
    /**
     * Envoie un événement clavier
     */
    fun sendKeyEvent(key: String, keyCode: Int, action: KeyAction, modifiers: KeyModifiers): Boolean {
        sessionId?.let { session ->
            val keyMessage = messageBuilder.keyEvent(session, key, keyCode, action, modifiers)
            return sendMessage(keyMessage)
        }
        return false
    }
    
    /**
     * Envoie du texte
     */
    fun sendTextInput(text: String): Boolean {
        sessionId?.let { session ->
            val textMessage = messageBuilder.textInput(session, text)
            return sendMessage(textMessage)
        }
        return false
    }
    
    /**
     * Envoie un événement de geste
     */
    fun sendGestureEvent(gestureType: GestureType, state: GestureState, parameters: GestureParameters): Boolean {
        sessionId?.let { session ->
            val gestureMessage = messageBuilder.gestureEvent(session, gestureType, state, parameters)
            return sendMessage(gestureMessage)
        }
        return false
    }
    
    /**
     * Met à jour la configuration
     */
    fun updateConfig(sensitivity: Float?, scrollSpeed: Float?, tapToClick: Boolean?): Boolean {
        sessionId?.let { session ->
            val configMessage = messageBuilder.configUpdate(session, sensitivity, scrollSpeed, tapToClick)
            return sendMessage(configMessage)
        }
        return false
    }
    
    /**
     * Effectue la connexion WebSocket
     */
    private fun performConnection() {
        currentUri?.let { uri ->
            webSocket = object : WebSocketClient(uri, Draft_6455()) {
                override fun onOpen(handshake: ServerHandshake?) {
                    Log.i(TAG, "WebSocket connected")
                    isConnected.set(true)
                    reconnectAttempts.set(0)
                    _connectionState.value = ConnectionState.CONNECTED
                    startHeartbeat()
                }
                
                override fun onMessage(message: String?) {
                    message?.let { processIncomingMessage(it) }
                }
                
                override fun onClose(code: Int, reason: String?, remote: Boolean) {
                    Log.i(TAG, "WebSocket closed: $code - $reason (remote: $remote)")
                    isConnected.set(false)
                    heartbeatJob?.cancel()
                    
                    if (shouldReconnect.get()) {
                        _connectionState.value = ConnectionState.RECONNECTING
                        scheduleReconnection()
                    } else {
                        _connectionState.value = ConnectionState.DISCONNECTED
                    }
                }
                
                override fun onError(ex: Exception?) {
                    Log.e(TAG, "WebSocket error: ${ex?.message}")
                    ex?.message?.let { _errors.tryEmit(it) }
                }
            }
            
            // Configuration du timeout
            webSocket?.connectionLostTimeout = (CONNECTION_TIMEOUT_MS / 1000).toInt()
            
            // Connexion
            try {
                webSocket?.connect()
            } catch (e: Exception) {
                Log.e(TAG, "Error connecting: ${e.message}")
                _connectionState.value = ConnectionState.FAILED
                if (shouldReconnect.get()) {
                    scheduleReconnection()
                }
            }
        }
    }
    
    /**
     * Traite les messages entrants
     */
    private fun processIncomingMessage(messageJson: String) {
        try {
            Log.d(TAG, "Received message: ${messageJson.take(100)}...")
            
            messageSerializer.deserializeMessage(messageJson)?.let { message ->
                // Traitement spécial pour l'authentification
                if (message.type == MessageType.AUTH_RESPONSE) {
                    val authData = messageSerializer.deserializeData<AuthResponseData>(message.data)
                    if (authData?.success == true) {
                        sessionId = message.sessionId
                        Log.i(TAG, "Authentication successful, session ID: $sessionId")
                    } else {
                        Log.w(TAG, "Authentication failed: ${authData?.message}")
                        _errors.tryEmit("Authentication failed: ${authData?.message}")
                    }
                }
                
                // Émission du message pour les observateurs
                _incomingMessages.tryEmit(message)
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error processing message: ${e.message}")
        }
    }
    
    /**
     * Démarre le heartbeat
     */
    private fun startHeartbeat() {
        heartbeatJob?.cancel()
        heartbeatJob = scope.launch {
            while (isConnected.get() && currentCoroutineContext().isActive) {
                delay(HEARTBEAT_INTERVAL_MS)
                sessionId?.let { session ->
                    val heartbeatMessage = messageBuilder.heartbeat(session)
                    sendMessage(heartbeatMessage)
                }
            }
        }
    }
    
    /**
     * Programme une tentative de reconnexion
     */
    private fun scheduleReconnection() {
        if (!shouldReconnect.get()) return
        
        val attempts = reconnectAttempts.incrementAndGet()
        if (attempts > MAX_RECONNECT_ATTEMPTS) {
            Log.e(TAG, "Max reconnection attempts reached")
            _connectionState.value = ConnectionState.FAILED
            shouldReconnect.set(false)
            return
        }
        
        Log.i(TAG, "Scheduling reconnection attempt $attempts/$MAX_RECONNECT_ATTEMPTS")
        
        reconnectJob?.cancel()
        reconnectJob = scope.launch {
            delay(RECONNECT_DELAY_MS * attempts) // Délai croissant
            if (shouldReconnect.get()) {
                Log.i(TAG, "Attempting reconnection...")
                performConnection()
            }
        }
    }
    
    /**
     * Nettoie les ressources
     */
    fun cleanup() {
        disconnect()
        scope.cancel()
    }
    
    /**
     * Vérifie si le client est connecté
     */
    fun isConnected(): Boolean = isConnected.get()
    
    /**
     * Obtient l'ID de session actuel
     */
    fun getSessionId(): String? = sessionId
}
