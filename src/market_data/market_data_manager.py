#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Gestionnaire des données de marché.
"""

from typing import Dict, Any, List
from loguru import logger

class MarketDataManager:
    """Gestionnaire des données de marché."""
    
    def __init__(self, config: Dict[str, Any], exchanges: Dict[str, Any] = None):
        """
        Initialise le gestionnaire de données.
        
        Args:
            config: Configuration du gestionnaire
            exchanges: Dictionnaire des connecteurs d'échange
        """
        self.config = config
        self.exchanges = exchanges or {}
        self.data_cache = {}
        logger.info("Gestionnaire de données de marché initialisé")
    
    def get_market_data(self, symbol: str, timeframe: str) -> Dict[str, Any]:
        """
        Récupère les données de marché pour un symbole et un timeframe.
        
        Args:
            symbol: Symbole du marché
            timeframe: Timeframe des données
            
        Returns:
            Données de marché
        """
        cache_key = f"{symbol}_{timeframe}"
        if cache_key in self.data_cache:
            return self.data_cache[cache_key]
            
        # TODO: Implémenter la récupération des données depuis la source
        data = {}
        self.data_cache[cache_key] = data
        return data
    
    def update_market_data(self, symbol: str, timeframe: str, data: Dict[str, Any]):
        """
        Met à jour les données de marché.
        
        Args:
            symbol: Symbole du marché
            timeframe: Timeframe des données
            data: Nouvelles données
        """
        cache_key = f"{symbol}_{timeframe}"
        self.data_cache[cache_key] = data
        logger.debug(f"Données mises à jour pour {symbol} {timeframe}")
    
    def update(self):
        """
        Met à jour les données de marché pour tous les symboles configurés.
        """
        if not self.exchanges:
            logger.warning("Aucun exchange configuré")
            return
            
        for exchange_id, exchange in self.exchanges.items():
            for symbol in exchange.symbols:
                try:
                    # Récupérer les données de marché
                    data = exchange.fetch_ticker(symbol)
                    self.update_market_data(symbol, "ticker", data)
                    
                    # Récupérer le carnet d'ordres
                    data = exchange.fetch_order_book(symbol)
                    self.update_market_data(symbol, "orderbook", data)
                    
                except Exception as e:
                    logger.error(f"Erreur lors de la mise à jour des données pour {symbol} sur {exchange_id}: {str(e)}")
    
    def start(self):
        """
        Démarre le gestionnaire de données.
        """
        logger.info("Démarrage du gestionnaire de données de marché")
        # Initialiser les connexions WebSocket pour les données en temps réel
        for exchange_id, exchange in self.exchanges.items():
            if hasattr(exchange, 'start_market_data_stream'):
                exchange.start_market_data_stream()
    
    def stop(self):
        """
        Arrête le gestionnaire de données.
        """
        logger.info("Arrêt du gestionnaire de données de marché")
        # Fermer les connexions WebSocket
        for exchange_id, exchange in self.exchanges.items():
            if hasattr(exchange, 'stop_market_data_stream'):
                exchange.stop_market_data_stream()
        
        # Vider le cache
        self.data_cache.clear()
