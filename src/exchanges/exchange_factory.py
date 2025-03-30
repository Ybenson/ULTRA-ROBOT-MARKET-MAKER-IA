#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Factory pour la création d'instances d'échanges.
"""

from typing import Dict, Any
from loguru import logger

from src.exchanges.base_exchange import BaseExchange
from src.exchanges.binance_exchange import BinanceExchange

class ExchangeFactory:
    """Factory pour créer des instances d'échanges."""
    
    @staticmethod
    def create_exchange(exchange_id: str, config: Dict[str, Any]) -> BaseExchange:
        """
        Crée une instance d'échange en fonction de l'ID fourni.
        
        Args:
            exchange_id: Identifiant de l'échange (ex: 'binance', 'alpaca', etc.)
            config: Configuration de l'échange
            
        Returns:
            Une instance de BaseExchange
            
        Raises:
            ValueError: Si l'exchange_id n'est pas supporté
        """
        exchange_map = {
            'binance': BinanceExchange,
        }
        
        if exchange_id not in exchange_map:
            raise ValueError(f"Exchange non supporté: {exchange_id}")
            
        exchange_class = exchange_map[exchange_id]
        logger.info(f"Création d'une instance de {exchange_id}")
        return exchange_class(config)
