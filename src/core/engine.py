#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Moteur principal de Market Making pour ULTRA-ROBOT MARKET MAKER IA.

Ce module contient le moteur central qui coordonne toutes les fonctionnalités
du bot de market making, y compris la gestion des stratégies, l'exécution des ordres,
la gestion des risques et l'optimisation par IA.
"""

import time
import threading
import asyncio
from typing import Dict, Any, List, Optional
from loguru import logger

from src.api.exchange_factory import ExchangeFactory
from src.strategies.strategy_factory import StrategyFactory
from src.risk_management.risk_manager import RiskManager
from src.execution.order_executor import OrderExecutor
from src.data.market_data_manager import MarketDataManager
from src.ai.optimizer import AIOptimizer


class MarketMakingEngine:
    """
    Moteur principal de Market Making qui coordonne toutes les fonctionnalités du bot.
    
    Cette classe est responsable de l'initialisation de tous les composants,
    de la coordination de leurs interactions et de l'exécution de la boucle principale
    du bot de market making.
    """
    
    def __init__(self, config: Dict[str, Any], mode: str = "simulation"):
        """
        Initialise le moteur de Market Making.
        
        Args:
            config: Configuration complète du bot.
            mode: Mode d'exécution ('live', 'backtest', 'paper', 'simulation').
        """
        self.config = config
        self.mode = mode
        self.running = False
        self.exchanges = {}
        self.strategies = {}
        self.symbols = []
        
        # Composants principaux
        self.exchange_factory = None
        self.strategy_factory = None
        self.risk_manager = None
        self.order_executor = None
        self.market_data_manager = None
        self.ai_optimizer = None
        
        # Threads et boucles d'événements
        self.main_thread = None
        self.event_loop = None
        
        logger.info(f"Moteur de Market Making initialisé en mode {mode}")
        
    def initialize(self):
        """
        Initialise tous les composants du bot.
        
        Cette méthode configure les connexions aux exchanges, les gestionnaires de données,
        les stratégies, le gestionnaire de risques, l'exécuteur d'ordres et l'optimiseur IA.
        """
        logger.info("Initialisation des composants du bot...")
        
        # Initialiser la factory d'exchanges
        self.exchange_factory = ExchangeFactory(self.config)
        
        # Créer les connexions aux exchanges
        for market_config in self.config["markets"]["enabled_markets"]:
            exchange_id = market_config if isinstance(market_config, str) else market_config["id"]
            exchange = self.exchange_factory.create_exchange(exchange_id, self.mode)
            self.exchanges[exchange_id] = exchange
            logger.info(f"Exchange initialisé: {exchange_id}")
        
        # Initialiser le gestionnaire de données de marché
        self.market_data_manager = MarketDataManager(
            exchanges=self.exchanges,
            config=self.config["data"]
        )
        
        # Initialiser le gestionnaire de risques
        self.risk_manager = RiskManager(
            config=self.config["risk_management"],
            market_data_manager=self.market_data_manager
        )
        
        # Initialiser l'exécuteur d'ordres
        self.order_executor = OrderExecutor(
            exchanges=self.exchanges,
            config=self.config["execution"],
            risk_manager=self.risk_manager
        )
        
        # Initialiser la factory de stratégies
        self.strategy_factory = StrategyFactory(
            market_data_manager=self.market_data_manager,
            order_executor=self.order_executor,
            risk_manager=self.risk_manager,
            config=self.config["strategies"]
        )
        
        # Créer les stratégies
        for strategy_config in self.config["strategies"]["enabled_strategies"]:
            strategy_id = strategy_config if isinstance(strategy_config, str) else strategy_config["id"]
            strategy = self.strategy_factory.create_strategy(strategy_id)
            self.strategies[strategy_id] = strategy
            logger.info(f"Stratégie initialisée: {strategy_id}")
        
        # Initialiser l'optimiseur IA si activé
        if self.config["ai"]["enabled"]:
            self.ai_optimizer = AIOptimizer(
                config=self.config["ai"],
                market_data_manager=self.market_data_manager,
                strategies=self.strategies
            )
            logger.info("Optimiseur IA initialisé")
        
        # Collecter tous les symboles à trader
        self.symbols = self._collect_trading_symbols()
        
        logger.info(f"Initialisation terminée. Prêt à trader sur {len(self.symbols)} symboles")
        
    def start(self):
        """
        Démarre le bot de market making.
        
        Cette méthode lance la boucle principale du bot dans un thread séparé
        et initialise les flux de données en temps réel.
        """
        if self.running:
            logger.warning("Le bot est déjà en cours d'exécution")
            return
        
        logger.info("Démarrage du bot de market making...")
        
        # Démarrer le gestionnaire de données de marché
        self.market_data_manager.start()
        
        # Créer une nouvelle boucle d'événements asyncio
        self.event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.event_loop)
        
        # Démarrer le thread principal
        self.running = True
        self.main_thread = threading.Thread(target=self._main_loop)
        self.main_thread.daemon = True
        self.main_thread.start()
        
        logger.info("Bot de market making démarré avec succès")
        
        # Si en mode interactif, attendre l'arrêt par l'utilisateur
        if not self.mode == "backtest":
            try:
                while self.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                self.stop()
        
    def stop(self):
        """
        Arrête le bot de market making.
        
        Cette méthode arrête proprement tous les composants du bot,
        annule les ordres en cours et ferme les connexions.
        """
        if not self.running:
            logger.warning("Le bot n'est pas en cours d'exécution")
            return
        
        logger.info("Arrêt du bot de market making...")
        
        # Marquer comme non exécuté
        self.running = False
        
        # Arrêter le gestionnaire de données de marché
        if self.market_data_manager:
            self.market_data_manager.stop()
        
        # Annuler tous les ordres en cours
        if self.order_executor:
            self.order_executor.cancel_all_orders()
        
        # Attendre que le thread principal se termine
        if self.main_thread and self.main_thread.is_alive():
            self.main_thread.join(timeout=10)
        
        # Fermer la boucle d'événements asyncio
        if self.event_loop:
            self.event_loop.stop()
            
        logger.info("Bot de market making arrêté avec succès")
        
    def _main_loop(self):
        """
        Boucle principale du bot de market making.
        
        Cette méthode exécute la logique principale du bot dans une boucle continue,
        y compris la mise à jour des stratégies, l'optimisation par IA et la surveillance.
        """
        logger.info("Démarrage de la boucle principale du bot")
        
        try:
            while self.running:
                # Mettre à jour les données de marché
                self.market_data_manager.update()
                
                # Exécuter les stratégies
                for strategy_id, strategy in self.strategies.items():
                    try:
                        strategy.execute()
                    except Exception as e:
                        logger.error(f"Erreur lors de l'exécution de la stratégie {strategy_id}: {str(e)}")
                
                # Exécuter l'optimiseur IA si activé
                if self.ai_optimizer and time.time() % self.config["ai"]["update_frequency_seconds"] < 1:
                    try:
                        self.ai_optimizer.optimize()
                        logger.debug("Optimisation IA exécutée")
                    except Exception as e:
                        logger.error(f"Erreur lors de l'optimisation IA: {str(e)}")
                
                # Vérifier l'état de santé du système
                self._check_system_health()
                
                # Pause pour éviter une utilisation excessive du CPU
                time.sleep(0.1)
                
        except Exception as e:
            logger.exception(f"Erreur critique dans la boucle principale: {str(e)}")
            self.stop()
    
    def _collect_trading_symbols(self) -> List[str]:
        """
        Collecte tous les symboles à trader à partir de la configuration.
        
        Returns:
            Liste des symboles à trader.
        """
        symbols = []
        
        # Collecter les symboles depuis la configuration
        if "symbols" in self.config["markets"]:
            symbols.extend(self.config["markets"]["symbols"])
        
        # Collecter les symboles depuis les stratégies
        for strategy in self.strategies.values():
            if hasattr(strategy, "symbols"):
                symbols.extend(strategy.symbols)
        
        # Supprimer les doublons
        symbols = list(set(symbols))
        
        return symbols
    
    def _check_system_health(self):
        """
        Vérifie l'état de santé du système et des composants.
        
        Cette méthode surveille les performances du système, la connectivité
        des exchanges et l'état des composants critiques.
        """
        # Vérifier la connectivité des exchanges
        for exchange_id, exchange in self.exchanges.items():
            if not exchange.is_connected():
                logger.warning(f"Exchange {exchange_id} déconnecté. Tentative de reconnexion...")
                try:
                    exchange.reconnect()
                except Exception as e:
                    logger.error(f"Échec de la reconnexion à {exchange_id}: {str(e)}")
        
        # Vérifier l'utilisation de la mémoire et du CPU
        # (à implémenter avec des bibliothèques comme psutil)
        
        # Vérifier les limites d'API
        for exchange_id, exchange in self.exchanges.items():
            if hasattr(exchange, "check_rate_limits") and exchange.check_rate_limits():
                logger.warning(f"Limites d'API approchant pour {exchange_id}. Ralentissement des opérations...")
