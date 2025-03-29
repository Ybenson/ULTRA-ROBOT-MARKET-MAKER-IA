#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Factory de stratégies pour ULTRA-ROBOT MARKET MAKER IA.

Ce module permet de créer différentes stratégies de trading en fonction
de la configuration fournie.
"""

from typing import Dict, Any, List, Optional
from loguru import logger

from src.strategies.market_making_strategy import MarketMakingStrategy
from src.strategies.adaptive_market_making_strategy import AdaptiveMarketMakingStrategy
from src.strategies.statistical_arbitrage_strategy import StatisticalArbitrageStrategy
from src.strategies.combined_strategy import CombinedStrategy


class StrategyFactory:
    """
    Factory pour créer des instances de stratégies de trading.
    
    Cette classe permet d'instancier différentes stratégies de trading
    en fonction de la configuration fournie.
    """
    
    def __init__(self, market_data_manager=None, order_executor=None, risk_manager=None, config=None):
        """
        Initialise la factory de stratégies.
        
        Args:
            market_data_manager: Gestionnaire de données de marché.
            order_executor: Exécuteur d'ordres.
            risk_manager: Gestionnaire de risques.
            config: Configuration des stratégies.
        """
        self.market_data_manager = market_data_manager
        self.order_executor = order_executor
        self.risk_manager = risk_manager
        self.config = config or {}
        
        # Registre des types de stratégies disponibles
        self.strategy_types = {
            "market_making": MarketMakingStrategy,
            "adaptive_market_making": AdaptiveMarketMakingStrategy,
            "statistical_arbitrage": StatisticalArbitrageStrategy,
            "combined": CombinedStrategy,
        }
        
        logger.info(f"Factory de stratégies initialisée avec {len(self.strategy_types)} types de stratégies")
    
    def create_strategy(self, strategy_id: str):
        """
        Crée une instance de stratégie en fonction de l'identifiant.
        
        Args:
            strategy_id: Identifiant de la stratégie à créer.
            
        Returns:
            Instance de la stratégie créée.
            
        Raises:
            ValueError: Si le type de stratégie n'est pas reconnu.
        """
        # Obtenir la configuration de la stratégie
        strategy_config = self._get_strategy_config(strategy_id)
        
        # Obtenir le type de stratégie
        strategy_type = strategy_config.get("type", "market_making")
        
        # Vérifier si le type de stratégie est valide
        if strategy_type not in self.strategy_types:
            raise ValueError(f"Type de stratégie non reconnu: {strategy_type}")
        
        # Créer l'instance de stratégie
        strategy_class = self.strategy_types[strategy_type]
        strategy = strategy_class(
            strategy_id=strategy_id,
            market_data_manager=self.market_data_manager,
            order_executor=self.order_executor,
            risk_manager=self.risk_manager,
            config=strategy_config
        )
        
        logger.info(f"Stratégie créée: {strategy_id} (type: {strategy_type})")
        return strategy
    
    def _get_strategy_config(self, strategy_id: str) -> Dict[str, Any]:
        """
        Obtient la configuration d'une stratégie spécifique.
        
        Args:
            strategy_id: Identifiant de la stratégie.
            
        Returns:
            Configuration de la stratégie.
        """
        # Obtenir la liste des stratégies activées
        enabled_strategies = self.config.get("enabled_strategies", [])
        
        # Chercher la configuration de la stratégie spécifique
        for strategy_config in enabled_strategies:
            if isinstance(strategy_config, dict) and strategy_config.get("id") == strategy_id:
                return strategy_config
            elif isinstance(strategy_config, str) and strategy_config == strategy_id:
                # Si seul l'ID est fourni, chercher dans les configurations par défaut
                if "default_configs" in self.config and strategy_id in self.config["default_configs"]:
                    return self.config["default_configs"][strategy_id]
        
        # Si aucune configuration spécifique n'est trouvée, utiliser une configuration par défaut
        logger.warning(f"Aucune configuration trouvée pour la stratégie {strategy_id}. Utilisation des valeurs par défaut.")
        return {
            "id": strategy_id,
            "type": "market_making",
            "symbols": self.config.get("default_symbols", ["BTC/USDT"]),
            "parameters": {
                "spread_bid": 0.1,  # 0.1%
                "spread_ask": 0.1,  # 0.1%
                "order_size": 0.01,
                "order_count": 3,
                "refresh_rate": 10,  # secondes
            }
        }
    
    def register_strategy_type(self, type_name: str, strategy_class):
        """
        Enregistre un nouveau type de stratégie.
        
        Args:
            type_name: Nom du type de stratégie.
            strategy_class: Classe de stratégie à enregistrer.
        """
        self.strategy_types[type_name] = strategy_class
        logger.info(f"Nouveau type de stratégie enregistré: {type_name}")
    
    def get_available_strategy_types(self) -> List[str]:
        """
        Obtient la liste des types de stratégies disponibles.
        
        Returns:
            Liste des noms des types de stratégies disponibles.
        """
        return list(self.strategy_types.keys())
