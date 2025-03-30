#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Connecteur de base pour les exchanges dans ULTRA-ROBOT MARKET MAKER IA.

Ce module définit l'interface commune que tous les connecteurs d'exchange
doivent implémenter pour être utilisés par le bot.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple, Union
from loguru import logger


class BaseExchange(ABC):
    """
    Classe abstraite définissant l'interface commune pour tous les connecteurs d'exchange.
    
    Tous les connecteurs spécifiques à un exchange doivent hériter de cette classe
    et implémenter ses méthodes abstraites.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialise le connecteur d'exchange.
        
        Args:
            config: Configuration du connecteur.
        """
        self.config = config
        self.name = config.get("name", "unknown")
        self.api_key = config.get("api_key", "")
        self.api_secret = config.get("api_secret", "")
        self.additional_params = config.get("additional_params", {})
        
        # Capacités de l'exchange
        self.has = {
            "fetchTicker": True,
            "fetchOrderBook": True,
            "fetchOHLCV": True,
            "createOrder": True,
            "cancelOrder": True,
            "fetchBalance": True,
            "fetchOrders": True,
            "fetchOpenOrders": True,
            "fetchClosedOrders": True,
            "ws": False  # Websocket support
        }
        
        # Limites de l'exchange
        self.limits = {
            "order_rate": config.get("limits", {}).get("order_rate", 10),  # Ordres par seconde
            "market_data_rate": config.get("limits", {}).get("market_data_rate", 20)  # Requêtes par seconde
        }
        
        # Frais de l'exchange
        self.fees = {
            "maker": config.get("fees", {}).get("maker", 0.001),  # 0.1% par défaut
            "taker": config.get("fees", {}).get("taker", 0.001)   # 0.1% par défaut
        }
        
        # Symboles supportés
        self.symbols = config.get("symbols", [])
        
        # État de la connexion
        self.connected = False
        
        logger.info(f"Connecteur d'exchange {self.name} initialisé")
    
    @abstractmethod
    def connect(self) -> bool:
        """
        Établit la connexion avec l'exchange.
        
        Returns:
            True si la connexion est établie avec succès, False sinon.
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> bool:
        """
        Ferme la connexion avec l'exchange.
        
        Returns:
            True si la déconnexion est réussie, False sinon.
        """
        pass
    
    @abstractmethod
    def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Récupère le ticker pour un symbole.
        
        Args:
            symbol: Symbole de l'actif.
            
        Returns:
            Dictionnaire contenant les informations du ticker.
        """
        pass
    
    @abstractmethod
    def fetch_order_book(self, symbol: str, limit: int = 10) -> Dict[str, Any]:
        """
        Récupère le carnet d'ordres pour un symbole.
        
        Args:
            symbol: Symbole de l'actif.
            limit: Nombre maximum d'ordres à récupérer.
            
        Returns:
            Dictionnaire contenant le carnet d'ordres.
        """
        pass
    
    @abstractmethod
    def fetch_ohlcv(self, symbol: str, timeframe: str = "1h", limit: int = 100) -> List[List[float]]:
        """
        Récupère les bougies OHLCV pour un symbole.
        
        Args:
            symbol: Symbole de l'actif.
            timeframe: Intervalle des bougies (1m, 5m, 15m, 1h, 4h, 1d).
            limit: Nombre maximum de bougies à récupérer.
            
        Returns:
            Liste des bougies OHLCV.
        """
        pass
    
    @abstractmethod
    def fetch_balance(self) -> Dict[str, Any]:
        """
        Récupère le solde du compte.
        
        Returns:
            Dictionnaire contenant les soldes pour chaque actif.
        """
        pass
    
    @abstractmethod
    def create_order(self, symbol: str, order_type: str, side: str, amount: float, 
                    price: Optional[float] = None, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Crée un ordre sur l'exchange.
        
        Args:
            symbol: Symbole de l'actif.
            order_type: Type d'ordre (limit, market, etc.).
            side: Côté de l'ordre (buy, sell).
            amount: Quantité à acheter/vendre.
            price: Prix de l'ordre (pour les ordres limit).
            params: Paramètres supplémentaires spécifiques à l'exchange.
            
        Returns:
            Dictionnaire contenant les informations de l'ordre créé.
        """
        pass
    
    @abstractmethod
    def cancel_order(self, order_id: str, symbol: Optional[str] = None) -> Dict[str, Any]:
        """
        Annule un ordre sur l'exchange.
        
        Args:
            order_id: Identifiant de l'ordre à annuler.
            symbol: Symbole de l'actif (requis par certains exchanges).
            
        Returns:
            Dictionnaire contenant les informations de l'ordre annulé.
        """
        pass
    
    @abstractmethod
    def fetch_order(self, order_id: str, symbol: Optional[str] = None) -> Dict[str, Any]:
        """
        Récupère les informations d'un ordre.
        
        Args:
            order_id: Identifiant de l'ordre.
            symbol: Symbole de l'actif (requis par certains exchanges).
            
        Returns:
            Dictionnaire contenant les informations de l'ordre.
        """
        pass
    
    @abstractmethod
    def fetch_orders(self, symbol: Optional[str] = None, since: Optional[int] = None, 
                    limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Récupère la liste des ordres.
        
        Args:
            symbol: Symbole de l'actif (optionnel).
            since: Timestamp à partir duquel récupérer les ordres (optionnel).
            limit: Nombre maximum d'ordres à récupérer (optionnel).
            
        Returns:
            Liste des ordres.
        """
        pass
    
    @abstractmethod
    def fetch_open_orders(self, symbol: Optional[str] = None, since: Optional[int] = None, 
                         limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Récupère la liste des ordres ouverts.
        
        Args:
            symbol: Symbole de l'actif (optionnel).
            since: Timestamp à partir duquel récupérer les ordres (optionnel).
            limit: Nombre maximum d'ordres à récupérer (optionnel).
            
        Returns:
            Liste des ordres ouverts.
        """
        pass
    
    @abstractmethod
    def start_market_data_stream(self) -> bool:
        """
        Démarre le flux de données de marché.
        
        Returns:
            True si le flux est démarré avec succès, False sinon.
        """
        pass
    
    @abstractmethod
    def stop_market_data_stream(self) -> bool:
        """
        Arrête le flux de données de marché.
        
        Returns:
            True si le flux est arrêté avec succès, False sinon.
        """
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """
        Vérifie si l'exchange est connecté.
        
        Returns:
            True si l'exchange est connecté, False sinon.
        """
        pass
    
    def has_symbol(self, symbol: str) -> bool:
        """
        Vérifie si un symbole est supporté par l'exchange.
        
        Args:
            symbol: Symbole de l'actif.
            
        Returns:
            True si le symbole est supporté, False sinon.
        """
        return symbol in self.symbols
    
    def get_fee(self, symbol: str, order_type: str, side: str, amount: float, 
               price: float, is_maker: bool = True) -> float:
        """
        Calcule les frais pour un ordre.
        
        Args:
            symbol: Symbole de l'actif.
            order_type: Type d'ordre (limit, market, etc.).
            side: Côté de l'ordre (buy, sell).
            amount: Quantité à acheter/vendre.
            price: Prix de l'ordre.
            is_maker: True si l'ordre est un maker, False s'il est un taker.
            
        Returns:
            Montant des frais.
        """
        fee_type = "maker" if is_maker else "taker"
        fee_rate = self.fees.get(fee_type, 0.001)
        
        # Calculer le montant total de l'ordre
        order_amount = amount * price
        
        # Calculer les frais
        fee_amount = order_amount * fee_rate
        
        return fee_amount
    
    def get_min_order_amount(self, symbol: str) -> float:
        """
        Récupère le montant minimum pour un ordre.
        
        Args:
            symbol: Symbole de l'actif.
            
        Returns:
            Montant minimum pour un ordre.
        """
        # Par défaut, retourner une valeur générique
        # Les implémentations spécifiques devraient surcharger cette méthode
        return 0.001
    
    def get_min_price_increment(self, symbol: str) -> float:
        """
        Récupère l'incrément minimum de prix pour un symbole.
        
        Args:
            symbol: Symbole de l'actif.
            
        Returns:
            Incrément minimum de prix.
        """
        # Par défaut, retourner une valeur générique
        # Les implémentations spécifiques devraient surcharger cette méthode
        return 0.00001
    
    def get_min_amount_increment(self, symbol: str) -> float:
        """
        Récupère l'incrément minimum de quantité pour un symbole.
        
        Args:
            symbol: Symbole de l'actif.
            
        Returns:
            Incrément minimum de quantité.
        """
        # Par défaut, retourner une valeur générique
        # Les implémentations spécifiques devraient surcharger cette méthode
        return 0.00001
