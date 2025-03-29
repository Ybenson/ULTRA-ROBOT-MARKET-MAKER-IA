#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Stratégie de Market Making Adaptative pour ULTRA-ROBOT MARKET MAKER IA.

Ce module étend la stratégie de market making de base avec des ajustements
dynamiques en fonction des conditions de marché.
"""

import time
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from loguru import logger

from src.strategies.market_making_strategy import MarketMakingStrategy


class AdaptiveMarketMakingStrategy(MarketMakingStrategy):
    """
    Stratégie de Market Making Adaptative.
    
    Cette classe étend la stratégie de market making de base avec des ajustements
    dynamiques des spreads et des tailles d'ordres en fonction de la volatilité,
    du volume et d'autres conditions de marché.
    """
    
    def __init__(self, strategy_id: str, market_data_manager=None, order_executor=None, 
                 risk_manager=None, config=None):
        """
        Initialise la stratégie de Market Making Adaptative.
        
        Args:
            strategy_id: Identifiant unique de la stratégie.
            market_data_manager: Gestionnaire de données de marché.
            order_executor: Exécuteur d'ordres.
            risk_manager: Gestionnaire de risques.
            config: Configuration de la stratégie.
        """
        # Initialiser la classe parente
        super().__init__(strategy_id, market_data_manager, order_executor, risk_manager, config)
        
        # Extraire les paramètres spécifiques à la stratégie adaptative
        parameters = self.config.get("parameters", {})
        
        # Paramètres d'adaptation
        self.volatility_factor = parameters.get("volatility_factor", 1.0)
        self.volume_factor = parameters.get("volume_factor", 1.0)
        self.trend_factor = parameters.get("trend_factor", 0.5)
        self.liquidity_factor = parameters.get("liquidity_factor", 1.0)
        self.mean_reversion_factor = parameters.get("mean_reversion_factor", 0.5)
        
        # Fenêtres d'analyse
        self.volatility_window = parameters.get("volatility_window", 24)  # heures
        self.volume_window = parameters.get("volume_window", 24)  # heures
        self.trend_window = parameters.get("trend_window", 24)  # heures
        
        # Limites d'adaptation
        self.max_spread_multiplier = parameters.get("max_spread_multiplier", 3.0)
        self.min_spread_multiplier = parameters.get("min_spread_multiplier", 0.5)
        self.max_size_multiplier = parameters.get("max_size_multiplier", 2.0)
        self.min_size_multiplier = parameters.get("min_size_multiplier", 0.5)
        
        # État interne pour l'adaptation
        self.market_conditions = {}  # Conditions de marché par symbole
        self.historical_spreads = {}  # Historique des spreads par symbole
        self.historical_volumes = {}  # Historique des volumes par symbole
        self.historical_volatilities = {}  # Historique des volatilités par symbole
        
        logger.info(f"Stratégie de Market Making Adaptative initialisée: {strategy_id}")
    
    def execute(self):
        """
        Exécute la stratégie de market making adaptative.
        
        Cette méthode étend la méthode de base pour inclure l'adaptation
        des paramètres en fonction des conditions de marché.
        """
        current_time = time.time()
        
        # Exécuter la stratégie pour chaque symbole
        for symbol in self.symbols:
            try:
                # Vérifier si un rafraîchissement est nécessaire
                last_refresh = self.last_refresh_time.get(symbol, 0)
                if current_time - last_refresh < self.refresh_rate:
                    continue
                
                # Mettre à jour le temps de rafraîchissement
                self.last_refresh_time[symbol] = current_time
                
                # Analyser les conditions de marché
                self._analyze_market_conditions(symbol)
                
                # Adapter les paramètres
                self._adapt_parameters(symbol)
                
                # Exécuter la logique de la stratégie de base
                super().execute()
                
                logger.debug(f"Stratégie adaptative exécutée pour {symbol}")
                
            except Exception as e:
                logger.error(f"Erreur lors de l'exécution de la stratégie adaptative pour {symbol}: {str(e)}")
    
    def _analyze_market_conditions(self, symbol: str):
        """
        Analyse les conditions de marché pour un symbole.
        
        Args:
            symbol: Symbole de l'actif.
        """
        if not self.market_data_manager:
            return
        
        try:
            # Initialiser les conditions de marché si nécessaire
            if symbol not in self.market_conditions:
                self.market_conditions[symbol] = {
                    "volatility": 1.0,
                    "volume_ratio": 1.0,
                    "trend_strength": 0.0,
                    "liquidity": 1.0,
                    "mean_reversion": 0.0
                }
            
            # Obtenir la volatilité
            volatility = self.market_data_manager.get_volatility(symbol, window=self.volatility_window)
            if volatility is not None:
                # Normaliser la volatilité par rapport à la moyenne historique
                if symbol not in self.historical_volatilities:
                    self.historical_volatilities[symbol] = []
                
                self.historical_volatilities[symbol].append(volatility)
                if len(self.historical_volatilities[symbol]) > 100:
                    self.historical_volatilities[symbol].pop(0)
                
                avg_volatility = np.mean(self.historical_volatilities[symbol]) if self.historical_volatilities[symbol] else volatility
                normalized_volatility = volatility / avg_volatility if avg_volatility > 0 else 1.0
                
                self.market_conditions[symbol]["volatility"] = normalized_volatility
            
            # Obtenir le ratio de volume
            current_volume = self.market_data_manager.get_average_volume(symbol, window=1)
            avg_volume = self.market_data_manager.get_average_volume(symbol, window=self.volume_window)
            
            if current_volume is not None and avg_volume is not None and avg_volume > 0:
                volume_ratio = current_volume / avg_volume
                self.market_conditions[symbol]["volume_ratio"] = volume_ratio
            
            # Obtenir la force de la tendance
            trend_strength = self.market_data_manager.get_trend_indicator(symbol, window=self.trend_window)
            if trend_strength is not None:
                self.market_conditions[symbol]["trend_strength"] = trend_strength
            
            # Obtenir la liquidité
            liquidity = self.market_data_manager.get_order_book_depth(symbol)
            if liquidity is not None:
                self.market_conditions[symbol]["liquidity"] = liquidity
            
            # Calculer l'indicateur de retour à la moyenne
            mean_reversion = self._calculate_mean_reversion(symbol)
            if mean_reversion is not None:
                self.market_conditions[symbol]["mean_reversion"] = mean_reversion
            
            logger.debug(f"Conditions de marché analysées pour {symbol}: {self.market_conditions[symbol]}")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse des conditions de marché pour {symbol}: {str(e)}")
    
    def _calculate_mean_reversion(self, symbol: str) -> Optional[float]:
        """
        Calcule l'indicateur de retour à la moyenne pour un symbole.
        
        Args:
            symbol: Symbole de l'actif.
            
        Returns:
            Indicateur de retour à la moyenne entre -1 et 1, ou None si non disponible.
        """
        if not self.market_data_manager:
            return None
        
        try:
            # Obtenir les prix récents
            recent_prices = self.market_data_manager.get_recent_prices(symbol, limit=20)
            if not recent_prices or len(recent_prices) < 10:
                return None
            
            # Calculer la moyenne mobile
            window = min(10, len(recent_prices))
            moving_avg = np.mean(recent_prices[-window:])
            
            # Calculer la déviation du prix actuel par rapport à la moyenne
            current_price = recent_prices[-1]
            deviation = (current_price - moving_avg) / moving_avg
            
            # Normaliser entre -1 et 1
            mean_reversion = np.clip(deviation * -1, -1, 1)
            
            return mean_reversion
            
        except Exception as e:
            logger.error(f"Erreur lors du calcul du retour à la moyenne pour {symbol}: {str(e)}")
            return None
    
    def _adapt_parameters(self, symbol: str):
        """
        Adapte les paramètres de la stratégie en fonction des conditions de marché.
        
        Args:
            symbol: Symbole de l'actif.
        """
        if symbol not in self.market_conditions:
            return
        
        try:
            conditions = self.market_conditions[symbol]
            
            # Adapter le spread en fonction de la volatilité
            volatility_multiplier = conditions["volatility"] ** self.volatility_factor
            volatility_multiplier = np.clip(volatility_multiplier, self.min_spread_multiplier, self.max_spread_multiplier)
            
            # Adapter la taille des ordres en fonction du volume
            volume_multiplier = conditions["volume_ratio"] ** self.volume_factor
            volume_multiplier = np.clip(volume_multiplier, self.min_size_multiplier, self.max_size_multiplier)
            
            # Adapter le spread en fonction de la liquidité
            liquidity_multiplier = conditions["liquidity"] ** (-self.liquidity_factor)
            liquidity_multiplier = np.clip(liquidity_multiplier, self.min_spread_multiplier, self.max_spread_multiplier)
            
            # Adapter le spread en fonction de la tendance
            trend_strength = abs(conditions["trend_strength"])
            trend_multiplier = 1 + trend_strength * self.trend_factor
            
            # Adapter le spread en fonction du retour à la moyenne
            mean_reversion = abs(conditions["mean_reversion"])
            mean_reversion_multiplier = 1 + mean_reversion * self.mean_reversion_factor
            
            # Calculer les multiplicateurs finaux
            final_spread_multiplier = volatility_multiplier * liquidity_multiplier * trend_multiplier * mean_reversion_multiplier
            final_spread_multiplier = np.clip(final_spread_multiplier, self.min_spread_multiplier, self.max_spread_multiplier)
            
            final_size_multiplier = volume_multiplier
            final_size_multiplier = np.clip(final_size_multiplier, self.min_size_multiplier, self.max_size_multiplier)
            
            # Appliquer les multiplicateurs aux paramètres de base
            base_params = self.get_parameters()
            adapted_params = {
                "spread_bid": base_params["spread_bid"] * final_spread_multiplier,
                "spread_ask": base_params["spread_ask"] * final_spread_multiplier,
                "order_size": base_params["order_size"] * final_size_multiplier
            }
            
            # Adapter le nombre d'ordres en fonction de la liquidité
            if conditions["liquidity"] < 0.5:
                adapted_params["order_count"] = max(1, int(base_params["order_count"] * 0.5))
            elif conditions["liquidity"] > 2.0:
                adapted_params["order_count"] = min(10, int(base_params["order_count"] * 1.5))
            
            # Adapter la fréquence de rafraîchissement en fonction de la volatilité
            if conditions["volatility"] > 1.5:
                adapted_params["refresh_rate"] = max(1, int(base_params["refresh_rate"] * 0.7))
            elif conditions["volatility"] < 0.7:
                adapted_params["refresh_rate"] = min(30, int(base_params["refresh_rate"] * 1.3))
            
            # Mettre à jour les paramètres
            self.update_parameters(adapted_params)
            
            logger.debug(f"Paramètres adaptés pour {symbol}: spread_multiplier={final_spread_multiplier:.2f}, size_multiplier={final_size_multiplier:.2f}")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'adaptation des paramètres pour {symbol}: {str(e)}")
    
    def update_parameters(self, parameters: Dict[str, Any]):
        """
        Met à jour les paramètres de la stratégie.
        
        Args:
            parameters: Nouveaux paramètres à appliquer.
        """
        # Mettre à jour les paramètres de base via la classe parente
        super().update_parameters(parameters)
        
        # Mettre à jour les paramètres spécifiques à la stratégie adaptative
        if "volatility_factor" in parameters:
            self.volatility_factor = parameters["volatility_factor"]
        if "volume_factor" in parameters:
            self.volume_factor = parameters["volume_factor"]
        if "trend_factor" in parameters:
            self.trend_factor = parameters["trend_factor"]
        if "liquidity_factor" in parameters:
            self.liquidity_factor = parameters["liquidity_factor"]
        if "mean_reversion_factor" in parameters:
            self.mean_reversion_factor = parameters["mean_reversion_factor"]
        
        logger.info(f"Paramètres adaptatifs mis à jour pour la stratégie {self.strategy_id}")
    
    def get_parameters(self) -> Dict[str, Any]:
        """
        Obtient les paramètres actuels de la stratégie.
        
        Returns:
            Dictionnaire des paramètres actuels.
        """
        # Obtenir les paramètres de base
        params = super().get_parameters()
        
        # Ajouter les paramètres spécifiques à la stratégie adaptative
        params.update({
            "volatility_factor": self.volatility_factor,
            "volume_factor": self.volume_factor,
            "trend_factor": self.trend_factor,
            "liquidity_factor": self.liquidity_factor,
            "mean_reversion_factor": self.mean_reversion_factor,
            "volatility_window": self.volatility_window,
            "volume_window": self.volume_window,
            "trend_window": self.trend_window,
            "max_spread_multiplier": self.max_spread_multiplier,
            "min_spread_multiplier": self.min_spread_multiplier,
            "max_size_multiplier": self.max_size_multiplier,
            "min_size_multiplier": self.min_size_multiplier
        })
        
        return params
    
    def get_status(self) -> Dict[str, Any]:
        """
        Obtient l'état actuel de la stratégie.
        
        Returns:
            Dictionnaire contenant l'état actuel de la stratégie.
        """
        # Obtenir l'état de base
        status = super().get_status()
        
        # Ajouter les informations spécifiques à la stratégie adaptative
        status.update({
            "market_conditions": self.market_conditions
        })
        
        return status
