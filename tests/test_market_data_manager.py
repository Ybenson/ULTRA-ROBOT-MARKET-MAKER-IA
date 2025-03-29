#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests unitaires pour le gestionnaire de données de marché.

Ce module contient les tests unitaires pour valider le fonctionnement
du gestionnaire de données de marché.
"""

import unittest
import time
import threading
from unittest.mock import MagicMock, patch
import numpy as np
from typing import Dict, Any

from src.data.market_data_manager import MarketDataManager


class TestMarketDataManager(unittest.TestCase):
    """
    Tests unitaires pour le gestionnaire de données de marché.
    """
    
    def setUp(self):
        """
        Initialise l'environnement de test avant chaque test.
        """
        # Créer un mock pour les exchanges
        self.mock_exchange = MagicMock()
        self.mock_exchange.fetch_ticker.return_value = {
            "symbol": "BTC/USDT",
            "bid": 50000.0,
            "ask": 50100.0,
            "last": 50050.0,
            "high": 51000.0,
            "low": 49000.0,
            "volume": 100.0,
            "timestamp": int(time.time() * 1000)
        }
        
        self.mock_exchange.fetch_order_book.return_value = {
            "bids": [[50000.0, 1.0], [49900.0, 2.0], [49800.0, 3.0]],
            "asks": [[50100.0, 1.0], [50200.0, 2.0], [50300.0, 3.0]],
            "timestamp": int(time.time() * 1000),
            "nonce": 123456789
        }
        
        self.mock_exchange.fetch_ohlcv.return_value = [
            [int(time.time() * 1000) - 3600000, 50000.0, 50500.0, 49500.0, 50050.0, 100.0],
            [int(time.time() * 1000) - 3600000 * 2, 49800.0, 50300.0, 49700.0, 50100.0, 120.0],
            [int(time.time() * 1000) - 3600000 * 3, 49900.0, 50400.0, 49600.0, 49800.0, 110.0]
        ]
        
        self.exchanges = {"binance": self.mock_exchange}
        
        # Configuration pour le gestionnaire de données
        self.config = {
            "cache_enabled": True,
            "cache_expiry_seconds": 10,
            "historical_data_days": 1,
            "use_websockets": False,
            "order_book_depth": 10,
            "tick_interval_seconds": 1,
            "candle_intervals": ["1m", "5m", "15m", "1h", "4h", "1d"],
            "exchanges": {
                "binance": {
                    "symbols": ["BTC/USDT", "ETH/USDT"]
                }
            }
        }
        
        # Créer le gestionnaire de données
        self.market_data_manager = MarketDataManager(self.exchanges, self.config)
    
    def tearDown(self):
        """
        Nettoie l'environnement de test après chaque test.
        """
        # Arrêter le gestionnaire de données s'il est en cours d'exécution
        if hasattr(self, "market_data_manager") and self.market_data_manager.running:
            self.market_data_manager.stop()
    
    def test_initialization(self):
        """
        Teste l'initialisation du gestionnaire de données.
        """
        # Vérifier que le gestionnaire de données est correctement initialisé
        self.assertEqual(self.market_data_manager.cache_enabled, True)
        self.assertEqual(self.market_data_manager.cache_expiry_seconds, 10)
        self.assertEqual(self.market_data_manager.historical_data_days, 1)
        self.assertEqual(self.market_data_manager.use_websockets, False)
        self.assertEqual(self.market_data_manager.order_book_depth, 10)
        self.assertEqual(self.market_data_manager.tick_interval_seconds, 1)
        self.assertEqual(self.market_data_manager.candle_intervals, ["1m", "5m", "15m", "1h", "4h", "1d"])
        
        # Vérifier que les structures de données sont initialisées
        self.assertEqual(self.market_data_manager.tickers, {})
        self.assertEqual(self.market_data_manager.order_books, {})
        self.assertEqual(self.market_data_manager.trades, {})
        self.assertEqual(self.market_data_manager.candles, {})
        
        # Vérifier que le gestionnaire de données n'est pas en cours d'exécution
        self.assertEqual(self.market_data_manager.running, False)
    
    def test_start_stop(self):
        """
        Teste le démarrage et l'arrêt du gestionnaire de données.
        """
        # Démarrer le gestionnaire de données
        self.market_data_manager.start()
        
        # Vérifier que le gestionnaire de données est en cours d'exécution
        self.assertEqual(self.market_data_manager.running, True)
        self.assertIsNotNone(self.market_data_manager.update_thread)
        
        # Attendre un peu pour que le thread démarre
        time.sleep(0.1)
        
        # Arrêter le gestionnaire de données
        self.market_data_manager.stop()
        
        # Vérifier que le gestionnaire de données est arrêté
        self.assertEqual(self.market_data_manager.running, False)
    
    def test_get_ticker(self):
        """
        Teste la récupération d'un ticker.
        """
        # Récupérer un ticker
        ticker = self.market_data_manager.get_ticker("BTC/USDT", "binance")
        
        # Vérifier que le ticker est correctement récupéré
        self.assertIsNotNone(ticker)
        self.assertEqual(ticker["symbol"], "BTC/USDT")
        self.assertEqual(ticker["bid"], 50000.0)
        self.assertEqual(ticker["ask"], 50100.0)
        
        # Vérifier que le mock a été appelé
        self.mock_exchange.fetch_ticker.assert_called_once_with("BTC/USDT")
    
    def test_get_order_book(self):
        """
        Teste la récupération d'un carnet d'ordres.
        """
        # Récupérer un carnet d'ordres
        order_book = self.market_data_manager.get_order_book("BTC/USDT", "binance")
        
        # Vérifier que le carnet d'ordres est correctement récupéré
        self.assertIsNotNone(order_book)
        self.assertEqual(len(order_book["bids"]), 3)
        self.assertEqual(len(order_book["asks"]), 3)
        self.assertEqual(order_book["bids"][0][0], 50000.0)
        self.assertEqual(order_book["asks"][0][0], 50100.0)
        
        # Vérifier que le mock a été appelé
        self.mock_exchange.fetch_order_book.assert_called_once_with("BTC/USDT", 10)
    
    def test_get_recent_candles(self):
        """
        Teste la récupération des bougies OHLCV récentes.
        """
        # Récupérer les bougies OHLCV récentes
        candles = self.market_data_manager.get_recent_candles("BTC/USDT", "1h", 3, "binance")
        
        # Vérifier que les bougies sont correctement récupérées
        self.assertIsNotNone(candles)
        self.assertEqual(len(candles), 3)
        
        # Vérifier que le mock a été appelé
        self.mock_exchange.fetch_ohlcv.assert_called_once()
    
    def test_get_volatility(self):
        """
        Teste le calcul de la volatilité.
        """
        # Configurer le mock pour renvoyer des prix spécifiques
        self.market_data_manager.get_recent_prices = MagicMock(return_value=[
            50000.0, 50100.0, 50200.0, 50150.0, 50050.0
        ])
        
        # Calculer la volatilité
        volatility = self.market_data_manager.get_volatility("BTC/USDT", 5, "1h", "binance")
        
        # Vérifier que la volatilité est correctement calculée
        self.assertIsNotNone(volatility)
        self.assertGreaterEqual(volatility, 0.0)
        
        # Vérifier que le mock a été appelé
        self.market_data_manager.get_recent_prices.assert_called_once_with("BTC/USDT", "1h", 6, "binance")
    
    def test_get_trend_indicator(self):
        """
        Teste le calcul de l'indicateur de tendance.
        """
        # Configurer le mock pour renvoyer des prix spécifiques
        self.market_data_manager.get_recent_prices = MagicMock(return_value=[
            50000.0, 50100.0, 50200.0, 50300.0, 50400.0
        ])
        
        # Calculer l'indicateur de tendance
        trend = self.market_data_manager.get_trend_indicator("BTC/USDT", 5, "1h", "binance")
        
        # Vérifier que l'indicateur de tendance est correctement calculé
        self.assertIsNotNone(trend)
        self.assertGreaterEqual(trend, 0.0)  # Tendance haussière
        
        # Vérifier que le mock a été appelé
        self.market_data_manager.get_recent_prices.assert_called_once_with("BTC/USDT", "1h", 5, "binance")
    
    def test_get_current_spread(self):
        """
        Teste le calcul du spread actuel.
        """
        # Configurer le mock pour renvoyer un ticker spécifique
        self.market_data_manager.get_ticker = MagicMock(return_value={
            "bid": 50000.0,
            "ask": 50100.0
        })
        
        # Calculer le spread actuel
        spread = self.market_data_manager.get_current_spread("BTC/USDT", "binance")
        
        # Vérifier que le spread est correctement calculé
        self.assertIsNotNone(spread)
        self.assertEqual(spread, 0.2)  # (50100 - 50000) / 50050 * 100 = 0.2%
        
        # Vérifier que le mock a été appelé
        self.market_data_manager.get_ticker.assert_called_once_with("BTC/USDT", "binance")
    
    def test_get_order_book_depth(self):
        """
        Teste le calcul de la profondeur du carnet d'ordres.
        """
        # Configurer le mock pour renvoyer un carnet d'ordres spécifique
        self.market_data_manager.get_order_book = MagicMock(return_value={
            "bids": [[50000.0, 1.0], [49900.0, 2.0], [49800.0, 3.0]],
            "asks": [[50100.0, 1.0], [50200.0, 2.0], [50300.0, 3.0]]
        })
        
        # Calculer la profondeur du carnet d'ordres
        depth = self.market_data_manager.get_order_book_depth("BTC/USDT", "binance")
        
        # Vérifier que la profondeur est correctement calculée
        self.assertIsNotNone(depth)
        self.assertEqual(depth, 0.12)  # (1+2+3+1+2+3) / 100 = 0.12
        
        # Vérifier que le mock a été appelé
        self.market_data_manager.get_order_book.assert_called_once_with("BTC/USDT", "binance")
    
    def test_update(self):
        """
        Teste la mise à jour manuelle des données de marché.
        """
        # Mettre à jour les données de marché
        self.market_data_manager.update()
        
        # Vérifier que les mocks ont été appelés
        self.mock_exchange.fetch_ticker.assert_called()
        self.mock_exchange.fetch_order_book.assert_called()
        self.mock_exchange.fetch_ohlcv.assert_called()
    
    def test_cache_expiry(self):
        """
        Teste l'expiration du cache.
        """
        # Configurer le gestionnaire de données pour un cache à courte durée
        self.market_data_manager.cache_expiry_seconds = 0.1
        
        # Récupérer un ticker (première requête)
        ticker1 = self.market_data_manager.get_ticker("BTC/USDT", "binance")
        
        # Vérifier que le mock a été appelé une fois
        self.assertEqual(self.mock_exchange.fetch_ticker.call_count, 1)
        
        # Récupérer à nouveau le ticker (devrait utiliser le cache)
        ticker2 = self.market_data_manager.get_ticker("BTC/USDT", "binance")
        
        # Vérifier que le mock n'a pas été appelé à nouveau
        self.assertEqual(self.mock_exchange.fetch_ticker.call_count, 1)
        
        # Attendre que le cache expire
        time.sleep(0.2)
        
        # Récupérer à nouveau le ticker (le cache devrait être expiré)
        ticker3 = self.market_data_manager.get_ticker("BTC/USDT", "binance")
        
        # Vérifier que le mock a été appelé à nouveau
        self.assertEqual(self.mock_exchange.fetch_ticker.call_count, 2)


if __name__ == "__main__":
    unittest.main()
