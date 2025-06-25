package com.remotemouse.android.models

import com.google.gson.Gson
import com.google.gson.annotations.SerializedName
import kotlinx.parcelize.Parcelize
import android.os.Parcelable

/**
 * Classes pour les messages du protocole WebSocket Remote Mouse & Keyboard
 */

// Message de base pour tous les échanges WebSocket
@Parcelize
data class BaseMessage(
    @SerializedName("type") val type: String,
    @SerializedName("timestamp") val timestamp: Long,
    @SerializedName("sessionId") val sessionId: String?,
    @SerializedName("data") val data: String // JSON stringifié des données spécifiques
) : Parcelable

// Types de messages
object MessageType {
    // Authentification
    const val AUTH_REQUEST = "AUTH_REQUEST"
    const val AUTH_RESPONSE = "AUTH_RESPONSE"
    
    // Contrôle souris
    const val MOUSE_MOVE = "MOUSE_MOVE"
    const val MOUSE_CLICK = "MOUSE_CLICK"
    const val MOUSE_SCROLL = "MOUSE_SCROLL"
    
    // Contrôle clavier
    const val KEY_EVENT = "KEY_EVENT"
    const val TEXT_INPUT = "TEXT_INPUT"
    
    // Gestes avancés
    const val GESTURE_EVENT = "GESTURE_EVENT"
    
    // Messages de statut
    const val HEARTBEAT = "HEARTBEAT"
    const val ERROR = "ERROR"
    const val STATUS_UPDATE = "STATUS_UPDATE"
    
    // Configuration
    const val CONFIG_UPDATE = "CONFIG_UPDATE"
}

// Données d'authentification
@Parcelize
data class AuthRequestData(
    @SerializedName("pin") val pin: String,
    @SerializedName("deviceName") val deviceName: String,
    @SerializedName("deviceId") val deviceId: String
) : Parcelable

@Parcelize
data class ServerInfo(
    @SerializedName("name") val name: String,
    @SerializedName("version") val version: String
) : Parcelable

@Parcelize
data class AuthResponseData(
    @SerializedName("success") val success: Boolean,
    @SerializedName("message") val message: String,
    @SerializedName("serverInfo") val serverInfo: ServerInfo?
) : Parcelable

// Données de contrôle souris
@Parcelize
data class MouseMoveData(
    @SerializedName("deltaX") val deltaX: Float,
    @SerializedName("deltaY") val deltaY: Float,
    @SerializedName("sensitivity") val sensitivity: Float = 1.0f
) : Parcelable

enum class MouseButton {
    @SerializedName("left") LEFT,
    @SerializedName("right") RIGHT,
    @SerializedName("middle") MIDDLE
}

enum class MouseAction {
    @SerializedName("down") DOWN,
    @SerializedName("up") UP,
    @SerializedName("click") CLICK,
    @SerializedName("double_click") DOUBLE_CLICK
}

@Parcelize
data class MouseClickData(
    @SerializedName("button") val button: MouseButton,
    @SerializedName("action") val action: MouseAction
) : Parcelable

@Parcelize
data class MouseScrollData(
    @SerializedName("deltaX") val deltaX: Float,
    @SerializedName("deltaY") val deltaY: Float,
    @SerializedName("horizontal") val horizontal: Boolean = false
) : Parcelable

// Données de contrôle clavier
@Parcelize
data class KeyModifiers(
    @SerializedName("ctrl") val ctrl: Boolean = false,
    @SerializedName("alt") val alt: Boolean = false,
    @SerializedName("shift") val shift: Boolean = false,
    @SerializedName("win") val win: Boolean = false
) : Parcelable

enum class KeyAction {
    @SerializedName("down") DOWN,
    @SerializedName("up") UP,
    @SerializedName("press") PRESS
}

@Parcelize
data class KeyEventData(
    @SerializedName("key") val key: String,
    @SerializedName("keyCode") val keyCode: Int,
    @SerializedName("action") val action: KeyAction,
    @SerializedName("modifiers") val modifiers: KeyModifiers
) : Parcelable

@Parcelize
data class TextInputData(
    @SerializedName("text") val text: String
) : Parcelable

// Données de gestes
enum class GestureType {
    @SerializedName("pinch") PINCH,
    @SerializedName("rotate") ROTATE,
    @SerializedName("swipe") SWIPE
}

enum class GestureState {
    @SerializedName("start") START,
    @SerializedName("ongoing") ONGOING,
    @SerializedName("end") END
}

@Parcelize
data class GestureParameters(
    @SerializedName("scale") val scale: Float? = null,          // Pour pinch
    @SerializedName("rotation") val rotation: Float? = null,    // Pour rotate (degrés)
    @SerializedName("velocity") val velocity: Float? = null     // Pour swipe (px/s)
) : Parcelable

@Parcelize
data class GestureEventData(
    @SerializedName("gestureType") val gestureType: GestureType,
    @SerializedName("state") val state: GestureState,
    @SerializedName("parameters") val parameters: GestureParameters
) : Parcelable

// Données de statut
@Parcelize
data class HeartbeatData(
    @SerializedName("status") val status: String = "alive"
) : Parcelable

