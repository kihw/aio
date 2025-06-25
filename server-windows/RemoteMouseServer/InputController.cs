using System;
using System.Runtime.InteropServices;
using System.Threading.Tasks;
using System.Windows.Forms;
using Microsoft.Extensions.Logging;
using RemoteMouseServer.Models;

namespace RemoteMouseServer
{
    /// <summary>
    /// Contrôleur d'entrée pour Windows API - gestion souris et clavier
    /// Utilise les APIs Windows natives pour un contrôle précis et performant
    /// </summary>
    public class InputController
    {
        private readonly ILogger<InputController> _logger;
        
        // Configuration
        private float _mouseSensitivity = 1.0f;
        private float _scrollSpeed = 1.0f;
        private bool _smoothMovement = true;
        
        // État actuel
        private float _accumulatedX = 0f;
        private float _accumulatedY = 0f;

        public InputController(ILogger<InputController> logger)
        {
            _logger = logger;
        }

        #region Windows API Declarations

        [DllImport("user32.dll", SetLastError = true)]
        private static extern uint SendInput(uint nInputs, INPUT[] pInputs, int cbSize);

        [DllImport("user32.dll")]
        private static extern short VkKeyScan(char ch);

        [DllImport("user32.dll")]
        private static extern uint MapVirtualKey(uint uCode, uint uMapType);

        [DllImport("user32.dll")]
        private static extern bool SetCursorPos(int x, int y);

        [DllImport("user32.dll")]
        private static extern bool GetCursorPos(out POINT lpPoint);

        [DllImport("user32.dll")]
        private static extern int GetSystemMetrics(int nIndex);

        // Constantes système
        private const int SM_CXSCREEN = 0;
        private const int SM_CYSCREEN = 1;
        private const int INPUT_MOUSE = 0;
        private const int INPUT_KEYBOARD = 1;

        // Flags pour la souris
        private const uint MOUSEEVENTF_MOVE = 0x0001;
        private const uint MOUSEEVENTF_LEFTDOWN = 0x0002;
        private const uint MOUSEEVENTF_LEFTUP = 0x0004;
        private const uint MOUSEEVENTF_RIGHTDOWN = 0x0008;
        private const uint MOUSEEVENTF_RIGHTUP = 0x0010;
        private const uint MOUSEEVENTF_MIDDLEDOWN = 0x0020;
        private const uint MOUSEEVENTF_MIDDLEUP = 0x0040;
        private const uint MOUSEEVENTF_WHEEL = 0x0800;
        private const uint MOUSEEVENTF_HWHEEL = 0x1000;
        private const uint MOUSEEVENTF_ABSOLUTE = 0x8000;

        // Flags pour le clavier
        private const uint KEYEVENTF_KEYDOWN = 0x0000;
        private const uint KEYEVENTF_KEYUP = 0x0002;
        private const uint KEYEVENTF_SCANCODE = 0x0008;
        private const uint KEYEVENTF_UNICODE = 0x0004;

        // Structures
        [StructLayout(LayoutKind.Sequential)]
        private struct POINT
        {
            public int X;
            public int Y;
        }

        [StructLayout(LayoutKind.Sequential)]
        private struct INPUT
        {
            public uint Type;
            public INPUTUNION Union;
        }

        [StructLayout(LayoutKind.Explicit)]
        private struct INPUTUNION
        {
            [FieldOffset(0)]
            public MOUSEINPUT Mouse;
            [FieldOffset(0)]
            public KEYBDINPUT Keyboard;
        }

        [StructLayout(LayoutKind.Sequential)]
        private struct MOUSEINPUT
        {
            public int dx;
            public int dy;
            public uint mouseData;
            public uint dwFlags;
            public uint time;
            public IntPtr dwExtraInfo;
        }

        [StructLayout(LayoutKind.Sequential)]
        private struct KEYBDINPUT
        {
            public ushort wVk;
            public ushort wScan;
            public uint dwFlags;
            public uint time;
            public IntPtr dwExtraInfo;
        }

        #endregion

        #region Mouse Control

