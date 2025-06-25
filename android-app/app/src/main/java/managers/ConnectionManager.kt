package com.remotemouse.android.managers

import android.content.Context
import android.content.SharedPreferences
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import android.net.wifi.WifiManager
import android.util.Log
import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import com.remotemouse.android.models.*
import com.remotemouse.android.network.RemoteMouseWebSocketClient
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.*
import java.net.InetAddress
import java.net.NetworkInterface
import java.util.*
import javax.jmdns.JmDNS
import javax.jmdns.ServiceEvent
import javax.jmdns.ServiceListener

/**
 * Gestionnaire de connexions et découverte réseau pour Remote Mouse & Keyboard
 * Gère la découverte automatique des serveurs et la gestion des connexions
 */
class ConnectionManager(
    private val context: Context,
    private val scope: CoroutineScope = CoroutineScope(Dispatchers.IO + SupervisorJob())
) {
    
    companion object {
        private const val TAG = "ConnectionManager"
        private const val SERVICE_TYPE = "_remotemouse._tcp.local."
        private const val PREFS_NAME = "remote_mouse_connections"
        private const val KEY_LAST_SERVER = "last_server_address"
        private const val KEY_LAST_PIN = "last_pin"
        private const val KEY_DEVICE_ID = "device_id"
        private const val DISCOVERY_TIMEOUT_MS = 10000L
        private const val CONNECTION_RETRY_DELAY_MS = 2000L
        private const val MAX_CONNECTION_RETRIES = 3
    }
    
    // Modèle pour un serveur découvert
    data class DiscoveredServer(
        val name: String,
        val address: String,
        val port: Int,
        val isSecure: Boolean = false,
        val lastSeen: Long = System.currentTimeMillis(),
        val rssi: Int = 0 // Force du signal si disponible
    )
    
    // États de connexion
    enum class ConnectionStatus {
        DISCONNECTED,
        DISCOVERING,
        CONNECTING,
        CONNECTED,
        RECONNECTING,
        FAILED
    }
    
    // Variables d'état
    private val _connectionStatus = MutableStateFlow(ConnectionStatus.DISCONNECTED)
    val connectionStatus: StateFlow<ConnectionStatus> = _connectionStatus.asStateFlow()
    
    private val _discoveredServers = MutableStateFlow<List<DiscoveredServer>>(emptyList())
    val discoveredServers: StateFlow<List<DiscoveredServer>> = _discoveredServers.asStateFlow()
    
    private val _currentServer = MutableStateFlow<DiscoveredServer?>(null)
    val currentServer: StateFlow<DiscoveredServer?> = _currentServer.asStateFlow()
    
    private val _connectionError = MutableSharedFlow<String>()
    val connectionError: SharedFlow<String> = _connectionError.asSharedFlow()
    
    // Gestionnaires réseau
    private val connectivityManager = context.getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
    private val wifiManager = context.applicationContext.getSystemService(Context.WIFI_SERVICE) as WifiManager
    private val preferences: SharedPreferences = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
    
    // Client WebSocket
    private var webSocketClient: RemoteMouseWebSocketClient? = null
    
    // Découverte mDNS
    private var jmdns: JmDNS? = null
    private var discoveryJob: Job? = null
    private var connectionRetryJob: Job? = null
    
    // Variables de configuration
    private var deviceId: String = getOrCreateDeviceId()
    private var currentPin: String? = null
    private var autoReconnect: Boolean = true
    
    init {
        setupNetworkCallback()
        loadSavedConnection()
    }
    
    /**
     * Configure la surveillance des changements réseau
     */
    private fun setupNetworkCallback() {
        val networkCallback = object : ConnectivityManager.NetworkCallback() {
            override fun onAvailable(network: Network) {
                Log.i(TAG, "Network available")
                if (autoReconnect && _connectionStatus.value == ConnectionStatus.FAILED) {
                    reconnectToLastServer()
                }
            }
            
            override fun onLost(network: Network) {
                Log.i(TAG, "Network lost")
                if (_connectionStatus.value == ConnectionStatus.CONNECTED) {
                    _connectionStatus.value = ConnectionStatus.RECONNECTING
                }
            }
        }
        
        connectivityManager.registerDefaultNetworkCallback(networkCallback)
    }
    
    /**
     * Charge la dernière connexion sauvegardée
     */
    private fun loadSavedConnection() {
        val lastServer = preferences.getString(KEY_LAST_SERVER, null)
        val lastPin = preferences.getString(KEY_LAST_PIN, null)
        
        if (lastServer != null && lastPin != null) {
            currentPin = lastPin
            // Optionnel : essayer de se reconnecter automatiquement
        }
    }
    
    /**
     * Génère ou récupère l'ID unique de l'appareil
     */
    private fun getOrCreateDeviceId(): String {
        var id = preferences.getString(KEY_DEVICE_ID, null)
        if (id == null) {
            id = UUID.randomUUID().toString()
            preferences.edit().putString(KEY_DEVICE_ID, id).apply()
        }
        return id
    }
    
    /**
     * Démarre la découverte des serveurs
     */
    fun startDiscovery() {
        if (_connectionStatus.value == ConnectionStatus.DISCOVERING) {
            Log.w(TAG, "Discovery already in progress")
            return
        }
        
        Log.i(TAG, "Starting server discovery")
        _connectionStatus.value = ConnectionStatus.DISCOVERING
        _discoveredServers.value = emptyList()
        
        discoveryJob?.cancel()
        discoveryJob = scope.launch {
            try {
                setupMDNSDiscovery()
                
                // Timeout pour la découverte
                delay(DISCOVERY_TIMEOUT_MS)
                stopDiscovery()
                
            } catch (e: Exception) {
                Log.e(TAG, "Discovery error: ${e.message}")
                _connectionError.tryEmit("Discovery failed: ${e.message}")
                _connectionStatus.value = ConnectionStatus.DISCONNECTED
            }
        }
    }
    
    /**
     * Configure la découverte mDNS
     */
    private suspend fun setupMDNSDiscovery() = withContext(Dispatchers.IO) {
        try {
            val wifiLock = wifiManager.createMulticastLock("RemoteMouseDiscovery")
            wifiLock.acquire()
            
            val localAddress = getLocalInetAddress()
            if (localAddress != null) {
                jmdns = JmDNS.create(localAddress)
                
                val serviceListener = object : ServiceListener {
                    override fun serviceAdded(event: ServiceEvent) {
                        Log.d(TAG, "Service added: ${event.info}")
                        jmdns?.requestServiceInfo(event.type, event.name)
                    }
                    
                    override fun serviceRemoved(event: ServiceEvent) {
                        Log.d(TAG, "Service removed: ${event.info}")
                        removeDiscoveredServer(event.info.server)
                    }
                    
                    override fun serviceResolved(event: ServiceEvent) {
                        Log.d(TAG, "Service resolved: ${event.info}")
                        val info = event.info
                        
                        if (info.inet4Addresses.isNotEmpty()) {
                            val server = DiscoveredServer(
                                name = info.name,
                                address = info.inet4Addresses[0].hostAddress ?: "",
                                port = info.port,
                                isSecure = info.getPropertyString("secure") == "true"
                            )
                            
                            addDiscoveredServer(server)
                        }
                    }
                }
                
                jmdns?.addServiceListener(SERVICE_TYPE, serviceListener)
                
            } else {
                throw Exception("No network interface available")
            }
            
        } catch (e: Exception) {
            Log.e(TAG, "mDNS setup failed: ${e.message}")
            throw e
        }
    }
    
    /**
     * Obtient l'adresse IP locale
     */
    private fun getLocalInetAddress(): InetAddress? {
        try {
            val networkInterfaces = NetworkInterface.getNetworkInterfaces()
            while (networkInterfaces.hasMoreElements()) {
                val networkInterface = networkInterfaces.nextElement()
                
                if (!networkInterface.isLoopback && networkInterface.isUp) {
                    val addresses = networkInterface.inetAddresses
                    while (addresses.hasMoreElements()) {
                        val address = addresses.nextElement()
                        if (!address.isLoopbackAddress && address.isSiteLocalAddress) {
                            return address
                        }
                    }
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to get local address: ${e.message}")
        }
        return null
    }
    
    /**
     * Ajoute un serveur découvert
     */
    private fun addDiscoveredServer(server: DiscoveredServer) {
        val currentList = _discoveredServers.value.toMutableList()
        
        // Éviter les doublons
        val existingIndex = currentList.indexOfFirst { it.address == server.address && it.port == server.port }
        if (existingIndex >= 0) {
            currentList[existingIndex] = server
        } else {
            currentList.add(server)
        }
        
        // Trier par force du signal / dernière vue
        currentList.sortByDescending { it.lastSeen }
        
        _discoveredServers.value = currentList
        Log.i(TAG, "Server discovered: ${server.name} at ${server.address}:${server.port}")
    }
    
    /**
     * Supprime un serveur découvert
     */
    private fun removeDiscoveredServer(serverName: String) {
        val currentList = _discoveredServers.value.toMutableList()
        currentList.removeAll { it.name == serverName }
        _discoveredServers.value = currentList
    }
    
    /**
     * Arrête la découverte
     */
    fun stopDiscovery() {
        Log.i(TAG, "Stopping discovery")
        discoveryJob?.cancel()
        
        try {
            jmdns?.removeAllServiceListeners()
            jmdns?.close()
            jmdns = null
        } catch (e: Exception) {
            Log.e(TAG, "Error stopping mDNS: ${e.message}")
        }
        
        if (_connectionStatus.value == ConnectionStatus.DISCOVERING) {
            _connectionStatus.value = ConnectionStatus.DISCONNECTED
        }
    }
    
    /**
     * Se connecte à un serveur spécifique
     */
    fun connectToServer(server: DiscoveredServer, pin: String) {
        if (_connectionStatus.value == ConnectionStatus.CONNECTING || 
            _connectionStatus.value == ConnectionStatus.CONNECTED) {
            Log.w(TAG, "Already connecting or connected")
            return
        }
        
        Log.i(TAG, "Connecting to server: ${server.name} at ${server.address}:${server.port}")
        
        _connectionStatus.value = ConnectionStatus.CONNECTING
        _currentServer.value = server
        currentPin = pin
        
        // Sauvegarder pour reconnexion automatique
        preferences.edit()
            .putString(KEY_LAST_SERVER, "${server.address}:${server.port}")
            .putString(KEY_LAST_PIN, pin)
            .apply()
        
        performConnection(server, pin)
    }
    
    /**
     * Se connecte à un serveur par adresse
     */
    fun connectToAddress(address: String, port: Int = 8080, pin: String) {
        val server = DiscoveredServer(
            name = "Manual Connection",
            address = address,
            port = port
        )
        connectToServer(server, pin)
    }
    
    /**
     * Effectue la connexion réelle
     */
    private fun performConnection(server: DiscoveredServer, pin: String) {
        scope.launch {
            try {
                // Nettoyer l'ancienne connexion
                webSocketClient?.cleanup()
                
                // Créer un nouveau client
                webSocketClient = RemoteMouseWebSocketClient(scope)
                
                // Observer les états de connexion
                webSocketClient?.connectionState?.collect { state ->
                    handleWebSocketState(state)
                }
                
                // Se connecter
                webSocketClient?.connect(server.address, server.port)
                
                // Attendre un moment puis s'authentifier
                delay(1000)
                
                val deviceName = android.os.Build.MODEL
                webSocketClient?.authenticate(pin, deviceName, deviceId)
                
            } catch (e: Exception) {
                Log.e(TAG, "Connection failed: ${e.message}")
                _connectionError.tryEmit("Connection failed: ${e.message}")
                _connectionStatus.value = ConnectionStatus.FAILED
            }
        }
    }
    
    /**
     * Gère les changements d'état du WebSocket
     */
    private fun handleWebSocketState(state: RemoteMouseWebSocketClient.ConnectionState) {
        val newStatus = when (state) {
            RemoteMouseWebSocketClient.ConnectionState.CONNECTING -> ConnectionStatus.CONNECTING
            RemoteMouseWebSocketClient.ConnectionState.CONNECTED -> ConnectionStatus.CONNECTED
            RemoteMouseWebSocketClient.ConnectionState.RECONNECTING -> ConnectionStatus.RECONNECTING
            RemoteMouseWebSocketClient.ConnectionState.DISCONNECTED -> ConnectionStatus.DISCONNECTED
            RemoteMouseWebSocketClient.ConnectionState.FAILED -> ConnectionStatus.FAILED
        }
        
        _connectionStatus.value = newStatus
        
        // Gestion de la reconnexion automatique
        if (state == RemoteMouseWebSocketClient.ConnectionState.FAILED && autoReconnect) {
            scheduleReconnection()
        }
    }
    
    /**
     * Programme une tentative de reconnexion
     */
    private fun scheduleReconnection() {
        connectionRetryJob?.cancel()
        connectionRetryJob = scope.launch {
            repeat(MAX_CONNECTION_RETRIES) { attempt ->
                Log.i(TAG, "Reconnection attempt ${attempt + 1}/$MAX_CONNECTION_RETRIES")
                delay(CONNECTION_RETRY_DELAY_MS * (attempt + 1))
                
                _currentServer.value?.let { server ->
                    currentPin?.let { pin ->
                        performConnection(server, pin)
                        
                        // Attendre le résultat
                        delay(5000)
                        if (_connectionStatus.value == ConnectionStatus.CONNECTED) {
                            return@launch // Succès
                        }
                    }
                }
            }
            
            Log.w(TAG, "Max reconnection attempts reached")
            _connectionError.tryEmit("Failed to reconnect after $MAX_CONNECTION_RETRIES attempts")
        }
    }
    
    /**
     * Reconnecte au dernier serveur
     */
    private fun reconnectToLastServer() {
        val lastServer = preferences.getString(KEY_LAST_SERVER, null)
        val lastPin = preferences.getString(KEY_LAST_PIN, null)
        
        if (lastServer != null && lastPin != null) {
            val parts = lastServer.split(":")
            if (parts.size == 2) {
                val address = parts[0]
                val port = parts[1].toIntOrNull() ?: 8080
                connectToAddress(address, port, lastPin)
            }
        }
    }
    
    /**
     * Se déconnecte du serveur actuel
     */
    fun disconnect() {
        Log.i(TAG, "Disconnecting from server")
        autoReconnect = false
        connectionRetryJob?.cancel()
        
        webSocketClient?.disconnect()
        _connectionStatus.value = ConnectionStatus.DISCONNECTED
        _currentServer.value = null
    }
    
    /**
     * Obtient le client WebSocket actuel
     */
    fun getWebSocketClient(): RemoteMouseWebSocketClient? = webSocketClient
    
    /**
     * Configure la reconnexion automatique
     */
    fun setAutoReconnect(enabled: Boolean) {
        autoReconnect = enabled
    }
    
    /**
     * Vérifie si connecté
     */
    fun isConnected(): Boolean = _connectionStatus.value == ConnectionStatus.CONNECTED
    
    /**
     * Gestion des permissions (pour la découverte réseau)
     */
    fun onPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        // Traiter les résultats des permissions si nécessaire
        // (pour l'accès au WiFi et à la localisation sur Android 6+)
    }
    
    /**
     * Nettoie les ressources
     */
    fun cleanup() {
        Log.i(TAG, "Cleaning up ConnectionManager")
        disconnect()
        stopDiscovery()
        webSocketClient?.cleanup()
        scope.cancel()
    }
}
