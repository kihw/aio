package com.remotemouse.android.ui

import android.content.Intent
import android.os.Bundle
import android.view.Menu
import android.view.MenuItem
import android.widget.Toast
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import com.google.android.material.snackbar.Snackbar
import com.remotemouse.android.R
import com.remotemouse.android.databinding.ActivityMainBinding
import com.remotemouse.android.managers.ConnectionManager
import com.remotemouse.android.network.RemoteMouseWebSocketClient
import com.remotemouse.android.settings.SettingsActivity
import com.remotemouse.android.viewmodels.MainViewModel
import kotlinx.coroutines.launch

/**
 * Activité principale de l'application Remote Mouse & Keyboard
 * Contient le trackpad principal et les contrôles de base
 */
class MainActivity : AppCompatActivity() {
    
    private lateinit var binding: ActivityMainBinding
    private val viewModel: MainViewModel by viewModels()
    private lateinit var connectionManager: ConnectionManager
    
    private var trackpadView: TrackpadView? = null
    private var keyboardFragment: KeyboardFragment? = null
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        // Configuration de l'interface
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)
        
        // Configuration de la toolbar
        setSupportActionBar(binding.toolbar)
        supportActionBar?.title = getString(R.string.app_name)
        
        // Gestion des insets système
        ViewCompat.setOnApplyWindowInsetsListener(binding.root) { v, insets ->
            val systemBars = insets.getInsets(WindowInsetsCompat.Type.systemBars())
            v.setPadding(systemBars.left, systemBars.top, systemBars.right, systemBars.bottom)
            insets
        }
        
        // Initialisation des composants
        setupConnectionManager()
        setupTrackpadView()
        setupUI()
        observeViewModel()
    }
    
    /**
     * Configure le gestionnaire de connexion
     */
    private fun setupConnectionManager() {
        connectionManager = ConnectionManager(this)
    }
    
    /**
     * Configure la vue trackpad
     */
    private fun setupTrackpadView() {
        trackpadView = binding.trackpadView
        trackpadView?.setOnTrackpadListener(object : TrackpadView.OnTrackpadListener {
            override fun onMouseMove(deltaX: Float, deltaY: Float) {
                viewModel.sendMouseMove(deltaX, deltaY)
            }
            
            override fun onMouseClick(button: String, isDoubleClick: Boolean) {
                viewModel.sendMouseClick(button, isDoubleClick)
            }
            
            override fun onMouseScroll(deltaX: Float, deltaY: Float) {
                viewModel.sendMouseScroll(deltaX, deltaY)
            }
            
            override fun onGesture(gestureType: String, parameters: Map<String, Float>) {
                viewModel.sendGesture(gestureType, parameters)
            }
        })
    }
    
    /**
     * Configure l'interface utilisateur
     */
    private fun setupUI() {
        // Bouton de connexion
        binding.fabConnect.setOnClickListener {
            if (viewModel.isConnected.value == true) {
                viewModel.disconnect()
            } else {
                showConnectionDialog()
            }
        }
        
        // Boutons de contrôle
        binding.btnLeftClick.setOnClickListener {
            viewModel.sendMouseClick("left", false)
        }
        
        binding.btnRightClick.setOnClickListener {
            viewModel.sendMouseClick("right", false)
        }
        
        binding.btnMiddleClick.setOnClickListener {
            viewModel.sendMouseClick("middle", false)
        }
        
        // Bouton clavier
        binding.btnKeyboard.setOnClickListener {
            toggleKeyboard()
        }
        
        // Status text
        binding.tvConnectionStatus.text = getString(R.string.status_disconnected)
    }
    
    /**
     * Observe les changements du ViewModel
     */
    private fun observeViewModel() {
        // État de connexion
        lifecycleScope.launch {
            viewModel.connectionState.collect { state ->
                updateConnectionUI(state)
            }
        }
        
        // Statut de connexion
        lifecycleScope.launch {
            viewModel.isConnected.collect { isConnected ->
                updateConnectedUI(isConnected)
            }
        }
        
        // Messages d'erreur
        lifecycleScope.launch {
            viewModel.errorMessages.collect { error ->
                showError(error)
            }
        }
        
        // Messages de statut
        lifecycleScope.launch {
            viewModel.statusMessages.collect { status ->
                showStatus(status)
            }
        }
    }
    
    /**
     * Met à jour l'UI selon l'état de connexion
     */
    private fun updateConnectionUI(state: RemoteMouseWebSocketClient.ConnectionState) {
        val statusText = when (state) {
            RemoteMouseWebSocketClient.ConnectionState.DISCONNECTED -> 
                getString(R.string.status_disconnected)
            RemoteMouseWebSocketClient.ConnectionState.CONNECTING -> 
                getString(R.string.status_connecting)
            RemoteMouseWebSocketClient.ConnectionState.CONNECTED -> 
                getString(R.string.status_connected)
            RemoteMouseWebSocketClient.ConnectionState.RECONNECTING -> 
                getString(R.string.status_reconnecting)
            RemoteMouseWebSocketClient.ConnectionState.FAILED -> 
                getString(R.string.status_failed)
        }
        
        binding.tvConnectionStatus.text = statusText
        
        // Animation de l'indicateur de connexion
        val color = when (state) {
            RemoteMouseWebSocketClient.ConnectionState.CONNECTED -> 
                getColor(R.color.status_connected)
            RemoteMouseWebSocketClient.ConnectionState.CONNECTING,
            RemoteMouseWebSocketClient.ConnectionState.RECONNECTING -> 
                getColor(R.color.status_connecting)
            else -> getColor(R.color.status_disconnected)
        }
        
        binding.connectionIndicator.setBackgroundColor(color)
    }
    
    /**
     * Met à jour l'UI selon le statut de connexion
     */
    private fun updateConnectedUI(isConnected: Boolean) {
        // Icône du FAB
        val iconRes = if (isConnected) R.drawable.ic_disconnect else R.drawable.ic_connect
        binding.fabConnect.setImageResource(iconRes)
        
        // Activation des contrôles
        binding.trackpadView.isEnabled = isConnected
        binding.btnLeftClick.isEnabled = isConnected
        binding.btnRightClick.isEnabled = isConnected
        binding.btnMiddleClick.isEnabled = isConnected
        binding.btnKeyboard.isEnabled = isConnected
        
        // Opacité visuelle
        val alpha = if (isConnected) 1.0f else 0.5f
        binding.trackpadContainer.alpha = alpha
        binding.controlsContainer.alpha = alpha
    }
    
    /**
     * Affiche la boîte de dialogue de connexion
     */
    private fun showConnectionDialog() {
        ConnectionDialogFragment.newInstance { serverAddress, pin ->
            viewModel.connect(serverAddress, pin)
        }.show(supportFragmentManager, "connection_dialog")
    }
    
    /**
     * Affiche/masque le clavier virtuel
     */
    private fun toggleKeyboard() {
        if (keyboardFragment == null) {
            keyboardFragment = KeyboardFragment.newInstance()
            keyboardFragment?.show(supportFragmentManager, "keyboard_fragment")
        } else {
            keyboardFragment?.dismiss()
            keyboardFragment = null
        }
    }
    
    /**
     * Affiche un message d'erreur
     */
    private fun showError(message: String) {
        if (message.isNotEmpty()) {
            Snackbar.make(binding.root, message, Snackbar.LENGTH_LONG)
                .setAction(R.string.action_retry) {
                    viewModel.retryLastAction()
                }
                .show()
        }
    }
    
    /**
     * Affiche un message de statut
     */
    private fun showStatus(message: String) {
        if (message.isNotEmpty()) {
            Toast.makeText(this, message, Toast.LENGTH_SHORT).show()
        }
    }
    
    override fun onCreateOptionsMenu(menu: Menu): Boolean {
        menuInflater.inflate(R.menu.menu_main, menu)
        return true
    }
    
    override fun onOptionsItemSelected(item: MenuItem): Boolean {
        return when (item.itemId) {
            R.id.action_settings -> {
                startActivity(Intent(this, SettingsActivity::class.java))
                true
            }
            R.id.action_scan_devices -> {
                viewModel.scanForDevices()
                true
            }
            R.id.action_about -> {
                showAboutDialog()
                true
            }
            else -> super.onOptionsItemSelected(item)
        }
    }
    
    /**
     * Affiche la boîte de dialogue "À propos"
     */
    private fun showAboutDialog() {
        AboutDialogFragment().show(supportFragmentManager, "about_dialog")
    }
    
    override fun onResume() {
        super.onResume()
        // Réactiver les gestes du trackpad
        trackpadView?.onResume()
        
        // Rafraîchir l'état de connexion
        viewModel.refreshConnectionState()
    }
    
    override fun onPause() {
        super.onPause()
        // Suspendre les gestes du trackpad pour économiser la batterie
        trackpadView?.onPause()
    }
    
    override fun onDestroy() {
        super.onDestroy()
        // Nettoyer les ressources
        viewModel.cleanup()
        keyboardFragment = null
    }
    
    override fun onBackPressed() {
        // Si le clavier est ouvert, le fermer au lieu de quitter
        if (keyboardFragment != null) {
            toggleKeyboard()
        } else {
            super.onBackPressed()
        }
    }
    
    /**
     * Gestion des permissions runtime si nécessaire
     */
    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        connectionManager.onPermissionsResult(requestCode, permissions, grantResults)
    }
}
