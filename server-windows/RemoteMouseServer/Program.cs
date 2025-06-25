using System;
using System.IO;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Forms;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using RemoteMouseServer.Config;
using RemoteMouseServer.Logging;
using RemoteMouseServer.Security;
using RemoteMouseServer.UI;

namespace RemoteMouseServer
{
    /// <summary>
    /// Point d'entrée principal du serveur Remote Mouse & Keyboard
    /// Gère l'initialisation, la configuration et l'interface tray
    /// </summary>
    internal class Program
    {
        private static readonly string AppName = "Remote Mouse Server";
        private static readonly string Version = "1.0.0";
        private static readonly Mutex SingleInstanceMutex = new Mutex(true, "RemoteMouseServer_SingleInstance");
        
        private static IHost? _host;
        private static TrayApplication? _trayApp;
        private static CancellationTokenSource _cancellationTokenSource = new();
        private static ILogger<Program>? _logger;

        /// <summary>
        /// Point d'entrée principal de l'application
        /// </summary>
        [STAThread]
        static async Task<int> Main(string[] args)
        {
            try
            {
                // Vérifier qu'une seule instance est en cours d'exécution
                if (!SingleInstanceMutex.WaitOne(TimeSpan.Zero, true))
                {
                    MessageBox.Show(
                        "Remote Mouse Server is already running.",
                        "Application Already Running",
                        MessageBoxButtons.OK,
                        MessageBoxIcon.Information);
                    return 1;
                }

                // Configuration de l'application Windows Forms
                Application.EnableVisualStyles();
                Application.SetCompatibleTextRenderingDefault(false);
                Application.SetHighDpiMode(HighDpiMode.SystemAware);

                // Gestionnaire d'exceptions globales
                Application.SetUnhandledExceptionMode(UnhandledExceptionMode.CatchException);
                Application.ThreadException += OnThreadException;
                AppDomain.CurrentDomain.UnhandledException += OnUnhandledException;

                // Construire et démarrer l'host
                _host = CreateHostBuilder(args).Build();
                
                // Obtenir le logger
                _logger = _host.Services.GetRequiredService<ILogger<Program>>();
                _logger.LogInformation("Starting {AppName} v{Version}", AppName, Version);

                // Initialiser l'application tray
                _trayApp = _host.Services.GetRequiredService<TrayApplication>();
                _trayApp.Initialize();

                // Démarrer les services en arrière-plan
                var hostTask = _host.RunAsync(_cancellationTokenSource.Token);

                // Démarrer l'interface tray sur le thread principal
                _logger.LogInformation("Application started successfully. Running in system tray.");
                Application.Run(_trayApp);

                // Arrêter les services quand l'application se ferme
                _cancellationTokenSource.Cancel();
                await hostTask;

                _logger.LogInformation("Application shut down gracefully");
                return 0;
            }
            catch (Exception ex)
            {
                var message = $"Fatal error during startup: {ex.Message}";
                
                if (_logger != null)
                    _logger.LogCritical(ex, "Fatal error during startup");
                else
                    Console.WriteLine(message);

                MessageBox.Show(
                    message,
                    "Fatal Error",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Error);

                return -1;
            }
            finally
            {
                SingleInstanceMutex.ReleaseMutex();
                SingleInstanceMutex.Dispose();
                _host?.Dispose();
                _cancellationTokenSource.Dispose();
            }
        }

        /// <summary>
        /// Crée et configure l'host de l'application
        /// </summary>
        private static IHostBuilder CreateHostBuilder(string[] args) =>
            Host.CreateDefaultBuilder(args)
                .UseWindowsService() // Support pour l'exécution en tant que service Windows
                .ConfigureAppConfiguration((context, config) =>
                {
                    // Configuration de base
                    config.SetBasePath(Directory.GetCurrentDirectory());
                    config.AddJsonFile("appsettings.json", optional: false, reloadOnChange: true);
                    config.AddJsonFile($"appsettings.{context.HostingEnvironment.EnvironmentName}.json", 
                                     optional: true, reloadOnChange: true);
                    config.AddCommandLine(args);
                    config.AddEnvironmentVariables("REMOTEMOUSE_");
                })
                .ConfigureLogging((context, logging) =>
                {
                    logging.ClearProviders();
                    
                    // Logger personnalisé pour fichiers
                    logging.AddProvider(new FileLoggerProvider(
                        Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "Logs")));
                    
                    // Logger console en mode debug
                    if (context.HostingEnvironment.IsDevelopment())
                    {
                        logging.AddConsole();
                        logging.AddDebug();
                    }
                    
                    // Logger Windows Event Log
                    logging.AddEventLog(settings =>
                    {
                        settings.SourceName = AppName;
                    });
                })
                .ConfigureServices((context, services) =>
                {
                    // Configuration
                    services.Configure<AppSettings>(context.Configuration.GetSection("AppSettings"));
                    
                    // Services principaux
                    services.AddSingleton<WebSocketServer>();
                    services.AddSingleton<InputController>();
                    services.AddSingleton<AuthManager>();
                    services.AddSingleton<TrayApplication>();
                    
                    // Services hébergés
                    services.AddHostedService<WebSocketHostedService>();
                    services.AddHostedService<NetworkDiscoveryService>();
                    
                    // Autres services
                    services.AddSingleton<IConfiguration>(context.Configuration);
                });

