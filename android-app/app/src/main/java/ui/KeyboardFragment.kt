package com.remotemouse.android.ui

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.view.WindowManager
import androidx.fragment.app.DialogFragment
import androidx.fragment.app.activityViewModels
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.GridLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.google.android.material.bottomsheet.BottomSheetDialogFragment
import com.remotemouse.android.R
import com.remotemouse.android.adapters.KeyboardAdapter
import com.remotemouse.android.databinding.FragmentKeyboardBinding
import com.remotemouse.android.models.*
import com.remotemouse.android.viewmodels.MainViewModel
import kotlinx.coroutines.launch

/**
 * Fragment pour le clavier virtuel avec touches spéciales
 * Affiche un clavier personnalisé pour l'envoi de touches et de texte
 */
class KeyboardFragment : BottomSheetDialogFragment() {
    
    companion object {
        private const val TAG = "KeyboardFragment"
        
        fun newInstance(): KeyboardFragment {
            return KeyboardFragment()
        }
    }
    
    private var _binding: FragmentKeyboardBinding? = null
    private val binding get() = _binding!!
    
    private val viewModel: MainViewModel by activityViewModels()
    private lateinit var keyboardAdapter: KeyboardAdapter
    
    private var currentKeyboardLayout = KeyboardLayout.ALPHABET
    private var isShiftPressed = false
    private var isCtrlPressed = false
    private var isAltPressed = false
    
    // Types de layout du clavier
    enum class KeyboardLayout {
        ALPHABET,
        NUMBERS,
        SYMBOLS,
        FUNCTION_KEYS,
        ARROW_KEYS
    }
    
    // Définition des touches
    data class KeyboardKey(
        val label: String,
        val keyCode: Int,
        val isSpecial: Boolean = false,
        val isModifier: Boolean = false,
        val action: KeyAction = KeyAction.PRESS,
        val width: Int = 1 // Largeur relative (1 = normale, 2 = double, etc.)
    )
    
    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View {
        _binding = FragmentKeyboardBinding.inflate(inflater, container, false)
        return binding.root
    }
    
    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        
        setupKeyboard()
        setupLayoutSwitchers()
        setupTextInput()
        observeViewModel()
        