        /// <summary>
        /// Déplace la souris relativement à sa position actuelle
        /// </summary>
        public async Task MoveMouse(float deltaX, float deltaY, float sensitivity = 1.0f)
        {
            try
            {
                // Appliquer la sensibilité
                var adjustedSensitivity = _mouseSensitivity * sensitivity;
                var adjustedDeltaX = deltaX * adjustedSensitivity;
                var adjustedDeltaY = deltaY * adjustedSensitivity;

                if (_smoothMovement)
                {
                    // Accumulation pour les petits mouvements
                    _accumulatedX += adjustedDeltaX;
                    _accumulatedY += adjustedDeltaY;

                    var moveX = (int)Math.Round(_accumulatedX);
                    var moveY = (int)Math.Round(_accumulatedY);

                    if (Math.Abs(moveX) > 0 || Math.Abs(moveY) > 0)
                    {
                        _accumulatedX -= moveX;
                        _accumulatedY -= moveY;

                        await ExecuteMouseMove(moveX, moveY);
                    }
                }
                else
                {
                    await ExecuteMouseMove((int)adjustedDeltaX, (int)adjustedDeltaY);
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error moving mouse: deltaX={DeltaX}, deltaY={DeltaY}", deltaX, deltaY);
            }
        }

        /// <summary>
        /// Exécute le mouvement de souris via l'API Windows
        /// </summary>
        private async Task ExecuteMouseMove(int deltaX, int deltaY)
        {
            if (deltaX == 0 && deltaY == 0) return;

            await Task.Run(() =>
            {
                var input = new INPUT
                {
                    Type = INPUT_MOUSE,
                    Union = new INPUTUNION
                    {
                        Mouse = new MOUSEINPUT
                        {
                            dx = deltaX,
                            dy = deltaY,
                            dwFlags = MOUSEEVENTF_MOVE,
                            time = 0,
                            dwExtraInfo = IntPtr.Zero
                        }
                    }
                };

                SendInput(1, new[] { input }, Marshal.SizeOf<INPUT>());
            });
        }

        /// <summary>
        /// Effectue un clic de souris
        /// </summary>
        public async Task ClickMouse(MouseButton button, MouseAction action)
        {
            try
            {
                uint downFlag, upFlag;

                switch (button)
                {
                    case MouseButton.LEFT:
                        downFlag = MOUSEEVENTF_LEFTDOWN;
                        upFlag = MOUSEEVENTF_LEFTUP;
                        break;
                    case MouseButton.RIGHT:
                        downFlag = MOUSEEVENTF_RIGHTDOWN;
                        upFlag = MOUSEEVENTF_RIGHTUP;
                        break;
                    case MouseButton.MIDDLE:
                        downFlag = MOUSEEVENTF_MIDDLEDOWN;
                        upFlag = MOUSEEVENTF_MIDDLEUP;
                        break;
                    default:
                        _logger.LogWarning("Unknown mouse button: {Button}", button);
                        return;
                }

                await ExecuteMouseClick(downFlag, upFlag, action);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error clicking mouse: button={Button}, action={Action}", button, action);
            }
        }

        /// <summary>
        /// Exécute un clic de souris via l'API Windows
        /// </summary>
        private async Task ExecuteMouseClick(uint downFlag, uint upFlag, MouseAction action)
        {
            await Task.Run(async () =>
            {
                switch (action)
                {
                    case MouseAction.DOWN:
                        SendMouseEvent(downFlag);
                        break;

                    case MouseAction.UP:
                        SendMouseEvent(upFlag);
                        break;

                    case MouseAction.CLICK:
                        SendMouseEvent(downFlag);
                        await Task.Delay(10); // Délai court pour simuler un clic réel
                        SendMouseEvent(upFlag);
                        break;

                    case MouseAction.DOUBLE_CLICK:
                        // Premier clic
                        SendMouseEvent(downFlag);
                        await Task.Delay(10);
                        SendMouseEvent(upFlag);
                        
                        // Délai entre les clics
                        await Task.Delay(50);
                        
                        // Deuxième clic
                        SendMouseEvent(downFlag);
                        await Task.Delay(10);
                        SendMouseEvent(upFlag);
                        break;
                }
            });
        }

        /// <summary>
        /// Envoie un événement de souris
        /// </summary>
        private void SendMouseEvent(uint flag)
        {
            var input = new INPUT
            {
                Type = INPUT_MOUSE,
                Union = new INPUTUNION
                {
                    Mouse = new MOUSEINPUT
                    {
                        dx = 0,
                        dy = 0,
                        dwFlags = flag,
                        time = 0,
                        dwExtraInfo = IntPtr.Zero
                    }
                }
            };

            SendInput(1, new[] { input }, Marshal.SizeOf<INPUT>());
        }

        /// <summary>
        /// Effectue un scroll de souris
        /// </summary>
        public async Task ScrollMouse(float deltaX, float deltaY, bool horizontal = false)
        {
            try
            {
                var adjustedSpeed = _scrollSpeed;
                
                if (horizontal && Math.Abs(deltaX) > 0)
                {
                    await ExecuteScroll((int)(deltaX * adjustedSpeed * 120), true);
                }
                
                if (Math.Abs(deltaY) > 0)
                {
                    await ExecuteScroll((int)(deltaY * adjustedSpeed * 120), false);
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error scrolling mouse: deltaX={DeltaX}, deltaY={DeltaY}", deltaX, deltaY);
            }
        }

        /// <summary>
        /// Exécute un scroll via l'API Windows
        /// </summary>
        private async Task ExecuteScroll(int wheelData, bool horizontal)
        {
            await Task.Run(() =>
            {
                var input = new INPUT
                {
                    Type = INPUT_MOUSE,
                    Union = new INPUTUNION
                    {
                        Mouse = new MOUSEINPUT
                        {
                            dx = 0,
                            dy = 0,
                            mouseData = (uint)wheelData,
                            dwFlags = horizontal ? MOUSEEVENTF_HWHEEL : MOUSEEVENTF_WHEEL,
                            time = 0,
                            dwExtraInfo = IntPtr.Zero
                        }
                    }
                };

                SendInput(1, new[] { input }, Marshal.SizeOf<INPUT>());
            });
        }

        #endregion

        #region Keyboard Control

        /// <summary>
        /// Envoie un événement clavier
        /// </summary>
        public async Task SendKey(string key, int keyCode, KeyAction action, KeyModifiers modifiers)
        {
            try
            {
                await Task.Run(async () =>
                {
                    // Appuyer sur les modificateurs
                    if (modifiers.Ctrl) await SendKeyEvent(Keys.ControlKey, KEYEVENTF_KEYDOWN);
                    if (modifiers.Alt) await SendKeyEvent(Keys.Menu, KEYEVENTF_KEYDOWN);
                    if (modifiers.Shift) await SendKeyEvent(Keys.ShiftKey, KEYEVENTF_KEYDOWN);
                    if (modifiers.Win) await SendKeyEvent(Keys.LWin, KEYEVENTF_KEYDOWN);

                    // Envoyer la touche principale
                    var vkCode = (Keys)keyCode;
                    
                    switch (action)
                    {
                        case KeyAction.DOWN:
                            await SendKeyEvent(vkCode, KEYEVENTF_KEYDOWN);
                            break;
                        case KeyAction.UP:
                            await SendKeyEvent(vkCode, KEYEVENTF_KEYUP);
                            break;
                        case KeyAction.PRESS:
                            await SendKeyEvent(vkCode, KEYEVENTF_KEYDOWN);
                            await Task.Delay(10);
                            await SendKeyEvent(vkCode, KEYEVENTF_KEYUP);
                            break;
                    }

                    // Relâcher les modificateurs (dans l'ordre inverse)
                    if (modifiers.Win) await SendKeyEvent(Keys.LWin, KEYEVENTF_KEYUP);
                    if (modifiers.Shift) await SendKeyEvent(Keys.ShiftKey, KEYEVENTF_KEYUP);
                    if (modifiers.Alt) await SendKeyEvent(Keys.Menu, KEYEVENTF_KEYUP);
                    if (modifiers.Ctrl) await SendKeyEvent(Keys.ControlKey, KEYEVENTF_KEYUP);
                });
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error sending key: key={Key}, keyCode={KeyCode}, action={Action}", 
                               key, keyCode, action);
            }
        }

        /// <summary>
        /// Envoie un événement clavier spécifique
        /// </summary>
        private async Task SendKeyEvent(Keys key, uint flags)
        {
            await Task.Run(() =>
            {
                var input = new INPUT
                {
                    Type = INPUT_KEYBOARD,
                    Union = new INPUTUNION
                    {
                        Keyboard = new KEYBDINPUT
                        {
                            wVk = (ushort)key,
                            wScan = (ushort)MapVirtualKey((uint)key, 0),
                            dwFlags = flags,
                            time = 0,
                            dwExtraInfo = IntPtr.Zero
                        }
                    }
                };

                SendInput(1, new[] { input }, Marshal.SizeOf<INPUT>());
            });
        }

        /// <summary>
        /// Envoie du texte caractère par caractère
        /// </summary>
        public async Task SendText(string text)
        {
            try
            {
                await Task.Run(async () =>
                {
                    foreach (char c in text)
                    {
                        if (char.IsControl(c))
                        {
                            // Gérer les caractères de contrôle spéciaux
                            await HandleControlCharacter(c);
                        }
                        else
                        {
                            await SendUnicodeCharacter(c);
                        }
                        
                        // Petit délai entre les caractères pour une saisie plus naturelle
                        await Task.Delay(5);
                    }
                });
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error sending text: {Text}", text);
            }
        }

        /// <summary>
        /// Envoie un caractère Unicode
        /// </summary>
        private async Task SendUnicodeCharacter(char character)
        {
            await Task.Run(() =>
            {
                var inputs = new INPUT[2];

                // Key down
                inputs[0] = new INPUT
                {
                    Type = INPUT_KEYBOARD,
                    Union = new INPUTUNION
                    {
                        Keyboard = new KEYBDINPUT
                        {
                            wVk = 0,
                            wScan = character,
                            dwFlags = KEYEVENTF_UNICODE,
                            time = 0,
                            dwExtraInfo = IntPtr.Zero
                        }
                    }
                };

                // Key up
                inputs[1] = new INPUT
                {
                    Type = INPUT_KEYBOARD,
                    Union = new INPUTUNION
                    {
                        Keyboard = new KEYBDINPUT
                        {
                            wVk = 0,
                            wScan = character,
                            dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP,
                            time = 0,
                            dwExtraInfo = IntPtr.Zero
                        }
                    }
                };

                SendInput(2, inputs, Marshal.SizeOf<INPUT>());
            });
        }

        /// <summary>
        /// Gère les caractères de contrôle
        /// </summary>
        private async Task HandleControlCharacter(char c)
        {
            switch (c)
            {
                case '\n':
                case '\r':
                    await SendKeyEvent(Keys.Return, KEYEVENTF_KEYDOWN);
                    await Task.Delay(10);
                    await SendKeyEvent(Keys.Return, KEYEVENTF_KEYUP);
                    break;
                case '\t':
                    await SendKeyEvent(Keys.Tab, KEYEVENTF_KEYDOWN);
                    await Task.Delay(10);
                    await SendKeyEvent(Keys.Tab, KEYEVENTF_KEYUP);
                    break;
                case '\b':
                    await SendKeyEvent(Keys.Back, KEYEVENTF_KEYDOWN);
                    await Task.Delay(10);
                    await SendKeyEvent(Keys.Back, KEYEVENTF_KEYUP);
                    break;
            }
        }

        #endregion

        #region Gesture Processing

        /// <summary>
        /// Traite un geste multi-touch
        /// </summary>
        public async Task ProcessGesture(GestureType gestureType, GestureState state, GestureParameters parameters)
        {
            try
            {
                switch (gestureType)
                {
                    case GestureType.PINCH:
                        await ProcessPinchGesture(state, parameters);
                        break;
                    case GestureType.ROTATE:
                        await ProcessRotateGesture(state, parameters);
                        break;
                    case GestureType.SWIPE:
                        await ProcessSwipeGesture(state, parameters);
                        break;
                    default:
                        _logger.LogWarning("Unknown gesture type: {GestureType}", gestureType);
                        break;
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error processing gesture: type={GestureType}, state={State}", 
                               gestureType, state);
            }
        }

        /// <summary>
        /// Traite un geste de pincement (zoom)
        /// </summary>
        private async Task ProcessPinchGesture(GestureState state, GestureParameters parameters)
        {
            if (parameters.Scale.HasValue)
            {
                var scale = parameters.Scale.Value;
                
                // Convertir en événements de scroll avec Ctrl (zoom)
                var modifiers = new KeyModifiers { Ctrl = true };
                var scrollDelta = scale > 1.0f ? 1.0f : -1.0f;
                
                await SendKey("Control", (int)Keys.ControlKey, KeyAction.DOWN, new KeyModifiers());
                await ScrollMouse(0, scrollDelta * Math.Abs(scale - 1.0f) * 5);
                await SendKey("Control", (int)Keys.ControlKey, KeyAction.UP, new KeyModifiers());
            }
        }

        /// <summary>
        /// Traite un geste de rotation
        /// </summary>
        private async Task ProcessRotateGesture(GestureState state, GestureParameters parameters)
        {
            if (parameters.Rotation.HasValue)
            {
                // Pour l'instant, mapper la rotation vers scroll horizontal
                var rotation = parameters.Rotation.Value;
                await ScrollMouse(rotation / 45.0f, 0, true);
            }
        }

        /// <summary>
        /// Traite un geste de balayage
        /// </summary>
        private async Task ProcessSwipeGesture(GestureState state, GestureParameters parameters)
        {
            if (parameters.Velocity.HasValue)
            {
                var velocity = parameters.Velocity.Value;
                
                // Mapper vers des actions de navigation (page précédente/suivante)
                if (velocity > 500) // Balayage rapide vers la droite
                {
                    await SendKey("Right", (int)Keys.Right, KeyAction.PRESS, new KeyModifiers { Alt = true });
                }
                else if (velocity < -500) // Balayage rapide vers la gauche
                {
                    await SendKey("Left", (int)Keys.Left, KeyAction.PRESS, new KeyModifiers { Alt = true });
                }
            }
        }

        #endregion

        #region Configuration

        /// <summary>
        /// Définit la sensibilité de la souris
        /// </summary>
        public void SetSensitivity(float sensitivity)
        {
            _mouseSensitivity = Math.Max(0.1f, Math.Min(5.0f, sensitivity));
            _logger.LogInformation("Mouse sensitivity set to {Sensitivity}", _mouseSensitivity);
        }

        /// <summary>
        /// Définit la vitesse de défilement
        /// </summary>
        public void SetScrollSpeed(float scrollSpeed)
        {
            _scrollSpeed = Math.Max(0.1f, Math.Min(5.0f, scrollSpeed));
            _logger.LogInformation("Scroll speed set to {ScrollSpeed}", _scrollSpeed);
        }

        /// <summary>
        /// Active/désactive le mouvement fluide
        /// </summary>
        public void SetSmoothMovement(bool enabled)
        {
            _smoothMovement = enabled;
            if (!enabled)
            {
                // Réinitialiser l'accumulation
                _accumulatedX = 0f;
                _accumulatedY = 0f;
            }
            _logger.LogInformation("Smooth movement {Status}", enabled ? "enabled" : "disabled");
        }

        /// <summary>
        /// Obtient la position actuelle de la souris
        /// </summary>
        public (int X, int Y) GetMousePosition()
        {
            GetCursorPos(out POINT point);
            return (point.X, point.Y);
        }

        /// <summary>
        /// Obtient les dimensions de l'écran
        /// </summary>
        public (int Width, int Height) GetScreenSize()
        {
            return (GetSystemMetrics(SM_CXSCREEN), GetSystemMetrics(SM_CYSCREEN));
        }

        #endregion
    }
}
