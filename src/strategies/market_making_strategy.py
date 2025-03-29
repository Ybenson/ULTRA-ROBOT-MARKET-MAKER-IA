#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Stratégie de Market Making de base pour ULTRA-ROBOT MARKET MAKER IA.

Ce module implémente une stratégie de market making classique qui place
des ordres d'achat et de vente autour du prix du marché avec un spread défini.
"""

import time
from typing import Dict, Any, List, Optional, Tuple
from loguru import logger


class MarketMakingStrategy:
    """
    Stratégie de Market Making de base.
    
    Cette classe implémente une stratégie de market making qui place des ordres
    d'achat et de vente autour du prix du marché avec un spread configurable.
    """
    
    def __init__(self, strategy_id: str, market_data_manager=None, order_executor=None, 
                 risk_manager=None, config=None):
        """
        Initialise la stratégie de Market Making.
        
        Args:
            strategy_id: Identifiant unique de la stratégie.
            market_data_manager: Gestionnaire de données de marché.
            order_executor: Exécuteur d'ordres.
            risk_manager: Gestionnaire de risques.
            config: Configuration de la stratégie.
        """
        self.strategy_id = strategy_id
        self.market_data_manager = market_data_manager
        self.order_executor = order_executor
        self.risk_manager = risk_manager
        self.config = config or {}
        
        # Extraire les paramètres de la configuration
        self.symbols = self.config.get("symbols", ["BTC/USDT"])
        parameters = self.config.get("parameters", {})
        
        # Paramètres de la stratégie
        self.spread_bid = parameters.get("spread_bid", 0.1)  # 0.1%
        self.spread_ask = parameters.get("spread_ask", 0.1)  # 0.1%
        self.order_size = parameters.get("order_size", 0.01)
        self.order_count = parameters.get("order_count", 3)
        self.refresh_rate = parameters.get("refresh_rate", 10)  # secondes
        self.min_profit = parameters.get("min_profit", 0.05)  # 0.05%
        self.max_position = parameters.get("max_position", 1.0)
        
        # État interne
        self.active_orders = {}  # Ordres actifs par symbole
        self.last_refresh_time = {}  # Dernier temps de rafraîchissement par symbole
        self.positions = {}  # Positions actuelles par symbole
        self.order_book_snapshots = {}  # Instantanés du carnet d'ordres par symbole
        
        logger.info(f"Stratégie de Market Making initialisée: {strategy_id} sur {', '.join(self.symbols)}")
    
    def execute(self):
        """
        Exécute la stratégie de market making.
        
        Cette méthode est appelée régulièrement par le moteur principal pour
        exécuter la logique de la stratégie.
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
                
                # Vérifier si le marché est manipulé
                if self.risk_manager and self.risk_manager.detect_market_manipulation(symbol):
                    logger.warning(f"Manipulation de marché détectée pour {symbol}. Suspension temporaire.")
                    self._cancel_all_orders(symbol)
                    continue
                
                # Obtenir les données de marché actuelles
                market_data = self._get_market_data(symbol)
                if not market_data:
                    logger.warning(f"Données de marché non disponibles pour {symbol}")
                    continue
                
                # Calculer les prix des ordres
                order_prices = self._calculate_order_prices(symbol, market_data)
                
                # Vérifier les limites de position
                current_position = self.positions.get(symbol, 0)
                if abs(current_position) >= self.max_position:
                    logger.warning(f"Position maximale atteinte pour {symbol}: {current_position}")
                    # Annuler les ordres du côté qui augmenterait la position
                    if current_position > 0:
                        self._cancel_orders_by_side(symbol, "buy")
                    else:
                        self._cancel_orders_by_side(symbol, "sell")
                
                # Annuler les ordres existants si nécessaire
                if self._should_refresh_orders(symbol, order_prices):
                    self._cancel_all_orders(symbol)
                
                # Placer de nouveaux ordres
                self._place_orders(symbol, order_prices)
                
                logger.debug(f"Stratégie exécutée pour {symbol}")
                
            except Exception as e:
                logger.error(f"Erreur lors de l'exécution de la stratégie pour {symbol}: {str(e)}")
    
    def _get_market_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Obtient les données de marché actuelles pour un symbole.
        
        Args:
            symbol: Symbole de l'actif.
            
        Returns:
            Dictionnaire contenant les données de marché ou None si non disponibles.
        """
        if not self.market_data_manager:
            logger.warning("Gestionnaire de données de marché non disponible")
            return None
        
        try:
            # Obtenir le prix moyen actuel
            ticker = self.market_data_manager.get_ticker(symbol)
            if not ticker:
                return None
            
            # Obtenir le carnet d'ordres
            order_book = self.market_data_manager.get_order_book(symbol)
            if not order_book:
                return None
            
            # Stocker un instantané du carnet d'ordres
            self.order_book_snapshots[symbol] = order_book
            
            # Extraire les informations pertinentes
            mid_price = (ticker["bid"] + ticker["ask"]) / 2
            bid_price = ticker["bid"]
            ask_price = ticker["ask"]
            current_spread = (ask_price - bid_price) / mid_price * 100  # en pourcentage
            
            return {
                "mid_price": mid_price,
                "bid_price": bid_price,
                "ask_price": ask_price,
                "current_spread": current_spread,
                "order_book": order_book,
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de l'obtention des données de marché pour {symbol}: {str(e)}")
            return None
    
    def _calculate_order_prices(self, symbol: str, market_data: Dict[str, Any]) -> Dict[str, List[float]]:
        """
        Calcule les prix des ordres à placer.
        
        Args:
            symbol: Symbole de l'actif.
            market_data: Données de marché actuelles.
            
        Returns:
            Dictionnaire contenant les prix des ordres d'achat et de vente.
        """
        mid_price = market_data["mid_price"]
        
        # Calculer les prix des ordres d'achat
        bid_prices = []
        for i in range(self.order_count):
            # Spread progressif pour les ordres plus éloignés
            spread_factor = 1 + i * 0.5  # Augmenter le spread pour les ordres plus éloignés
            bid_spread = self.spread_bid * spread_factor
            bid_price = mid_price * (1 - bid_spread / 100)
            bid_prices.append(bid_price)
        
        # Calculer les prix des ordres de vente
        ask_prices = []
        for i in range(self.order_count):
            # Spread progressif pour les ordres plus éloignés
            spread_factor = 1 + i * 0.5  # Augmenter le spread pour les ordres plus éloignés
            ask_spread = self.spread_ask * spread_factor
            ask_price = mid_price * (1 + ask_spread / 100)
            ask_prices.append(ask_price)
        
        return {
            "bid_prices": bid_prices,
            "ask_prices": ask_prices
        }
    
    def _should_refresh_orders(self, symbol: str, new_order_prices: Dict[str, List[float]]) -> bool:
        """
        Détermine si les ordres existants doivent être rafraîchis.
        
        Args:
            symbol: Symbole de l'actif.
            new_order_prices: Nouveaux prix des ordres calculés.
            
        Returns:
            True si les ordres doivent être rafraîchis, False sinon.
        """
        # Si aucun ordre actif, rafraîchir
        if symbol not in self.active_orders or not self.active_orders[symbol]:
            return True
        
        # Obtenir les ordres actifs
        active_orders = self.active_orders[symbol]
        
        # Vérifier si le nombre d'ordres a changé
        if len(active_orders.get("buy", [])) != len(new_order_prices["bid_prices"]) or \
           len(active_orders.get("sell", [])) != len(new_order_prices["ask_prices"]):
            return True
        
        # Vérifier si les prix ont changé significativement
        price_threshold = 0.1  # 0.1% de changement de prix
        
        for i, order in enumerate(active_orders.get("buy", [])):
            if i >= len(new_order_prices["bid_prices"]):
                break
            old_price = order["price"]
            new_price = new_order_prices["bid_prices"][i]
            price_diff = abs(old_price - new_price) / old_price * 100
            if price_diff > price_threshold:
                return True
        
        for i, order in enumerate(active_orders.get("sell", [])):
            if i >= len(new_order_prices["ask_prices"]):
                break
            old_price = order["price"]
            new_price = new_order_prices["ask_prices"][i]
            price_diff = abs(old_price - new_price) / old_price * 100
            if price_diff > price_threshold:
                return True
        
        return False
    
    def _cancel_all_orders(self, symbol: str):
        """
        Annule tous les ordres actifs pour un symbole.
        
        Args:
            symbol: Symbole de l'actif.
        """
        if not self.order_executor:
            logger.warning("Exécuteur d'ordres non disponible")
            return
        
        if symbol not in self.active_orders:
            return
        
        try:
            # Annuler tous les ordres d'achat
            for order in self.active_orders[symbol].get("buy", []):
                self.order_executor.cancel_order(symbol, order["id"])
            
            # Annuler tous les ordres de vente
            for order in self.active_orders[symbol].get("sell", []):
                self.order_executor.cancel_order(symbol, order["id"])
            
            # Réinitialiser les ordres actifs
            self.active_orders[symbol] = {"buy": [], "sell": []}
            
            logger.debug(f"Tous les ordres annulés pour {symbol}")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'annulation des ordres pour {symbol}: {str(e)}")
    
    def _cancel_orders_by_side(self, symbol: str, side: str):
        """
        Annule tous les ordres actifs d'un côté spécifique pour un symbole.
        
        Args:
            symbol: Symbole de l'actif.
            side: Côté des ordres à annuler ('buy' ou 'sell').
        """
        if not self.order_executor:
            logger.warning("Exécuteur d'ordres non disponible")
            return
        
        if symbol not in self.active_orders or side not in self.active_orders[symbol]:
            return
        
        try:
            # Annuler tous les ordres du côté spécifié
            for order in self.active_orders[symbol][side]:
                self.order_executor.cancel_order(symbol, order["id"])
            
            # Réinitialiser les ordres actifs du côté spécifié
            self.active_orders[symbol][side] = []
            
            logger.debug(f"Ordres {side} annulés pour {symbol}")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'annulation des ordres {side} pour {symbol}: {str(e)}")
    
    def _place_orders(self, symbol: str, order_prices: Dict[str, List[float]]):
        """
        Place de nouveaux ordres pour un symbole.
        
        Args:
            symbol: Symbole de l'actif.
            order_prices: Prix des ordres à placer.
        """
        if not self.order_executor:
            logger.warning("Exécuteur d'ordres non disponible")
            return
        
        # Initialiser les ordres actifs si nécessaire
        if symbol not in self.active_orders:
            self.active_orders[symbol] = {"buy": [], "sell": []}
        
        try:
            # Placer les ordres d'achat
            for price in order_prices["bid_prices"]:
                # Vérifier les limites de position pour les achats
                if self.risk_manager and not self.risk_manager.check_position_limit(symbol, "buy", self.order_size):
                    logger.warning(f"Limite de position atteinte pour les achats sur {symbol}")
                    break
                
                order = self.order_executor.place_order(
                    symbol=symbol,
                    side="buy",
                    order_type="limit",
                    amount=self.order_size,
                    price=price
                )
                
                if order:
                    self.active_orders[symbol]["buy"].append(order)
                    logger.debug(f"Ordre d'achat placé pour {symbol} à {price:.8f}")
            
            # Placer les ordres de vente
            for price in order_prices["ask_prices"]:
                # Vérifier les limites de position pour les ventes
                if self.risk_manager and not self.risk_manager.check_position_limit(symbol, "sell", self.order_size):
                    logger.warning(f"Limite de position atteinte pour les ventes sur {symbol}")
                    break
                
                order = self.order_executor.place_order(
                    symbol=symbol,
                    side="sell",
                    order_type="limit",
                    amount=self.order_size,
                    price=price
                )
                
                if order:
                    self.active_orders[symbol]["sell"].append(order)
                    logger.debug(f"Ordre de vente placé pour {symbol} à {price:.8f}")
            
        except Exception as e:
            logger.error(f"Erreur lors du placement des ordres pour {symbol}: {str(e)}")
    
    def update_parameters(self, parameters: Dict[str, Any]):
        """
        Met à jour les paramètres de la stratégie.
        
        Args:
            parameters: Nouveaux paramètres à appliquer.
        """
        # Mettre à jour les paramètres
        if "spread_bid" in parameters:
            self.spread_bid = parameters["spread_bid"]
        if "spread_ask" in parameters:
            self.spread_ask = parameters["spread_ask"]
        if "order_size" in parameters:
            self.order_size = parameters["order_size"]
        if "order_count" in parameters:
            self.order_count = parameters["order_count"]
        if "refresh_rate" in parameters:
            self.refresh_rate = parameters["refresh_rate"]
        if "min_profit" in parameters:
            self.min_profit = parameters["min_profit"]
        if "max_position" in parameters:
            self.max_position = parameters["max_position"]
        
        logger.info(f"Paramètres mis à jour pour la stratégie {self.strategy_id}")
    
    def get_parameters(self) -> Dict[str, Any]:
        """
        Obtient les paramètres actuels de la stratégie.
        
        Returns:
            Dictionnaire des paramètres actuels.
        """
        return {
            "spread_bid": self.spread_bid,
            "spread_ask": self.spread_ask,
            "order_size": self.order_size,
            "order_count": self.order_count,
            "refresh_rate": self.refresh_rate,
            "min_profit": self.min_profit,
            "max_position": self.max_position
        }
    
    def get_status(self) -> Dict[str, Any]:
        """
        Obtient l'état actuel de la stratégie.
        
        Returns:
            Dictionnaire contenant l'état actuel de la stratégie.
        """
        return {
            "strategy_id": self.strategy_id,
            "symbols": self.symbols,
            "active_orders": self.active_orders,
            "positions": self.positions,
            "parameters": self.get_parameters()
        }
