#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Classe de base pour les stratégies dans ULTRA-ROBOT MARKET MAKER IA.

Ce module définit l'interface commune que toutes les stratégies
doivent implémenter pour être utilisées par le bot.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple, Union
from loguru import logger

from src.data.market_data_manager import MarketDataManager


class BaseStrategy(ABC):
    """
    Classe abstraite définissant l'interface commune pour toutes les stratégies.
    
    Toutes les stratégies spécifiques doivent hériter de cette classe
    et implémenter ses méthodes abstraites.
    """
    
    def __init__(self, config: Dict[str, Any], market_data_manager: MarketDataManager):
        """
        Initialise la stratégie.
        
        Args:
            config: Configuration de la stratégie.
            market_data_manager: Gestionnaire de données de marché.
        """
        self.config = config
        self.market_data_manager = market_data_manager
        self.name = config.get("name", self.__class__.__name__)
        self.enabled = config.get("enabled", True)
        self.symbols = config.get("symbols", [])
        self.exchanges = config.get("exchanges", [])
        
        # Paramètres de performance
        self.performance = {
            "trades_total": 0,
            "trades_won": 0,
            "trades_lost": 0,
            "profit_total": 0.0,
            "profit_percent": 0.0,
            "max_drawdown": 0.0,
            "sharpe_ratio": 0.0
        }
        
        # État interne
        self.is_running = False
        self.last_update_time = 0
        
        logger.info(f"Stratégie {self.name} initialisée")
    
    @abstractmethod
    def update(self):
        """
        Met à jour la stratégie.
        
        Cette méthode est appelée périodiquement pour mettre à jour
        l'état de la stratégie et générer des signaux.
        """
        pass
    
    def start(self):
        """
        Démarre la stratégie.
        """
        if self.is_running:
            logger.warning(f"La stratégie {self.name} est déjà en cours d'exécution")
            return
        
        self.is_running = True
        logger.info(f"Stratégie {self.name} démarrée")
    
    def stop(self):
        """
        Arrête la stratégie.
        """
        if not self.is_running:
            logger.warning(f"La stratégie {self.name} n'est pas en cours d'exécution")
            return
        
        self.is_running = False
        logger.info(f"Stratégie {self.name} arrêtée")
    
    def is_enabled(self) -> bool:
        """
        Vérifie si la stratégie est activée.
        
        Returns:
            True si la stratégie est activée, False sinon.
        """
        return self.enabled
    
    def set_enabled(self, enabled: bool):
        """
        Active ou désactive la stratégie.
        
        Args:
            enabled: True pour activer, False pour désactiver.
        """
        self.enabled = enabled
        
        if self.enabled:
            logger.info(f"Stratégie {self.name} activée")
        else:
            logger.info(f"Stratégie {self.name} désactivée")
            
            # Arrêter la stratégie si elle est en cours d'exécution
            if self.is_running:
                self.stop()
    
    def get_name(self) -> str:
        """
        Récupère le nom de la stratégie.
        
        Returns:
            Nom de la stratégie.
        """
        return self.name
    
    def get_performance(self) -> Dict[str, Any]:
        """
        Récupère les performances de la stratégie.
        
        Returns:
            Dictionnaire des performances.
        """
        return self.performance
    
    def update_performance(self, trade_result: Dict[str, Any]):
        """
        Met à jour les performances de la stratégie.
        
        Args:
            trade_result: Résultat d'un trade.
        """
        # Incrémenter le nombre total de trades
        self.performance["trades_total"] += 1
        
        # Mettre à jour les trades gagnés/perdus
        if trade_result.get("profit", 0) > 0:
            self.performance["trades_won"] += 1
        else:
            self.performance["trades_lost"] += 1
        
        # Mettre à jour le profit total
        self.performance["profit_total"] += trade_result.get("profit", 0)
        
        # Mettre à jour le profit en pourcentage
        if trade_result.get("profit_percent", 0) != 0:
            self.performance["profit_percent"] += trade_result.get("profit_percent", 0)
        
        # Mettre à jour le drawdown maximum
        current_drawdown = trade_result.get("drawdown", 0)
        if current_drawdown > self.performance["max_drawdown"]:
            self.performance["max_drawdown"] = current_drawdown
        
        # Calculer le ratio de Sharpe (simplifié)
        if self.performance["trades_total"] > 0:
            win_rate = self.performance["trades_won"] / self.performance["trades_total"]
            avg_profit = self.performance["profit_total"] / self.performance["trades_total"]
            
            if avg_profit > 0:
                self.performance["sharpe_ratio"] = win_rate * avg_profit / (self.performance["max_drawdown"] + 0.0001)
    
    def should_process_symbol(self, symbol: str, exchange_id: Optional[str] = None) -> bool:
        """
        Vérifie si un symbole doit être traité par cette stratégie.
        
        Args:
            symbol: Symbole de l'actif.
            exchange_id: Identifiant de l'exchange.
            
        Returns:
            True si le symbole doit être traité, False sinon.
        """
        # Si aucun symbole n'est spécifié, traiter tous les symboles
        if not self.symbols:
            return True
        
        # Vérifier si le symbole est dans la liste des symboles à traiter
        if symbol in self.symbols:
            # Si aucun exchange n'est spécifié, traiter tous les exchanges
            if not self.exchanges:
                return True
            
            # Sinon, vérifier si l'exchange est dans la liste des exchanges à traiter
            return exchange_id in self.exchanges
        
        return False
    
    def get_config(self) -> Dict[str, Any]:
        """
        Récupère la configuration de la stratégie.
        
        Returns:
            Configuration de la stratégie.
        """
        return self.config
    
    def update_config(self, config: Dict[str, Any]):
        """
        Met à jour la configuration de la stratégie.
        
        Args:
            config: Nouvelle configuration.
        """
        self.config.update(config)
        
        # Mettre à jour les paramètres de base
        self.name = self.config.get("name", self.__class__.__name__)
        self.enabled = self.config.get("enabled", True)
        self.symbols = self.config.get("symbols", [])
        self.exchanges = self.config.get("exchanges", [])
        
        logger.info(f"Configuration de la stratégie {self.name} mise à jour")