        /// <summary>
        /// Gestionnaire d'exceptions du thread principal
        /// </summary>
        private static void OnThreadException(object sender, ThreadExceptionEventArgs e)
        {
            _logger?.LogError(e.Exception, "Unhandled thread exception occurred");
            
            var result = MessageBox.Show(
                $"An unexpected error occurred:\n{e.Exception.Message}\n\nDo you want to continue running?",
                "Unexpected Error",
                MessageBoxButtons.YesNo,
                MessageBoxIcon.Error);

            if (result == DialogResult.No)
            {
                Application.Exit();
            }
        }

        /// <summary>
        /// Gestionnaire d'exceptions non gérées du domaine d'application
        /// </summary>
        private static void OnUnhandledException(object sender, UnhandledExceptionEventArgs e)
        {
            var exception = e.ExceptionObject as Exception;
            _logger?.LogCritical(exception, "Unhandled domain exception occurred. Terminating: {IsTerminating}", 
                               e.IsTerminating);

            if (e.IsTerminating)
            {
                MessageBox.Show(
                    $"A fatal error occurred and the application must close:\n{exception?.Message}",
                    "Fatal Error",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Error);
            }
        }
    }

    /// <summary>
    /// Service hébergé pour le serveur WebSocket
    /// </summary>
    public class WebSocketHostedService : BackgroundService
    {
        private readonly WebSocketServer _webSocketServer;
        private readonly ILogger<WebSocketHostedService> _logger;
        private readonly AppSettings _settings;

        public WebSocketHostedService(
            WebSocketServer webSocketServer,
            ILogger<WebSocketHostedService> logger,
            Microsoft.Extensions.Options.IOptions<AppSettings> settings)
        {
            _webSocketServer = webSocketServer;
            _logger = logger;
            _settings = settings.Value;
        }

        protected override async Task ExecuteAsync(CancellationToken stoppingToken)
        {
            try
            {
                _logger.LogInformation("Starting WebSocket server on port {Port}", _settings.Port);
                
                await _webSocketServer.StartAsync(_settings.Port, stoppingToken);
                
                _logger.LogInformation("WebSocket server started successfully");
                
                // Attendre l'arrêt
                await Task.Delay(Timeout.Infinite, stoppingToken);
            }
            catch (OperationCanceledException)
            {
                _logger.LogInformation("WebSocket server stopping due to cancellation");
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error in WebSocket server");
                throw;
            }
            finally
            {
                _logger.LogInformation("Stopping WebSocket server");
                await _webSocketServer.StopAsync();
            }
        }
    }

    /// <summary>
    /// Service hébergé pour la découverte réseau
    /// </summary>
    public class NetworkDiscoveryService : BackgroundService
    {
        private readonly ILogger<NetworkDiscoveryService> _logger;
        private readonly AppSettings _settings;

        public NetworkDiscoveryService(
            ILogger<NetworkDiscoveryService> logger,
            Microsoft.Extensions.Options.IOptions<AppSettings> settings)
        {
            _logger = logger;
            _settings = settings.Value;
        }

        protected override async Task ExecuteAsync(CancellationToken stoppingToken)
        {
            if (!_settings.EnableNetworkDiscovery)
            {
                _logger.LogInformation("Network discovery is disabled");
                return;
            }

            try
            {
                _logger.LogInformation("Starting network discovery service");
                
                // TODO: Implémenter la publication mDNS/Bonjour
                // Publier le service _remotemouse._tcp.local avec les informations du serveur
                
                await Task.Delay(Timeout.Infinite, stoppingToken);
            }
            catch (OperationCanceledException)
            {
                _logger.LogInformation("Network discovery service stopping");
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error in network discovery service");
            }
        }
    }
}
