#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ULTRA-ROBOT MARKET MAKER IA
---------------------------
Point d'entrée principal pour le bot de market making ultra-puissant avec IA.

Ce script initialise et lance le bot avec les configurations spécifiées.
"""

import argparse
import os
import sys
import logging
import yaml
from pathlib import Path
from loguru import logger
from typing import Dict, Any, List

# Importer les composants principaux du bot
from src.core.engine import MarketMakingEngine
from src.exchanges.binance_exchange import BinanceExchange
from src.market_data.market_data_manager import MarketDataManager
from src.monitoring.monitor import Monitor
from src.strategies.market_making_strategy import MarketMakingStrategy
from src.strategies.adaptive_market_making_strategy import AdaptiveMarketMakingStrategy
from src.strategies.statistical_arbitrage_strategy import StatisticalArbitrageStrategy


def parse_arguments():
    """Parse les arguments de ligne de commande."""
    parser = argparse.ArgumentParser(description="ULTRA-ROBOT MARKET MAKER IA")
    parser.add_argument(
        "--config",
        type=str,
        default="src/config/default.yaml",
        help="Chemin vers le fichier de configuration"
    )
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Niveau de journalisation"
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["live", "backtest", "paper", "simulation"],
        default="simulation",
        help="Mode d'exécution du bot"
    )
    return parser.parse_args()


def load_config(config_path: str = "src/config/default.yaml") -> Dict[str, Any]:
    """
    Charge la configuration depuis un fichier YAML.
    
    Args:
        config_path: Chemin vers le fichier de configuration
        
    Returns:
        Configuration chargée
    """
    try:
        with open(config_path, 'r') as f:
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
        config: Configuration du bot
    """
    log_level = config.get("general", {}).get("log_level", "INFO")
    logger.remove()
    logger.add(sys.stderr, level=log_level)
    logger.add("logs/ultra_robot_{time}.log", rotation="1 day", retention="30 days")
    logger.info(f"Journalisation configurée avec le niveau {log_level}")


def initialize_exchanges(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Initialise les connexions aux exchanges.
    
    Args:
        config: Configuration du bot
        
    Returns:
        Dictionnaire des connexions aux exchanges
    """
    exchanges = {}
    enabled_markets = config.get("markets", {}).get("enabled_markets", [])
    
    for market in enabled_markets:
        market_id = market.get("id")
        if market_id == "binance":
            exchange = BinanceExchange(config=market)
            exchanges[market_id] = exchange
            logger.info(f"Connexion à {market_id} initialisée")
    
    return exchanges


def initialize_market_data_manager(config: Dict[str, Any], exchanges: Dict[str, Any]) -> MarketDataManager:
    """
    Initialise le gestionnaire de données de marché.
    
    Args:
        config: Configuration du bot
        exchanges: Dictionnaire des connexions aux exchanges
        
    Returns:
        Gestionnaire de données de marché
    """
    symbols = config.get("markets", {}).get("symbols", [])
    if not symbols:
        logger.error("Aucun symbole configuré")
        return None
        
    market_data_config = {
        "symbols": symbols,
        "cache_enabled": config.get("data", {}).get("cache_enabled", True),
        "cache_expiry": config.get("data", {}).get("cache_expiry_seconds", 60),
        "use_websockets": config.get("data", {}).get("use_websockets", True)
    }
    
    return MarketDataManager(config=market_data_config, exchanges=exchanges)


def initialize_strategies(config: Dict[str, Any], market_data_manager: MarketDataManager) -> Dict[str, Any]:
    """
    Initialise les stratégies de trading.
    
    Args:
        config: Configuration du bot
        market_data_manager: Gestionnaire de données de marché
        
    Returns:
        Dictionnaire des stratégies
    """
    strategies = {}
    enabled_strategies = config.get("strategies", {}).get("enabled_strategies", [])
    
    for strategy_config in enabled_strategies:
        try:
            strategy_id = strategy_config.get("id")
            strategy_type = strategy_config.get("type")
            
            if not strategy_id or not strategy_type:
                logger.error(f"Configuration de stratégie invalide: {strategy_config}")
                continue
            
            strategy = None
            if strategy_type == "market_making":
                strategy = MarketMakingStrategy(
                    strategy_id=strategy_id,
                    config=strategy_config,
                    market_data_manager=market_data_manager
                )
            elif strategy_type == "adaptive_market_making":
                strategy = AdaptiveMarketMakingStrategy(
                    strategy_id=strategy_id,
                    config=strategy_config,
                    market_data_manager=market_data_manager
                )
            elif strategy_type == "statistical_arbitrage":
                strategy = StatisticalArbitrageStrategy(
                    strategy_id=strategy_id,
                    config=strategy_config,
                    market_data_manager=market_data_manager
                )
            
            if strategy:
                strategies[strategy_id] = strategy
                logger.info(f"Stratégie {strategy_id} initialisée")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de la stratégie {strategy_id}: {str(e)}")
            
    return strategies


def main():
    """Point d'entrée principal du programme."""
    try:
        args = parse_arguments()
        
        # Charger la configuration
        config = load_config(args.config)
        setup_logging(config)
        
        logger.info("Démarrage d'ULTRA-ROBOT MARKET MAKER IA...")
        
        # Initialiser les exchanges
        exchanges = initialize_exchanges(config)
        if not exchanges:
            logger.error("Aucun exchange initialisé")
            return
            
        # Initialiser le gestionnaire de données
        market_data_manager = initialize_market_data_manager(config, exchanges)
        if not market_data_manager:
            logger.error("Échec de l'initialisation du gestionnaire de données")
            return
            
        # Initialiser les stratégies
        strategies = initialize_strategies(config, market_data_manager)
        if not strategies:
            logger.error("Aucune stratégie initialisée")
            return
            
        # Initialiser le moniteur
        monitor = Monitor(config.get("monitoring", {}))
        
        # Créer et démarrer le moteur
        engine_config = {
            "mode": config.get("general", {}).get("mode", "simulation"),
            "exchanges": exchanges,
            "strategies": strategies,
            "market_data_manager": market_data_manager,
            "monitor": monitor,
            "risk_config": config.get("risk_management", {}),
            "execution_config": config.get("execution", {})
        }
        
        engine = MarketMakingEngine(config=engine_config)
        engine.start()
        
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution: {str(e)}")
        raise
    finally:
        # Nettoyage
        if 'market_data_manager' in locals():
            market_data_manager.stop()
        if 'monitor' in locals():
            monitor.stop()
        if 'engine' in locals():
            engine.stop()


if __name__ == "__main__":
    main()