package com.remotemouse.android.ui

import android.content.Context
import android.graphics.*
import android.util.AttributeSet
import android.view.*
import android.view.GestureDetector
import android.view.ScaleGestureDetector
import androidx.core.content.ContextCompat
import com.remotemouse.android.R
import com.remotemouse.android.utils.GestureProcessor
import kotlin.math.*

/**
 * Vue personnalisée pour le trackpad avec support des gestes multi-touch
 * Simule un trackpad d'ordinateur portable avec gestes avancés
 */
class TrackpadView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
    defStyleAttr: Int = 0
) : View(context, attrs, defStyleAttr) {
    
    companion object {
        private const val TAG = "TrackpadView"
        private const val MOVEMENT_THRESHOLD = 2.0f
        private const val DOUBLE_TAP_TIMEOUT = 300L
        private const val LONG_PRESS_TIMEOUT = 500L
        private const val SCROLL_SENSITIVITY = 0.5f
        private const val PINCH_THRESHOLD = 0.1f
        private const val ROTATION_THRESHOLD = 5.0f
    }
    
    // Interface pour les événements du trackpad
    interface OnTrackpadListener {
        fun onMouseMove(deltaX: Float, deltaY: Float)
        fun onMouseClick(button: String, isDoubleClick: Boolean = false)
        fun onMouseScroll(deltaX: Float, deltaY: Float)
        fun onGesture(gestureType: String, parameters: Map<String, Float>)
    }
    
    // Variables de style et apparence
    private var trackpadBackground: Paint = Paint(Paint.ANTI_ALIAS_FLAG)
    private var borderPaint: Paint = Paint(Paint.ANTI_ALIAS_FLAG)
    private var touchIndicatorPaint: Paint = Paint(Paint.ANTI_ALIAS_FLAG)
    private var gestureLinePaint: Paint = Paint(Paint.ANTI_ALIAS_FLAG)
    
    // Variables d'état
    private var listener: OnTrackpadListener? = null
    private var gestureProcessor: GestureProcessor = GestureProcessor()
    private var isEnabled = true
    private var showVisualFeedback = true
    
    // Détecteurs de gestes
    private lateinit var gestureDetector: GestureDetector
    private lateinit var scaleGestureDetector: ScaleGestureDetector
    private lateinit var rotationGestureDetector: RotationGestureDetector
    
    // Variables de suivi des touches
    private var activePointers = mutableMapOf<Int, PointF>()
    private var lastMoveTime = 0L
    private var lastMovePosition = PointF()
    private var isScrolling = false
    private var isInGesture = false
    
    // Variables pour les indicateurs visuels
    private var touchPoints = mutableListOf<PointF>()
    private var gesturePath = Path()
    private var fadeAnimator: ValueAnimator? = null
    
    init {
        setupPaints()
        setupGestureDetectors()
        setupAttributes(attrs)
    }
    
    /**
     * Configure les objets Paint pour le rendu
     */
    private fun setupPaints() {
        // Arrière-plan du trackpad
        trackpadBackground.apply {
            color = ContextCompat.getColor(context, R.color.trackpad_background)
            style = Paint.Style.FILL
        }
        
        // Bordure
        borderPaint.apply {
            color = ContextCompat.getColor(context, R.color.trackpad_border)
            style = Paint.Style.STROKE
            strokeWidth = 4f
        }
        
        // Indicateurs de toucher
        touchIndicatorPaint.apply {
            color = ContextCompat.getColor(context, R.color.touch_indicator)
            style = Paint.Style.FILL
            alpha = 150
        }
        
        // Lignes de geste
        gestureLinePaint.apply {
            color = ContextCompat.getColor(context, R.color.gesture_line)
            style = Paint.Style.STROKE
            strokeWidth = 3f
            pathEffect = DashPathEffect(floatArrayOf(10f, 5f), 0f)
        }
    }
    
    /**
     * Configure les détecteurs de gestes
     */
    private fun setupGestureDetectors() {
        gestureDetector = GestureDetector(context, TrackpadGestureListener())
        scaleGestureDetector = ScaleGestureDetector(context, ScaleGestureListener())
        rotationGestureDetector = RotationGestureDetector(RotationGestureListener())
    }
    
    /**
     * Configure les attributs personnalisés
     */
    private fun setupAttributes(attrs: AttributeSet?) {
        attrs?.let {
            val typedArray = context.obtainStyledAttributes(it, R.styleable.TrackpadView)
            
            showVisualFeedback = typedArray.getBoolean(R.styleable.TrackpadView_showVisualFeedback, true)
            
            // Couleurs personnalisables
            trackpadBackground.color = typedArray.getColor(
                R.styleable.TrackpadView_trackpadBackgroundColor,
                ContextCompat.getColor(context, R.color.trackpad_background)
            )
            
            borderPaint.color = typedArray.getColor(
                R.styleable.TrackpadView_trackpadBorderColor,
                ContextCompat.getColor(context, R.color.trackpad_border)
            )
            
            typedArray.recycle()
        }
    }
    
    /**
     * Définit le listener pour les événements du trackpad
     */
    fun setOnTrackpadListener(listener: OnTrackpadListener?) {
        this.listener = listener
    }
    
    override fun onSizeChanged(w: Int, h: Int, oldw: Int, oldh: Int) {
        super.onSizeChanged(w, h, oldw, oldh)
        // Recalculer les zones de geste si nécessaire
        gestureProcessor.updateViewBounds(w, h)
    }
    
    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        
        val cornerRadius = 16f
        val rect = RectF(0f, 0f, width.toFloat(), height.toFloat())
        
        // Dessiner l'arrière-plan avec coins arrondis
        canvas.drawRoundRect(rect, cornerRadius, cornerRadius, trackpadBackground)
        
        // Dessiner la bordure
        canvas.drawRoundRect(rect, cornerRadius, cornerRadius, borderPaint)
        
        // Dessiner les indicateurs visuels si activés
        if (showVisualFeedback) {
            drawTouchIndicators(canvas)
            drawGesturePath(canvas)
        }
    }
    
    /**
     * Dessine les indicateurs de points de contact
     */
    private fun drawTouchIndicators(canvas: Canvas) {
        touchPoints.forEach { point ->
            canvas.drawCircle(point.x, point.y, 30f, touchIndicatorPaint)
        }
    }
    
    /**
     * Dessine le chemin du geste en cours
     */
    private fun drawGesturePath(canvas: Canvas) {
        if (!gesturePath.isEmpty) {
            canvas.drawPath(gesturePath, gestureLinePaint)
        }
    }
    
    override fun onTouchEvent(event: MotionEvent): Boolean {
        if (!isEnabled) return false
        
        // Mettre à jour les points de contact pour l'affichage
        updateTouchPoints(event)
        
        // Traiter les gestes complexes en premier
        var handled = scaleGestureDetector.onTouchEvent(event)
        handled = rotationGestureDetector.onTouchEvent(event) || handled
        
        // Si pas de geste complexe, traiter les gestes simples
        if (!handled && !scaleGestureDetector.isInProgress) {
            handled = gestureDetector.onTouchEvent(event)
        }
        
        // Traitement personnalisé pour le mouvement multi-touch
        when (event.actionMasked) {
            MotionEvent.ACTION_DOWN,
            MotionEvent.ACTION_POINTER_DOWN -> {
                handlePointerDown(event)
            }
            
            MotionEvent.ACTION_MOVE -> {
                if (!isInGesture) {
                    handleMove(event)
                }
            }
            
            MotionEvent.ACTION_UP,
            MotionEvent.ACTION_POINTER_UP -> {
                handlePointerUp(event)
            }
            
            MotionEvent.ACTION_CANCEL -> {
                handleCancel()
            }
        }
        
        invalidate()
        return true
    }
    
    /**
     * Met à jour les points de contact pour l'affichage visuel
     */
    private fun updateTouchPoints(event: MotionEvent) {
        touchPoints.clear()
        for (i in 0 until event.pointerCount) {
            touchPoints.add(PointF(event.getX(i), event.getY(i)))
        }
    }
    
    /**
     * Gère l'appui d'un pointeur
     */
    private fun handlePointerDown(event: MotionEvent) {
        val pointerIndex = event.actionIndex
        val pointerId = event.getPointerId(pointerIndex)
        
        activePointers[pointerId] = PointF(
            event.getX(pointerIndex),
            event.getY(pointerIndex)
        )
        
        // Commencer un nouveau chemin de geste
        if (activePointers.size == 1) {
            gesturePath.reset()
            gesturePath.moveTo(event.getX(pointerIndex), event.getY(pointerIndex))
        }
    }
    
    /**
     * Gère le mouvement des pointeurs
     */
    private fun handleMove(event: MotionEvent) {
        if (activePointers.isEmpty()) return
        
        val currentTime = System.currentTimeMillis()
        
        when (activePointers.size) {
            1 -> handleSingleFingerMove(event, currentTime)
            2 -> handleTwoFingerMove(event, currentTime)
        }
        
        // Mettre à jour le chemin de geste
        if (activePointers.size == 1) {
            gesturePath.lineTo(event.x, event.y)
        }
    }
    
    /**
     * Gère le mouvement à un doigt (mouvement de souris)
     */
    private fun handleSingleFingerMove(event: MotionEvent, currentTime: Long) {
        val currentPos = PointF(event.x, event.y)
        
        if (lastMoveTime > 0) {
            val deltaTime = currentTime - lastMoveTime
            val deltaX = currentPos.x - lastMovePosition.x
            val deltaY = currentPos.y - lastMovePosition.y
            
            // Filtrer les mouvements trop petits
            val distance = sqrt(deltaX * deltaX + deltaY * deltaY)
            if (distance > MOVEMENT_THRESHOLD && deltaTime > 0) {
                // Appliquer une sensibilité basée sur la vitesse
                val velocity = distance / deltaTime
                val sensitivity = gestureProcessor.calculateSensitivity(velocity)
                
                listener?.onMouseMove(deltaX * sensitivity, deltaY * sensitivity)
            }
        }
        
        lastMovePosition = currentPos
        lastMoveTime = currentTime
    }
    
    /**
     * Gère le mouvement à deux doigts (scroll)
     */
    private fun handleTwoFingerMove(event: MotionEvent, currentTime: Long) {
        if (!isScrolling && activePointers.size == 2) {
            isScrolling = true
        }
        
        if (isScrolling && event.pointerCount >= 2) {
            val deltaX = event.getX(0) - event.getX(1)
            val deltaY = event.getY(0) - event.getY(1)
            
            // Calculer le mouvement moyen
            val avgDeltaX = deltaX * SCROLL_SENSITIVITY
            val avgDeltaY = deltaY * SCROLL_SENSITIVITY
            
            listener?.onMouseScroll(avgDeltaX, avgDeltaY)
        }
    }
    
    /**
     * Gère la levée d'un pointeur
     */
    private fun handlePointerUp(event: MotionEvent) {
        val pointerIndex = event.actionIndex
        val pointerId = event.getPointerId(pointerIndex)
        
        activePointers.remove(pointerId)
        
        if (activePointers.isEmpty()) {
            isScrolling = false
            isInGesture = false
            lastMoveTime = 0
            
            // Animer la disparition des indicateurs visuels
            animateFadeOut()
        }
    }
    
    /**
     * Gère l'annulation du geste
     */
    private fun handleCancel() {
        activePointers.clear()
        isScrolling = false
        isInGesture = false
        lastMoveTime = 0
        gesturePath.reset()
        invalidate()
    }
    
    /**
     * Anime la disparition des indicateurs visuels
     */
    private fun animateFadeOut() {
        fadeAnimator?.cancel()
        fadeAnimator = ValueAnimator.ofInt(255, 0).apply {
            duration = 300
            addUpdateListener { animator ->
                val alpha = animator.animatedValue as Int
                touchIndicatorPaint.alpha = alpha
                gestureLinePaint.alpha = alpha
                invalidate()
            }
            addListener(object : AnimatorListenerAdapter() {
                override fun onAnimationEnd(animation: Animator) {
                    gesturePath.reset()
                    touchPoints.clear()
                    touchIndicatorPaint.alpha = 150
                    gestureLinePaint.alpha = 255
                }
            })
            start()
        }
    }
    
    /**
     * Gestionnaire de gestes simples
     */
    private inner class TrackpadGestureListener : GestureDetector.SimpleOnGestureListener() {
        
        override fun onSingleTapConfirmed(e: MotionEvent): Boolean {
            listener?.onMouseClick("left", false)
            return true
        }
        
        override fun onDoubleTap(e: MotionEvent): Boolean {
            listener?.onMouseClick("left", true)
            return true
        }
        
        override fun onLongPress(e: MotionEvent) {
            // Long press = clic droit
            listener?.onMouseClick("right", false)
            
            // Vibration pour feedback tactile
            performHapticFeedback(HapticFeedbackConstants.LONG_PRESS)
        }
        
        override fun onFling(e1: MotionEvent?, e2: MotionEvent, velocityX: Float, velocityY: Float): Boolean {
            // Geste de balayage rapide
            val parameters = mapOf(
                "velocityX" to velocityX,
                "velocityY" to velocityY,
                "distance" to sqrt(velocityX * velocityX + velocityY * velocityY)
            )
            
            listener?.onGesture("swipe", parameters)
            return true
        }
    }
    
    /**
     * Gestionnaire de gestes de pincement/zoom
     */
    private inner class ScaleGestureListener : ScaleGestureDetector.SimpleOnScaleGestureListener() {
        
        override fun onScaleBegin(detector: ScaleGestureDetector): Boolean {
            isInGesture = true
            return true
        }
        
        override fun onScale(detector: ScaleGestureDetector): Boolean {
            val scaleFactor = detector.scaleFactor
            
            if (abs(scaleFactor - 1.0f) > PINCH_THRESHOLD) {
                val parameters = mapOf(
                    "scale" to scaleFactor,
                    "focusX" to detector.focusX,
                    "focusY" to detector.focusY
                )
                
                listener?.onGesture("pinch", parameters)
            }
            
            return true
        }
        
        override fun onScaleEnd(detector: ScaleGestureDetector) {
            isInGesture = false
        }
    }
    
    /**
     * Gestionnaire de gestes de rotation
     */
    private inner class RotationGestureListener : RotationGestureDetector.OnRotationGestureListener {
        
        override fun onRotationBegin(detector: RotationGestureDetector): Boolean {
            isInGesture = true
            return true
        }
        
        override fun onRotation(detector: RotationGestureDetector): Boolean {
            val rotationDelta = detector.rotationDelta
            
            if (abs(rotationDelta) > ROTATION_THRESHOLD) {
                val parameters = mapOf(
                    "rotation" to rotationDelta,
                    "centerX" to detector.centerX,
                    "centerY" to detector.centerY
                )
                
                listener?.onGesture("rotate", parameters)
            }
            
            return true
        }
        
        override fun onRotationEnd(detector: RotationGestureDetector) {
            isInGesture = false
        }
    }
    
    /**
     * Méthodes publiques pour contrôler la vue
     */
    
    fun onResume() {
        isEnabled = true
    }
    
    fun onPause() {
        isEnabled = false
        handleCancel()
    }
    
    override fun setEnabled(enabled: Boolean) {
        super.setEnabled(enabled)
        isEnabled = enabled
        if (!enabled) {
            handleCancel()
        }
        alpha = if (enabled) 1.0f else 0.5f
    }
    
    fun setShowVisualFeedback(show: Boolean) {
        showVisualFeedback = show
        invalidate()
    }
    
    fun setSensitivity(sensitivity: Float) {
        gestureProcessor.setSensitivity(sensitivity)
    }
}