        // Ajuster la taille du dialog
        dialog?.window?.setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE)
    }
    
    /**
     * Configure le clavier principal
     */
    private fun setupKeyboard() {
        keyboardAdapter = KeyboardAdapter { key ->
            handleKeyPress(key)
        }
        
        binding.recyclerKeyboard.apply {
            layoutManager = GridLayoutManager(context, 10) // 10 colonnes
            adapter = keyboardAdapter
        }
        
        updateKeyboardLayout()
    }
    
    /**
     * Configure les boutons de changement de layout
     */
    private fun setupLayoutSwitchers() {
        binding.btnAlphabet.setOnClickListener {
            switchLayout(KeyboardLayout.ALPHABET)
        }
        
        binding.btnNumbers.setOnClickListener {
            switchLayout(KeyboardLayout.NUMBERS)
        }
        
        binding.btnSymbols.setOnClickListener {
            switchLayout(KeyboardLayout.SYMBOLS)
        }
        
        binding.btnFunctionKeys.setOnClickListener {
            switchLayout(KeyboardLayout.FUNCTION_KEYS)
        }
        
        binding.btnArrowKeys.setOnClickListener {
            switchLayout(KeyboardLayout.ARROW_KEYS)
        }
        
        // Touches de modification
        binding.btnShift.setOnClickListener {
            toggleModifier("shift")
        }
        
        binding.btnCtrl.setOnClickListener {
            toggleModifier("ctrl")
        }
        
        binding.btnAlt.setOnClickListener {
            toggleModifier("alt")
        }
        
        binding.btnSpace.setOnClickListener {
            sendKey(" ", 32, KeyAction.PRESS)
        }
        
        binding.btnBackspace.setOnClickListener {
            sendKey("Backspace", 8, KeyAction.PRESS)
        }
        
        binding.btnEnter.setOnClickListener {
            sendKey("Enter", 13, KeyAction.PRESS)
        }
        
        binding.btnTab.setOnClickListener {
            sendKey("Tab", 9, KeyAction.PRESS)
        }
        
        binding.btnEscape.setOnClickListener {
            sendKey("Escape", 27, KeyAction.PRESS)
        }
    }
    
    /**
     * Configure la zone de saisie de texte
     */
    private fun setupTextInput() {
        binding.btnSendText.setOnClickListener {
            val text = binding.etTextInput.text.toString()
            if (text.isNotEmpty()) {
                viewModel.sendTextInput(text)
                binding.etTextInput.text?.clear()
            }
        }
        
        // Envoi automatique sur Enter
        binding.etTextInput.setOnEditorActionListener { _, _, _ ->
            binding.btnSendText.performClick()
            true
        }
    }
    
    /**
     * Observe les changements du ViewModel
     */
    private fun observeViewModel() {
        lifecycleScope.launch {
            viewModel.isConnected.collect { isConnected ->
                updateConnectionState(isConnected)
            }
        }
    }
    
    /**
     * Met à jour l'état selon la connexion
     */
    private fun updateConnectionState(isConnected: Boolean) {
        binding.recyclerKeyboard.isEnabled = isConnected
        binding.etTextInput.isEnabled = isConnected
        binding.btnSendText.isEnabled = isConnected
        
        // Opacité visuelle
        val alpha = if (isConnected) 1.0f else 0.5f
        binding.keyboardContainer.alpha = alpha
        binding.textInputContainer.alpha = alpha
        
        if (!isConnected) {
            binding.tvConnectionWarning.visibility = View.VISIBLE
            binding.tvConnectionWarning.text = getString(R.string.keyboard_not_connected)
        } else {
            binding.tvConnectionWarning.visibility = View.GONE
        }
    }
    
    /**
     * Change le layout du clavier
     */
    private fun switchLayout(layout: KeyboardLayout) {
        currentKeyboardLayout = layout
        updateKeyboardLayout()
        updateLayoutButtons()
    }
    
    /**
     * Met à jour le layout du clavier
     */
    private fun updateKeyboardLayout() {
        val keys = when (currentKeyboardLayout) {
            KeyboardLayout.ALPHABET -> createAlphabetKeys()
            KeyboardLayout.NUMBERS -> createNumberKeys()
            KeyboardLayout.SYMBOLS -> createSymbolKeys()
            KeyboardLayout.FUNCTION_KEYS -> createFunctionKeys()
            KeyboardLayout.ARROW_KEYS -> createArrowKeys()
        }
        
        keyboardAdapter.updateKeys(keys)
    }
    
    /**
     * Met à jour l'apparence des boutons de layout
     */
    private fun updateLayoutButtons() {
        // Réinitialiser tous les boutons
        listOf(binding.btnAlphabet, binding.btnNumbers, binding.btnSymbols, 
               binding.btnFunctionKeys, binding.btnArrowKeys).forEach {
            it.isSelected = false
        }
        
        // Activer le bouton correspondant
        when (currentKeyboardLayout) {
            KeyboardLayout.ALPHABET -> binding.btnAlphabet.isSelected = true
            KeyboardLayout.NUMBERS -> binding.btnNumbers.isSelected = true
            KeyboardLayout.SYMBOLS -> binding.btnSymbols.isSelected = true
            KeyboardLayout.FUNCTION_KEYS -> binding.btnFunctionKeys.isSelected = true
            KeyboardLayout.ARROW_KEYS -> binding.btnArrowKeys.isSelected = true
        }
    }
    
    /**
     * Crée les touches alphabétiques
     */
    private fun createAlphabetKeys(): List<KeyboardKey> {
        val keys = mutableListOf<KeyboardKey>()
        
        // Première rangée
        "qwertyuiop".forEach { char ->
            val label = if (isShiftPressed) char.uppercase() else char.toString()
            keys.add(KeyboardKey(label, char.code))
        }
        
        // Deuxième rangée
        "asdfghjkl".forEach { char ->
            val label = if (isShiftPressed) char.uppercase() else char.toString()
            keys.add(KeyboardKey(label, char.code))
        }
        
        // Troisième rangée
        "zxcvbnm".forEach { char ->
            val label = if (isShiftPressed) char.uppercase() else char.toString()
            keys.add(KeyboardKey(label, char.code))
        }
        
        return keys
    }
    
    /**
     * Crée les touches numériques
     */
    private fun createNumberKeys(): List<KeyboardKey> {
        val keys = mutableListOf<KeyboardKey>()
        
        // Première rangée - chiffres avec symboles (si Shift)
        val numberRow = if (isShiftPressed) {
            listOf("!" to 33, "@" to 64, "#" to 35, "$" to 36, "%" to 37,
                   "^" to 94, "&" to 38, "*" to 42, "(" to 40, ")" to 41)
        } else {
            listOf("1" to 49, "2" to 50, "3" to 51, "4" to 52, "5" to 53,
                   "6" to 54, "7" to 55, "8" to 56, "9" to 57, "0" to 48)
        }
        
        numberRow.forEach { (label, code) ->
            keys.add(KeyboardKey(label, code))
        }
        
        return keys
    }
    
    /**
     * Crée les touches de symboles
     */
    private fun createSymbolKeys(): List<KeyboardKey> {
        val symbols = listOf(
            "." to 46, "," to 44, "?" to 63, "!" to 33, "'" to 39, "\"" to 34,
            "-" to 45, "+" to 43, "=" to 61, "_" to 95, ":" to 58, ";" to 59,
            "/" to 47, "\\" to 92, "|" to 124, "[" to 91, "]" to 93, "{" to 123,
            "}" to 125, "<" to 60, ">" to 62, "~" to 126, "`" to 96, "@" to 64
        )
        
        return symbols.map { (label, code) ->
            KeyboardKey(label, code)
        }
    }
    
    /**
     * Crée les touches de fonction
     */
    private fun createFunctionKeys(): List<KeyboardKey> {
        val functionKeys = mutableListOf<KeyboardKey>()
        
        // F1-F12
        for (i in 1..12) {
            functionKeys.add(KeyboardKey("F$i", 112 + i - 1, isSpecial = true))
        }
        
        // Touches spéciales
        functionKeys.addAll(listOf(
            KeyboardKey("Insert", 45, isSpecial = true),
            KeyboardKey("Delete", 46, isSpecial = true),
            KeyboardKey("Home", 36, isSpecial = true),
            KeyboardKey("End", 35, isSpecial = true),
            KeyboardKey("PgUp", 33, isSpecial = true),
            KeyboardKey("PgDn", 34, isSpecial = true)
        ))
        
        return functionKeys
    }
    
    /**
     * Crée les touches de direction
     */
    private fun createArrowKeys(): List<KeyboardKey> {
        return listOf(
            KeyboardKey("↑", 38, isSpecial = true),
            KeyboardKey("←", 37, isSpecial = true),
            KeyboardKey("↓", 40, isSpecial = true),
            KeyboardKey("→", 39, isSpecial = true)
        )
    }
    
    /**
     * Gère l'appui sur une touche
     */
    private fun handleKeyPress(key: KeyboardKey) {
        sendKey(key.label, key.keyCode, key.action)
        
        // Désactiver Shift après usage (sauf si verrouillé)
        if (!key.isModifier && isShiftPressed) {
            toggleModifier("shift")
        }
    }
    
    /**
     * Bascule un modificateur
     */
    private fun toggleModifier(modifier: String) {
        when (modifier) {
            "shift" -> {
                isShiftPressed = !isShiftPressed
                binding.btnShift.isSelected = isShiftPressed
                updateKeyboardLayout() // Mettre à jour les labels
            }
            "ctrl" -> {
                isCtrlPressed = !isCtrlPressed
                binding.btnCtrl.isSelected = isCtrlPressed
            }
            "alt" -> {
                isAltPressed = !isAltPressed
                binding.btnAlt.isSelected = isAltPressed
            }
        }
    }
    
    /**
     * Envoie une touche avec les modificateurs actuels
     */
    private fun sendKey(key: String, keyCode: Int, action: KeyAction) {
        val modifiers = KeyModifiers(
            ctrl = isCtrlPressed,
            alt = isAltPressed,
            shift = isShiftPressed,
            win = false
        )
        
        viewModel.sendKeyEvent(key, keyCode, action, modifiers)
        
        // Feedback tactile
        view?.performHapticFeedback(HapticFeedbackConstants.KEYBOARD_TAP)
    }
    
    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
    
    override fun onStart() {
        super.onStart()
        // Ajuster la hauteur du dialog pour qu'il prenne environ 40% de l'écran
        dialog?.window?.setLayout(
            ViewGroup.LayoutParams.MATCH_PARENT,
            (resources.displayMetrics.heightPixels * 0.4).toInt()
        )
    }
}
