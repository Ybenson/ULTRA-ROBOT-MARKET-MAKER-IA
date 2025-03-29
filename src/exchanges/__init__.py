#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module d'exchanges pour ULTRA-ROBOT MARKET MAKER IA.

Ce module contient les connecteurs pour les différents exchanges supportés.
"""

from src.exchanges.base_exchange import BaseExchange
from src.exchanges.binance_exchange import BinanceExchange

# Dictionnaire des connecteurs d'exchanges disponibles
EXCHANGE_CONNECTORS = {
    "binance": BinanceExchange
}

def create_exchange(exchange_id: str, config: dict):
    """
    Crée une instance de connecteur d'exchange.
    
    Args:
        exchange_id: Identifiant de l'exchange.
        config: Configuration du connecteur.
        
    Returns:
        Instance du connecteur d'exchange.
        
    Raises:
        ValueError: Si l'exchange n'est pas supporté.
    """
    if exchange_id.lower() not in EXCHANGE_CONNECTORS:
        raise ValueError(f"Exchange non supporté: {exchange_id}")
    
    connector_class = EXCHANGE_CONNECTORS[exchange_id.lower()]
    return connector_class(config)
