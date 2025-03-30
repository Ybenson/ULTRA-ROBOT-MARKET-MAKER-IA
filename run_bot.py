#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script de lancement pour ULTRA-ROBOT MARKET MAKER IA.

Ce script est le point d'entrée principal pour démarrer le bot de market making
en environnement de production.
"""

import os
import sys
import argparse
import time
from pathlib import Path
from dotenv import load_dotenv
from loguru import logger

# Ajouter le répertoire parent au chemin de recherche Python
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Importer le script d'initialisation
from src.init import load_config, setup_logging, initialize_exchanges, initialize_strategies

# Importer les composants du bot
from src.core.engine import MarketMakingEngine
from src.market_data.market_data_manager import MarketDataManager
from src.risk_management.risk_manager import RiskManager
from src.execution.order_executor import OrderExecutor
from src.monitoring.monitor import Monitor
from src.ai.optimizer import AIOptimizer


def parse_arguments():
    """
    Analyse les arguments de la ligne de commande.
    
    Returns:
        Arguments analysés.
    """
    parser = argparse.ArgumentParser(description="ULTRA-ROBOT MARKET MAKER IA")
    parser.add_argument("--config", type=str, default="src/config/default.yaml", help="Chemin vers le fichier de configuration")
    parser.add_argument("--mode", type=str, default="simulation", choices=["live", "simulation", "backtest", "paper"], help="Mode d'exécution")
    parser.add_argument("--log-level", type=str, default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], help="Niveau de journalisation")
    parser.add_argument("--log-file", type=str, default="logs/ultra_robot.log", help="Fichier de journalisation")
    parser.add_argument("--env-file", type=str, default="src/config/.env", help="Fichier d'environnement")
    parser.add_argument("--dashboard", action="store_true", help="Activer le tableau de bord")
    parser.add_argument("--dashboard-port", type=int, default=8050, help="Port du tableau de bord")
    parser.add_argument("--symbols", type=str, nargs="+", help="Symboles à trader (remplace ceux de la configuration)")
    parser.add_argument("--strategies", type=str, nargs="+", help="Stratégies à utiliser (remplace celles de la configuration)")
    parser.add_argument("--no-ai", action="store_true", help="Désactiver l'optimisation par IA")
    return parser.parse_args()


def setup_environment(args):
    """
    Configure l'environnement d'exécution.
    
    Args:
        args: Arguments de la ligne de commande.
        
    Returns:
        Configuration chargée.
    """
    # Créer les répertoires nécessaires
    os.makedirs("logs", exist_ok=True)
    os.makedirs("data", exist_ok=True)
    os.makedirs("models", exist_ok=True)
    
    # Charger les variables d'environnement
    env_path = Path(args.env_file)
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
        logger.info(f"Variables d'environnement chargées depuis {env_path}")
    else:
        logger.warning(f"Fichier d'environnement {env_path} non trouvé. Utilisation des variables d'environnement système.")
    
    # Configurer la journalisation
    setup_logging(log_level=args.log_level, log_file=args.log_file)
    
    # Charger la configuration
    config = load_config(args.config)
    
    # Remplacer les paramètres par les arguments de la ligne de commande
    if args.mode:
        config["general"]["mode"] = args.mode
    
    if args.dashboard:
        config["monitoring"]["dashboard_enabled"] = True
        if args.dashboard_port:
            config["monitoring"]["dashboard_port"] = args.dashboard_port
    
    if args.symbols:
        config["markets"]["symbols"] = args.symbols
    
    if args.strategies:
        # Filtrer les stratégies activées
        enabled_strategies = []
        for strategy_config in config["strategies"]["enabled_strategies"]:
            if isinstance(strategy_config, dict) and strategy_config.get("id") in args.strategies:
                enabled_strategies.append(strategy_config)
            elif isinstance(strategy_config, str) and strategy_config in args.strategies:
                enabled_strategies.append(strategy_config)
        
        config["strategies"]["enabled_strategies"] = enabled_strategies
    
    if args.no_ai:
        config["ai"]["enabled"] = False
    
    return config


def main():
    """
    Fonction principale.
    """
    # Analyser les arguments de la ligne de commande
    args = parse_arguments()
    
    # Configurer l'environnement
    config = setup_environment(args)
    
    # Afficher le mode d'exécution
    mode = config["general"]["mode"]
    logger.info(f"Démarrage d'ULTRA-ROBOT MARKET MAKER IA en mode {mode}")
    
    # Initialiser les connecteurs d'échange
    exchanges = initialize_exchanges(config)
    
    # Vérifier si au moins un exchange est disponible
    if not exchanges:
        logger.error("Aucun exchange disponible. Arrêt du bot.")
        sys.exit(1)
    
    # Initialiser le gestionnaire de données de marché
    market_data_manager = MarketDataManager(
        exchanges=exchanges,
        config=config.get("data", {})
    )
    
    # Initialiser le gestionnaire de risques
    risk_manager = RiskManager(
        config=config.get("risk_management", {}),
        market_data_manager=market_data_manager
    )
    
    # Initialiser l'exécuteur d'ordres
    order_executor = OrderExecutor(
        exchanges=exchanges,
        config=config.get("execution", {}),
        risk_manager=risk_manager
    )
    
    # Initialiser le moniteur
    monitor = Monitor(
        config=config.get("monitoring", {})
    )
    
    # Initialiser les stratégies
    strategies = initialize_strategies(
        config=config,
        market_data_manager=market_data_manager,
        order_executor=order_executor,
        risk_manager=risk_manager
    )
    
    # Vérifier si au moins une stratégie est disponible
    if not strategies:
        logger.error("Aucune stratégie disponible. Arrêt du bot.")
        sys.exit(1)
    
    # Initialiser l'optimiseur IA si activé
    ai_optimizer = None
    if config["ai"]["enabled"]:
        ai_optimizer = AIOptimizer(
            config=config.get("ai", {}),
            market_data_manager=market_data_manager,
            strategies={s.get_id(): s for s in strategies}
        )
    
    # Initialiser le moteur de market making
    engine = MarketMakingEngine(
        config=config,
        mode=mode
    )
    
    # Initialiser le moteur
    engine.initialize()
    
    # Démarrer le bot
    try:
        logger.info("Démarrage du bot...")
        
        # Démarrer le gestionnaire de données de marché
        market_data_manager.start()
        logger.info("Gestionnaire de données de marché démarré")
        
        # Démarrer le moniteur
        if config["monitoring"]["dashboard_enabled"]:
            monitor.start()
            logger.info(f"Tableau de bord démarré sur le port {config['monitoring']['dashboard_port']}")
        
        # Démarrer les stratégies
        for strategy in strategies:
            strategy.start()
            logger.info(f"Stratégie {strategy.get_id()} démarrée")
        
        # Démarrer le moteur
        engine.start()
        logger.info("Moteur de market making démarré")
        
        # Boucle principale
        try:
            while True:
                # Optimiser les stratégies si l'optimiseur IA est activé
                if ai_optimizer:
                    ai_optimizer.optimize()
                
                # Mettre à jour le moniteur
                if monitor.running:
                    monitor.update_metrics()
                
                # Attendre
                time.sleep(1)
        
        except KeyboardInterrupt:
            logger.info("Interruption utilisateur. Arrêt du bot...")
    
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution du bot: {str(e)}")
    
    finally:
        # Arrêter le bot proprement
        logger.info("Arrêt du bot...")
        
        # Arrêter le moteur
        engine.stop()
        logger.info("Moteur de market making arrêté")
        
        # Arrêter les stratégies
        for strategy in strategies:
            strategy.stop()
            logger.info(f"Stratégie {strategy.get_id()} arrêtée")
        
        # Arrêter le moniteur
        if monitor.running:
            monitor.stop()
            logger.info("Tableau de bord arrêté")
        
        # Arrêter le gestionnaire de données de marché
        market_data_manager.stop()
        logger.info("Gestionnaire de données de marché arrêté")
        
        logger.info("Bot arrêté avec succès")


if __name__ == "__main__":
    main()
