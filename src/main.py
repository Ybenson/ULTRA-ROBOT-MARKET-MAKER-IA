#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script principal pour ULTRA-ROBOT MARKET MAKER IA.

Ce script est le point d'entrée de l'application et coordonne
tous les composants du bot de market making.
"""

import os
import sys
import time
import argparse
import yaml
import ccxt
import threading
from pathlib import Path
from typing import Dict, Any, List
from loguru import logger
import dotenv

# Importer les composants du bot
from src.data.market_data_manager import MarketDataManager
from src.exchanges.binance_exchange import BinanceExchange
from src.strategies.statistical_arbitrage_strategy import StatisticalArbitrageStrategy
from src.monitoring.monitor import Monitor
from src.core.engine import Engine


def load_config(config_path: str) -> Dict[str, Any]:
    """
    Charge la configuration à partir d'un fichier YAML.
    
    Args:
        config_path: Chemin vers le fichier de configuration.
        
    Returns:
        Dictionnaire de configuration.
    """
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        
        logger.info(f"Configuration chargée depuis {config_path}")
        return config
    except Exception as e:
        logger.error(f"Erreur lors du chargement de la configuration: {str(e)}")
        sys.exit(1)


def setup_logging(config: Dict[str, Any]):
    """
    Configure la journalisation.
    
    Args:
        config: Configuration de la journalisation.
    """
    log_config = config.get("logging", {})
    log_level = log_config.get("level", "INFO")
    log_file = log_config.get("file", "logs/ultra_robot.log")
    
    # Créer le répertoire des logs s'il n'existe pas
    log_dir = os.path.dirname(log_file)
    os.makedirs(log_dir, exist_ok=True)
    
    # Configurer la journalisation
    logger.remove()  # Supprimer la configuration par défaut
    
    # Ajouter la sortie vers la console
    logger.add(sys.stderr, level=log_level)
    
    # Ajouter la sortie vers un fichier
    logger.add(
        log_file,
        level=log_level,
        rotation="10 MB",
        compression="zip",
        retention="1 week"
    )
    
    logger.info(f"Journalisation configurée avec le niveau {log_level}")


def initialize_exchanges(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Initialise les connexions aux exchanges.
    
    Args:
        config: Configuration des exchanges.
        
    Returns:
        Dictionnaire des connexions aux exchanges.
    """
    exchanges = {}
    exchange_configs = config.get("exchanges", {})
    
    for exchange_id, exchange_config in exchange_configs.items():
        try:
            if exchange_id == "binance":
                # Récupérer les clés API depuis les variables d'environnement
                api_key = os.getenv("BINANCE_API_KEY")
                api_secret = os.getenv("BINANCE_API_SECRET")
                
                if not api_key or not api_secret:
                    logger.warning(f"Clés API manquantes pour {exchange_id}, utilisation en mode lecture seule")
                
                # Créer la connexion à l'exchange
                exchange = BinanceExchange(
                    api_key=api_key,
                    api_secret=api_secret,
                    config=exchange_config
                )
                
                exchanges[exchange_id] = exchange
                logger.info(f"Connexion à {exchange_id} initialisée")
            else:
                logger.warning(f"Exchange non supporté: {exchange_id}")
        
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de {exchange_id}: {str(e)}")
    
    return exchanges


def initialize_strategies(config: Dict[str, Any], market_data_manager: MarketDataManager) -> List[Any]:
    """
    Initialise les stratégies de trading.
    
    Args:
        config: Configuration des stratégies.
        market_data_manager: Gestionnaire de données de marché.
        
    Returns:
        Liste des stratégies initialisées.
    """
    strategies = []
    strategy_configs = config.get("strategies", {})
    
    for strategy_type, strategy_config in strategy_configs.items():
        try:
            if not strategy_config.get("enabled", False):
                logger.info(f"Stratégie {strategy_type} désactivée, ignorée")
                continue
            
            if strategy_type == "statistical_arbitrage":
                # Créer la stratégie d'arbitrage statistique
                strategy = StatisticalArbitrageStrategy(
                    config=strategy_config,
                    market_data_manager=market_data_manager
                )
                
                strategies.append(strategy)
                logger.info(f"Stratégie {strategy_type} initialisée")
            else:
                logger.warning(f"Type de stratégie non supporté: {strategy_type}")
        
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de la stratégie {strategy_type}: {str(e)}")
    
    return strategies


def main():
    """
    Fonction principale.
    """
    # Analyser les arguments de la ligne de commande
    parser = argparse.ArgumentParser(description="ULTRA-ROBOT MARKET MAKER IA")
    parser.add_argument(
        "--config",
        type=str,
        default="config/default.yaml",
        help="Chemin vers le fichier de configuration"
    )
    parser.add_argument(
        "--env",
        type=str,
        default=".env",
        help="Chemin vers le fichier .env"
    )
    args = parser.parse_args()
    
    # Charger les variables d'environnement
    dotenv.load_dotenv(args.env)
    
    # Charger la configuration
    config = load_config(args.config)
    
    # Configurer la journalisation
    setup_logging(config)
    
    logger.info("Démarrage d'ULTRA-ROBOT MARKET MAKER IA...")
    
    try:
        # Initialiser les connexions aux exchanges
        exchanges = initialize_exchanges(config)
        
        if not exchanges:
            logger.error("Aucun exchange initialisé, arrêt du programme")
            sys.exit(1)
        
        # Initialiser le gestionnaire de données de marché
        market_data_manager = MarketDataManager(
            exchanges=exchanges,
            config=config.get("market_data", {})
        )
        
        # Initialiser les stratégies
        strategies = initialize_strategies(config, market_data_manager)
        
        if not strategies:
            logger.warning("Aucune stratégie initialisée")
        
        # Initialiser le moniteur
        monitor = Monitor(config=config.get("monitoring", {}))
        
        # Initialiser le moteur principal
        engine = Engine(
            config=config.get("engine", {}),
            exchanges=exchanges,
            market_data_manager=market_data_manager,
            strategies=strategies,
            monitor=monitor
        )
        
        # Démarrer le gestionnaire de données
        market_data_manager.start()
        logger.info("Gestionnaire de données démarré")
        
        # Démarrer le moniteur
        monitor.start()
        logger.info("Moniteur démarré")
        
        # Démarrer les stratégies
        for strategy in strategies:
            strategy.start()
            logger.info(f"Stratégie {strategy.get_name()} démarrée")
        
        # Démarrer le moteur principal
        engine.start()
        logger.info("Moteur principal démarré")
        
        # Boucle principale
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Interruption utilisateur, arrêt du programme...")
        
        # Arrêter le moteur principal
        engine.stop()
        logger.info("Moteur principal arrêté")
        
        # Arrêter les stratégies
        for strategy in strategies:
            strategy.stop()
            logger.info(f"Stratégie {strategy.get_name()} arrêtée")
        
        # Arrêter le moniteur
        monitor.stop()
        logger.info("Moniteur arrêté")
        
        # Arrêter le gestionnaire de données
        market_data_manager.stop()
        logger.info("Gestionnaire de données arrêté")
        
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution: {str(e)}")
        sys.exit(1)
    
    logger.info("ULTRA-ROBOT MARKET MAKER IA arrêté avec succès")


if __name__ == "__main__":
    main()
