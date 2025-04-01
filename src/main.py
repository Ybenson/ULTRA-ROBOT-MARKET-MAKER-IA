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

# Ajout du chemin du projet au PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importer les composants du bot
from market_data.market_data_manager import MarketDataManager
from exchanges.binance_exchange import BinanceExchange
from strategies.statistical_arbitrage_strategy import StatisticalArbitrageStrategy
from strategies.market_making_strategy import MarketMakingStrategy
from strategies.adaptive_market_making_strategy import AdaptiveMarketMakingStrategy
from monitoring.monitor import Monitor
from core.engine import MarketMakingEngine


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
    enabled_markets = config.get("markets", {}).get("enabled_markets", [])
    
    for market in enabled_markets:
        try:
            market_id = market.get("id")
            if market_id == "binance":
                # Récupérer les clés API depuis les variables d'environnement
                api_key = os.getenv(market.get("api_key_env"))
                api_secret = os.getenv(market.get("api_secret_env"))
                
                if not api_key or not api_secret:
                    logger.warning(f"Clés API manquantes pour {market_id}, utilisation en mode lecture seule")
                
                # Créer la configuration de l'exchange
                exchange_config = {
                    "api_key": api_key,
                    "api_secret": api_secret,
                    "testnet": market.get("testnet", False)
                }
                
                # Créer la connexion à l'exchange
                exchange = BinanceExchange(config=exchange_config)
                
                exchanges[market_id] = exchange
                logger.info(f"Connexion à {market_id} initialisée")
            else:
                logger.warning(f"Exchange non supporté: {market_id}")
        
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de {market_id}: {str(e)}")
    
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
    enabled_strategies = config.get("strategies", {}).get("enabled_strategies", [])
    
    for strategy_config in enabled_strategies:
        try:
            strategy_type = strategy_config.get("type")
            strategy_id = strategy_config.get("strategy_id")
            
            if strategy_type == "market_making":
                strategy = MarketMakingStrategy(
                    strategy_id=strategy_id,
                    config=strategy_config,
                    market_data_manager=market_data_manager
                )
                strategies.append(strategy)
                logger.info(f"Stratégie {strategy_id} initialisée")
            
            elif strategy_type == "adaptive_market_making":
                strategy = AdaptiveMarketMakingStrategy(
                    strategy_id=strategy_id,
                    config=strategy_config,
                    market_data_manager=market_data_manager
                )
                strategies.append(strategy)
                logger.info(f"Stratégie {strategy_id} initialisée")
            
            elif strategy_type == "statistical_arbitrage":
                strategy = StatisticalArbitrageStrategy(
                    strategy_id=strategy_id,
                    config=strategy_config,
                    market_data_manager=market_data_manager
                )
                strategies.append(strategy)
                logger.info(f"Stratégie {strategy_id} initialisée")
            
            else:
                logger.warning(f"Type de stratégie non supporté: {strategy_type}")
        
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de la stratégie {strategy_id}: {str(e)}")
    
    return strategies


def main():
    """
    Fonction principale.
    """
    parser = argparse.ArgumentParser(description="ULTRA-ROBOT MARKET MAKER IA")
    parser.add_argument("--config", type=str, default="src/config/default.yaml", help="Chemin vers le fichier de configuration")
    args = parser.parse_args()
    
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
        
        # Récupérer la liste des symboles depuis la configuration
        symbols = config.get("markets", {}).get("symbols", [])
        if not symbols:
            logger.error("Aucun symbole configuré, arrêt du programme")
            sys.exit(1)
        
        # Initialiser le gestionnaire de données de marché
        market_data_config = config.get("market_data", {})
        market_data_config["symbols"] = symbols
        
        market_data_manager = MarketDataManager(
            config=market_data_config,
            exchanges=exchanges
        )
        
        # Initialiser les stratégies
        strategies = initialize_strategies(config, market_data_manager)
        
        if not strategies:
            logger.warning("Aucune stratégie initialisée")
        
        # Initialiser le moniteur
        monitor = Monitor(config=config.get("monitoring", {}))
        
        # Initialiser le moteur principal avec la configuration complète
        engine_config = config.copy()
        engine_config.update({
            "exchanges": exchanges,
            "strategies": strategies,
            "market_data_manager": market_data_manager,
            "monitor": monitor,
            "symbols": symbols
        })
        
        engine = MarketMakingEngine(
            config=engine_config,
            mode=config.get("general", {}).get("mode", "simulation")
        )
        
        # Démarrer le gestionnaire de données
        market_data_manager.start()
        
        # Démarrer le moniteur
        monitor.start()
        
        # Démarrer le moteur principal
        engine.start()
        
        # Attendre indéfiniment
        while True:
            time.sleep(1)
    
    except KeyboardInterrupt:
        logger.info("Arrêt demandé par l'utilisateur...")
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution: {str(e)}")
    finally:
        # Arrêter tous les composants
        if 'market_data_manager' in locals():
            market_data_manager.stop()
        if 'monitor' in locals():
            monitor.stop()
        if 'engine' in locals():
            engine.stop()
        
        logger.info("Arrêt du programme")


if __name__ == "__main__":
    main()
