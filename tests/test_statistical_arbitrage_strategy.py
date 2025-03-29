#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests unitaires pour la stratégie d'arbitrage statistique.

Ce module contient les tests unitaires pour valider le fonctionnement
de la stratégie d'arbitrage statistique.
"""

import unittest
import time
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch
from typing import Dict, Any, List

from src.strategies.statistical_arbitrage_strategy import StatisticalArbitrageStrategy
from src.data.market_data_manager import MarketDataManager


class TestStatisticalArbitrageStrategy(unittest.TestCase):
    """
    Tests unitaires pour la stratégie d'arbitrage statistique.
    """
    
    def setUp(self):
        """
        Initialise l'environnement de test avant chaque test.
        """
        # Créer un mock pour le gestionnaire de données de marché
        self.market_data_manager = MagicMock(spec=MarketDataManager)
        
        # Configurer les mocks pour les méthodes du gestionnaire de données
        self.market_data_manager.get_recent_prices.return_value = [
            50000.0, 50100.0, 50200.0, 50300.0, 50400.0
        ]
        
        # Configuration pour la stratégie
        self.config = {
            "name": "StatisticalArbitrage",
            "enabled": True,
            "symbols": ["BTC/USDT", "ETH/USDT"],
            "exchanges": ["binance"],
            "lookback_period": 30,
            "z_score_threshold": 2.0,
            "position_size_usd": 1000.0,
            "max_positions": 5,
            "rebalance_interval_minutes": 60,
            "correlation_threshold": 0.7,
            "pairs": [
                {
                    "base": "BTC/USDT",
                    "quote": "ETH/USDT",
                    "exchange": "binance",
                    "hedge_ratio": 0.15
                }
            ]
        }
        
        # Créer la stratégie
        self.strategy = StatisticalArbitrageStrategy(self.config, self.market_data_manager)
        
        # Configurer les données historiques pour les tests
        self.btc_prices = pd.Series(
            [50000.0 + i * 100 for i in range(100)],
            index=pd.date_range(start="2023-01-01", periods=100, freq="H")
        )
        
        self.eth_prices = pd.Series(
            [3000.0 + i * 10 + np.random.normal(0, 50) for i in range(100)],
            index=pd.date_range(start="2023-01-01", periods=100, freq="H")
        )
        
        # Configurer le mock pour la méthode get_historical_prices
        def mock_get_historical_prices(symbol, interval, lookback, exchange_id):
            if symbol == "BTC/USDT":
                return self.btc_prices.values.tolist()
            elif symbol == "ETH/USDT":
                return self.eth_prices.values.tolist()
            else:
                return []
        
        self.market_data_manager.get_historical_prices.side_effect = mock_get_historical_prices
        
        # Configurer le mock pour la méthode get_ticker
        self.market_data_manager.get_ticker.return_value = {
            "bid": 50000.0,
            "ask": 50100.0,
            "last": 50050.0
        }
    
    def test_initialization(self):
        """
        Teste l'initialisation de la stratégie.
        """
        # Vérifier que la stratégie est correctement initialisée
        self.assertEqual(self.strategy.name, "StatisticalArbitrage")
        self.assertEqual(self.strategy.enabled, True)
        self.assertEqual(self.strategy.symbols, ["BTC/USDT", "ETH/USDT"])
        self.assertEqual(self.strategy.exchanges, ["binance"])
        self.assertEqual(self.strategy.lookback_period, 30)
        self.assertEqual(self.strategy.z_score_threshold, 2.0)
        self.assertEqual(self.strategy.position_size_usd, 1000.0)
        self.assertEqual(self.strategy.max_positions, 5)
        self.assertEqual(self.strategy.rebalance_interval_minutes, 60)
        self.assertEqual(self.strategy.correlation_threshold, 0.7)
        
        # Vérifier que les structures de données sont initialisées
        self.assertEqual(len(self.strategy.pairs), 1)
        self.assertEqual(self.strategy.pairs[0]["base"], "BTC/USDT")
        self.assertEqual(self.strategy.pairs[0]["quote"], "ETH/USDT")
        self.assertEqual(self.strategy.pairs[0]["exchange"], "binance")
        self.assertEqual(self.strategy.pairs[0]["hedge_ratio"], 0.15)
        
        # Vérifier que les positions sont initialisées
        self.assertEqual(self.strategy.positions, {})
    
    def test_initialize_model(self):
        """
        Teste l'initialisation du modèle d'arbitrage statistique.
        """
        # Initialiser le modèle
        pair = self.strategy.pairs[0]
        self.strategy._initialize_model(pair)
        
        # Vérifier que le modèle est correctement initialisé
        self.assertIn("model", pair)
        self.assertIn("spread_mean", pair)
        self.assertIn("spread_std", pair)
        self.assertIn("last_update_time", pair)
        
        # Vérifier que le gestionnaire de données a été appelé
        self.market_data_manager.get_historical_prices.assert_called()
    
    def test_calculate_z_score(self):
        """
        Teste le calcul du Z-score.
        """
        # Initialiser le modèle
        pair = self.strategy.pairs[0]
        self.strategy._initialize_model(pair)
        
        # Configurer les données pour le test
        pair["spread_mean"] = 0.0
        pair["spread_std"] = 1.0
        
        # Calculer le Z-score
        z_score = self.strategy._calculate_z_score(2.0, pair)
        
        # Vérifier que le Z-score est correctement calculé
        self.assertEqual(z_score, 2.0)
    
    def test_get_current_prices(self):
        """
        Teste la récupération des prix actuels.
        """
        # Récupérer les prix actuels
        pair = self.strategy.pairs[0]
        base_price, quote_price = self.strategy._get_current_prices(pair)
        
        # Vérifier que les prix sont correctement récupérés
        self.assertEqual(base_price, 50050.0)
        self.assertEqual(quote_price, 50050.0)
        
        # Vérifier que le gestionnaire de données a été appelé
        self.market_data_manager.get_ticker.assert_called()
    
    def test_calculate_spread(self):
        """
        Teste le calcul du spread.
        """
        # Calculer le spread
        pair = self.strategy.pairs[0]
        spread = self.strategy._calculate_spread(50000.0, 3000.0, pair)
        
        # Vérifier que le spread est correctement calculé
        self.assertEqual(spread, 50000.0 - 0.15 * 3000.0)
    
    def test_should_open_position(self):
        """
        Teste la décision d'ouverture de position.
        """
        # Initialiser le modèle
        pair = self.strategy.pairs[0]
        self.strategy._initialize_model(pair)
        
        # Configurer les données pour le test
        pair["spread_mean"] = 0.0
        pair["spread_std"] = 1.0
        
        # Tester avec un Z-score au-dessus du seuil
        should_open, position_type = self.strategy._should_open_position(2.5, pair)
        self.assertTrue(should_open)
        self.assertEqual(position_type, "short")
        
        # Tester avec un Z-score en dessous du seuil négatif
        should_open, position_type = self.strategy._should_open_position(-2.5, pair)
        self.assertTrue(should_open)
        self.assertEqual(position_type, "long")
        
        # Tester avec un Z-score dans la plage normale
        should_open, position_type = self.strategy._should_open_position(1.0, pair)
        self.assertFalse(should_open)
        self.assertIsNone(position_type)
    
    def test_should_close_position(self):
        """
        Teste la décision de fermeture de position.
        """
        # Tester la fermeture d'une position longue
        should_close = self.strategy._should_close_position(0.5, "long")
        self.assertTrue(should_close)
        
        # Tester la fermeture d'une position courte
        should_close = self.strategy._should_close_position(-0.5, "short")
        self.assertTrue(should_close)
        
        # Tester le maintien d'une position longue
        should_close = self.strategy._should_close_position(-1.5, "long")
        self.assertFalse(should_close)
        
        # Tester le maintien d'une position courte
        should_close = self.strategy._should_close_position(1.5, "short")
        self.assertFalse(should_close)
    
    def test_open_position(self):
        """
        Teste l'ouverture d'une position.
        """
        # Ouvrir une position longue
        pair = self.strategy.pairs[0]
        position_id = self.strategy._open_position(pair, "long", 50000.0, 3000.0)
        
        # Vérifier que la position est correctement ouverte
        self.assertIn(position_id, self.strategy.positions)
        position = self.strategy.positions[position_id]
        self.assertEqual(position["pair_id"], f"{pair['base']}_{pair['quote']}_{pair['exchange']}")
        self.assertEqual(position["type"], "long")
        self.assertEqual(position["base_entry_price"], 50000.0)
        self.assertEqual(position["quote_entry_price"], 3000.0)
        self.assertIsNotNone(position["entry_time"])
        self.assertEqual(position["status"], "open")
    
    def test_close_position(self):
        """
        Teste la fermeture d'une position.
        """
        # Ouvrir une position
        pair = self.strategy.pairs[0]
        position_id = self.strategy._open_position(pair, "long", 50000.0, 3000.0)
        
        # Fermer la position
        self.strategy._close_position(position_id, 51000.0, 3100.0)
        
        # Vérifier que la position est correctement fermée
        position = self.strategy.positions[position_id]
        self.assertEqual(position["status"], "closed")
        self.assertEqual(position["base_exit_price"], 51000.0)
        self.assertEqual(position["quote_exit_price"], 3100.0)
        self.assertIsNotNone(position["exit_time"])
        self.assertIsNotNone(position["pnl"])
        self.assertIsNotNone(position["pnl_percent"])
    
    def test_calculate_pnl(self):
        """
        Teste le calcul du P&L.
        """
        # Calculer le P&L pour une position longue
        pair = self.strategy.pairs[0]
        pnl, pnl_percent = self.strategy._calculate_pnl(
            "long", 50000.0, 3000.0, 51000.0, 3100.0, pair
        )
        
        # Vérifier que le P&L est correctement calculé
        self.assertGreater(pnl, 0)  # Le P&L devrait être positif
        
        # Calculer le P&L pour une position courte
        pnl, pnl_percent = self.strategy._calculate_pnl(
            "short", 50000.0, 3000.0, 49000.0, 2900.0, pair
        )
        
        # Vérifier que le P&L est correctement calculé
        self.assertGreater(pnl, 0)  # Le P&L devrait être positif
    
    def test_update(self):
        """
        Teste la mise à jour de la stratégie.
        """
        # Initialiser les modèles
        for pair in self.strategy.pairs:
            self.strategy._initialize_model(pair)
        
        # Mettre à jour la stratégie
        self.strategy.update()
        
        # Vérifier que le gestionnaire de données a été appelé
        self.market_data_manager.get_ticker.assert_called()
    
    def test_rebalance(self):
        """
        Teste le rééquilibrage des positions.
        """
        # Initialiser les modèles
        for pair in self.strategy.pairs:
            self.strategy._initialize_model(pair)
        
        # Ouvrir une position
        pair = self.strategy.pairs[0]
        position_id = self.strategy._open_position(pair, "long", 50000.0, 3000.0)
        
        # Configurer la position pour qu'elle soit ouverte depuis longtemps
        self.strategy.positions[position_id]["entry_time"] = time.time() - 3600 * 24  # 24 heures
        
        # Rééquilibrer les positions
        self.strategy._rebalance()
        
        # Vérifier que la position a été fermée
        position = self.strategy.positions[position_id]
        self.assertEqual(position["status"], "closed")


if __name__ == "__main__":
    unittest.main()
