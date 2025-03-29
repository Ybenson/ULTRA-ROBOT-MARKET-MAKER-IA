#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script d'initialisation pour ULTRA-ROBOT MARKET MAKER IA.

Ce script initialise tous les composants nécessaires au fonctionnement du bot
et configure l'environnement d'exécution.
"""

import os
import sys
import yaml
import logging
import argparse
from pathlib import Path
from dotenv import load_dotenv
from loguru import logger

# Importer les composants du bot
from src.core.engine import MarketMakingEngine
from src.data.market_data_manager import MarketDataManager
from src.exchanges.binance_exchange import BinanceExchange
from src.strategies.market_making_strategy import MarketMakingStrategy
from src.strategies.adaptive_market_making_strategy import AdaptiveMarketMakingStrategy
from src.strategies.statistical_arbitrage_strategy import StatisticalArbitrageStrategy
from src.strategies.combined_strategy import CombinedStrategy
from src.risk_management.risk_manager import RiskManager
from src.execution.order_executor import OrderExecutor
from src.monitoring.monitor import Monitor
from src.ai.optimizer import AIOptimizer


def setup_logging(log_level="INFO", log_file=None):
    """
    Configure la journalisation.
    
    Args:
        log_level: Niveau de journalisation.
        log_file: Fichier de journalisation.
    """
    # Supprimer les gestionnaires par défaut
    logger.remove()
    
    # Ajouter un gestionnaire pour la sortie standard
    logger.add(sys.stderr, level=log_level)
    
    # Ajouter un gestionnaire pour le fichier de journalisation
    if log_file:
        logger.add(log_file, rotation="10 MB", retention="1 week", level=log_level)
    
    # Configurer la journalisation pour les bibliothèques tierces
    logging.basicConfig(level=getattr(logging, log_level))


def load_config(config_file):
    """
    Charge la configuration à partir d'un fichier YAML.
    
    Args:
        config_file: Chemin vers le fichier de configuration.
        
    Returns:
        Configuration chargée.
    """
    try:
        with open(config_file, "r") as f:
            config = yaml.safe_load(f)
        
        logger.info(f"Configuration chargée depuis {config_file}")
        return config
    
    except Exception as e:
        logger.error(f"Erreur lors du chargement de la configuration: {str(e)}")
        sys.exit(1)


def initialize_exchanges(config):
    """
    Initialise les connecteurs d'échange.
    
    Args:
        config: Configuration du bot.
        
    Returns:
        Dictionnaire des connecteurs d'échange.
    """
    exchanges = {}
    
    try:
        # Récupérer la liste des marchés activés
        enabled_markets = config.get("markets", {}).get("enabled_markets", [])
        
        for market in enabled_markets:
            market_id = market.get("id")
            market_type = market.get("type")
            
            # Initialiser le connecteur en fonction du type de marché
            if market_type == "crypto":
                if market_id == "binance":
                    # Récupérer les clés API depuis les variables d'environnement
                    api_key_env = market.get("api_key_env", "BINANCE_API_KEY")
                    api_secret_env = market.get("api_secret_env", "BINANCE_API_SECRET")
                    
                    api_key = os.getenv(api_key_env)
                    api_secret = os.getenv(api_secret_env)
                    
                    if not api_key or not api_secret:
                        logger.warning(f"Clés API manquantes pour {market_id}. Le bot fonctionnera en mode simulation.")
                    
                    # Initialiser le connecteur Binance
                    testnet = market.get("testnet", True)
                    exchange = BinanceExchange(
                        api_key=api_key,
                        api_secret=api_secret,
                        testnet=testnet
                    )
                    
                    exchanges[market_id] = exchange
                    logger.info(f"Connecteur {market_id} initialisé")
            
            # Ajouter d'autres types de marchés ici (actions, forex, etc.)
    
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation des connecteurs d'échange: {str(e)}")
    
    return exchanges


def initialize_strategies(config, market_data_manager, order_executor, risk_manager):
    """
    Initialise les stratégies de trading.
    
    Args:
        config: Configuration du bot.
        market_data_manager: Gestionnaire de données de marché.
        order_executor: Exécuteur d'ordres.
        risk_manager: Gestionnaire de risques.
        
    Returns:
        Liste des stratégies initialisées.
    """
    strategies = []
    
    try:
        # Récupérer la liste des stratégies activées
        enabled_strategies = config.get("strategies", {}).get("enabled_strategies", [])
        
        for strategy_config in enabled_strategies:
            strategy_id = strategy_config.get("id")
            strategy_type = strategy_config.get("type")
            
            # Initialiser la stratégie en fonction du type
            if strategy_type == "market_making":
                strategy = MarketMakingStrategy(
                    strategy_id=strategy_id,
                    market_data_manager=market_data_manager,
                    order_executor=order_executor,
                    risk_manager=risk_manager,
                    config=strategy_config
                )
                
                strategies.append(strategy)
                logger.info(f"Stratégie de market making {strategy_id} initialisée")
            
            elif strategy_type == "adaptive_market_making":
                strategy = AdaptiveMarketMakingStrategy(
                    strategy_id=strategy_id,
                    market_data_manager=market_data_manager,
                    order_executor=order_executor,
                    risk_manager=risk_manager,
                    config=strategy_config
                )
                
                strategies.append(strategy)
                logger.info(f"Stratégie de market making adaptative {strategy_id} initialisée")
            
            elif strategy_type == "statistical_arbitrage":
                strategy = StatisticalArbitrageStrategy(
                    config=strategy_config,
                    market_data_manager=market_data_manager
                )
                
                strategies.append(strategy)
                logger.info(f"Stratégie d'arbitrage statistique {strategy_id} initialisée")
            
            elif strategy_type == "combined":
                # Initialiser la stratégie combinée
                combined_strategy = CombinedStrategy(
                    config=strategy_config,
                    market_data_manager=market_data_manager
                )
                
                # Ajouter les sous-stratégies
                sub_strategies = strategy_config.get("sub_strategies", [])
                
                for sub_strategy_id in sub_strategies:
                    # Rechercher la sous-stratégie dans la liste des stratégies déjà initialisées
                    for strategy in strategies:
                        if strategy.get_id() == sub_strategy_id:
                            weight = strategy_config.get("weights", {}).get(sub_strategy_id, 1.0)
                            combined_strategy.add_strategy(strategy, weight)
                            logger.info(f"Sous-stratégie {sub_strategy_id} ajoutée à la stratégie combinée {strategy_id} avec un poids de {weight}")
                
                strategies.append(combined_strategy)
                logger.info(f"Stratégie combinée {strategy_id} initialisée")
        
        # Initialiser l'optimiseur d'IA si configuré
        ai_optimizer_config = config.get("ai", {}).get("optimizer", {})
        
        if ai_optimizer_config.get("enabled", False):
            ai_optimizer = AIOptimizer(
                config=ai_optimizer_config,
                strategies=strategies,
                market_data_manager=market_data_manager
            )
            
            logger.info("Optimiseur d'IA initialisé")
    
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation des stratégies: {str(e)}")
    
    return strategies


def main():
    """
    Fonction principale.
    """
    # Analyser les arguments de la ligne de commande
    parser = argparse.ArgumentParser(description="ULTRA-ROBOT MARKET MAKER IA")
    parser.add_argument("--config", type=str, default="config/default.yaml", help="Chemin vers le fichier de configuration")
    parser.add_argument("--log-level", type=str, default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], help="Niveau de journalisation")
    parser.add_argument("--log-file", type=str, help="Fichier de journalisation")
    parser.add_argument("--env-file", type=str, default=".env", help="Fichier d'environnement")
    args = parser.parse_args()
    
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
    
    # Initialiser les connecteurs d'échange
    exchanges = initialize_exchanges(config)
    
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
    
    # Initialiser le moteur de market making
    engine = MarketMakingEngine(
        config=config,
        market_data_manager=market_data_manager,
        order_executor=order_executor,
        risk_manager=risk_manager,
        monitor=monitor,
        strategies=strategies
    )
    
    # Démarrer le bot
    try:
        logger.info("Démarrage d'ULTRA-ROBOT MARKET MAKER IA...")
        engine.start()
    
    except KeyboardInterrupt:
        logger.info("Arrêt d'ULTRA-ROBOT MARKET MAKER IA...")
        engine.stop()
    
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution d'ULTRA-ROBOT MARKET MAKER IA: {str(e)}")
        engine.stop()
        sys.exit(1)


if __name__ == "__main__":
    main()