@Parcelize
data class ErrorData(
    @SerializedName("code") val code: String,
    @SerializedName("message") val message: String,
    @SerializedName("fatal") val fatal: Boolean = false
) : Parcelable

@Parcelize
data class ServerSettings(
    @SerializedName("sensitivity") val sensitivity: Float,
    @SerializedName("scrollSpeed") val scrollSpeed: Float
) : Parcelable

@Parcelize
data class StatusUpdateData(
    @SerializedName("serverStatus") val serverStatus: String,
    @SerializedName("connectedClients") val connectedClients: Int,
    @SerializedName("settings") val settings: ServerSettings
) : Parcelable

// Données de configuration
@Parcelize
data class ConfigUpdateData(
    @SerializedName("sensitivity") val sensitivity: Float? = null,
    @SerializedName("scrollSpeed") val scrollSpeed: Float? = null,
    @SerializedName("tapToClick") val tapToClick: Boolean? = null
) : Parcelable

// Codes d'erreur standardisés
object ErrorCodes {
    const val INVALID_PIN = "INVALID_PIN"
    const val INVALID_SESSION = "INVALID_SESSION"
    const val RATE_LIMIT = "RATE_LIMIT"
    const val SERVER_ERROR = "SERVER_ERROR"
    const val UNSUPPORTED_MESSAGE = "UNSUPPORTED_MESSAGE"
}

/**
 * Utilitaire pour sérialiser/désérialiser les messages
 */
class MessageSerializer {
    private val gson = Gson()
    
    fun <T> createMessage(type: String, sessionId: String?, data: T): BaseMessage {
        return BaseMessage(
            type = type,
            timestamp = System.currentTimeMillis(),
            sessionId = sessionId,
            data = gson.toJson(data)
        )
    }
    
    fun serializeMessage(message: BaseMessage): String {
        return gson.toJson(message)
    }
    
    fun deserializeMessage(json: String): BaseMessage? {
        return try {
            gson.fromJson(json, BaseMessage::class.java)
        } catch (e: Exception) {
            null
        }
    }
    
    inline fun <reified T> deserializeData(dataJson: String): T? {
        return try {
            gson.fromJson(dataJson, T::class.java)
        } catch (e: Exception) {
            null
        }
    }
}

/**
 * Builder pour créer facilement des messages
 */
class MessageBuilder(private val serializer: MessageSerializer = MessageSerializer()) {
    
    fun authRequest(pin: String, deviceName: String, deviceId: String): String {
        val data = AuthRequestData(pin, deviceName, deviceId)
        val message = serializer.createMessage(MessageType.AUTH_REQUEST, null, data)
        return serializer.serializeMessage(message)
    }
    
    fun mouseMove(sessionId: String, deltaX: Float, deltaY: Float, sensitivity: Float = 1.0f): String {
        val data = MouseMoveData(deltaX, deltaY, sensitivity)
        val message = serializer.createMessage(MessageType.MOUSE_MOVE, sessionId, data)
        return serializer.serializeMessage(message)
    }
    
    fun mouseClick(sessionId: String, button: MouseButton, action: MouseAction): String {
        val data = MouseClickData(button, action)
        val message = serializer.createMessage(MessageType.MOUSE_CLICK, sessionId, data)
        return serializer.serializeMessage(message)
    }
    
    fun mouseScroll(sessionId: String, deltaX: Float, deltaY: Float, horizontal: Boolean = false): String {
        val data = MouseScrollData(deltaX, deltaY, horizontal)
        val message = serializer.createMessage(MessageType.MOUSE_SCROLL, sessionId, data)
        return serializer.serializeMessage(message)
    }
    
    fun keyEvent(sessionId: String, key: String, keyCode: Int, action: KeyAction, modifiers: KeyModifiers): String {
        val data = KeyEventData(key, keyCode, action, modifiers)
        val message = serializer.createMessage(MessageType.KEY_EVENT, sessionId, data)
        return serializer.serializeMessage(message)
    }
    
    fun textInput(sessionId: String, text: String): String {
        val data = TextInputData(text)
        val message = serializer.createMessage(MessageType.TEXT_INPUT, sessionId, data)
        return serializer.serializeMessage(message)
    }
    
    fun gestureEvent(sessionId: String, gestureType: GestureType, state: GestureState, parameters: GestureParameters): String {
        val data = GestureEventData(gestureType, state, parameters)
        val message = serializer.createMessage(MessageType.GESTURE_EVENT, sessionId, data)
        return serializer.serializeMessage(message)
    }
    
    fun heartbeat(sessionId: String): String {
        val data = HeartbeatData()
        val message = serializer.createMessage(MessageType.HEARTBEAT, sessionId, data)
        return serializer.serializeMessage(message)
    }
    
    fun configUpdate(sessionId: String, sensitivity: Float?, scrollSpeed: Float?, tapToClick: Boolean?): String {
        val data = ConfigUpdateData(sensitivity, scrollSpeed, tapToClick)
        val message = serializer.createMessage(MessageType.CONFIG_UPDATE, sessionId, data)
        return serializer.serializeMessage(message)
    }
}
