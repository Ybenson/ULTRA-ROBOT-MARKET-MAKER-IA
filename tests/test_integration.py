#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests d'intégration pour ULTRA-ROBOT MARKET MAKER IA.

Ce module contient des tests d'intégration qui valident le fonctionnement
de l'ensemble du bot de market making.
"""

import unittest
import time
import threading
import os
import yaml
from unittest.mock import MagicMock, patch
from typing import Dict, Any

# Importer les composants du bot
from src.data.market_data_manager import MarketDataManager
from src.exchanges.binance_exchange import BinanceExchange
from src.strategies.market_making_strategy import MarketMakingStrategy
from src.strategies.adaptive_market_making_strategy import AdaptiveMarketMakingStrategy
from src.strategies.statistical_arbitrage_strategy import StatisticalArbitrageStrategy
from src.strategies.combined_strategy import CombinedStrategy
from src.risk_management.risk_manager import RiskManager
from src.execution.order_executor import OrderExecutor
from src.monitoring.monitor import Monitor
from src.core.engine import MarketMakingEngine


class TestIntegration(unittest.TestCase):
    """
    Tests d'intégration pour le bot de market making.
    """
    
    def setUp(self):
        """
        Initialise l'environnement de test avant chaque test.
        """
        # Charger la configuration de test
        self.config = self._load_test_config()
        
        # Créer des mocks pour les exchanges
        self.mock_exchange = MagicMock(spec=BinanceExchange)
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
        
        # Configurer les méthodes d'exécution d'ordres
        self.mock_exchange.create_limit_buy_order.return_value = {
            "id": "123456",
            "symbol": "BTC/USDT",
            "type": "limit",
            "side": "buy",
            "price": 50000.0,
            "amount": 0.1,
            "status": "open",
            "timestamp": int(time.time() * 1000)
        }
        
        self.mock_exchange.create_limit_sell_order.return_value = {
            "id": "654321",
            "symbol": "BTC/USDT",
            "type": "limit",
            "side": "sell",
            "price": 50100.0,
            "amount": 0.1,
            "status": "open",
            "timestamp": int(time.time() * 1000)
        }
        
        self.mock_exchange.cancel_order.return_value = {
            "id": "123456",
            "status": "canceled"
        }
        
        self.exchanges = {"binance": self.mock_exchange}
        
        # Initialiser les composants du bot
        self._initialize_components()
    
    def tearDown(self):
        """
        Nettoie l'environnement de test après chaque test.
        """
        # Arrêter les composants s'ils sont en cours d'exécution
        if hasattr(self, "market_data_manager") and self.market_data_manager.running:
            self.market_data_manager.stop()
        
        if hasattr(self, "monitor") and self.monitor.running:
            self.monitor.stop()
        
        if hasattr(self, "strategies"):
            for strategy in self.strategies:
                if hasattr(strategy, "is_running") and strategy.is_running:
                    strategy.stop()
    
    def _load_test_config(self) -> Dict[str, Any]:
        """
        Charge la configuration de test.
        
        Returns:
            Configuration de test.
        """
        # Configuration de test par défaut
        return {
            "general": {
                "bot_name": "ULTRA-ROBOT-TEST",
                "mode": "simulation",
                "log_level": "INFO",
                "timezone": "UTC",
                "data_directory": "data"
            },
            "markets": {
                "enabled_markets": [
                    {
                        "id": "binance",
                        "type": "crypto",
                        "api_key_env": "BINANCE_API_KEY",
                        "api_secret_env": "BINANCE_API_SECRET",
                        "testnet": True
                    }
                ],
                "default_market": "binance",
                "symbols": ["BTC/USDT", "ETH/USDT"]
            },
            "strategies": {
                "enabled_strategies": [
                    {
                        "id": "mm_basic",
                        "type": "market_making",
                        "symbols": ["BTC/USDT"],
                        "parameters": {
                            "spread_bid": 0.1,
                            "spread_ask": 0.1,
                            "order_size": 0.01,
                            "order_count": 3,
                            "refresh_rate": 10,
                            "min_profit": 0.05,
                            "max_position": 1.0
                        }
                    },
                    {
                        "id": "stat_arb",
                        "type": "statistical_arbitrage",
                        "symbol_pairs": [["BTC/USDT", "ETH/USDT"]],
                        "parameters": {
                            "z_score_threshold": 2.0,
                            "half_life": 24,
                            "position_size": 0.01,
                            "max_position": 1.0
                        }
                    }
                ]
            },
            "risk_management": {
                "max_position_size": 1000,
                "max_drawdown_percent": 5.0,
                "stop_loss_percent": 2.0,
                "take_profit_percent": 5.0,
                "max_open_orders": 10,
                "manipulation_detection_enabled": True,
                "volatility_threshold": 3.0,
                "volume_spike_threshold": 5.0,
                "spread_anomaly_threshold": 3.0,
                "initial_capital": 10000
            },
            "execution": {
                "order_type": "limit",
                "max_slippage_percent": 0.1,
                "retry_attempts": 3,
                "retry_delay_seconds": 1,
                "use_iceberg_orders": False,
                "max_order_age_seconds": 300
            },
            "data": {
                "cache_enabled": True,
                "cache_expiry_seconds": 60,
                "historical_data_days": 30,
                "use_websockets": False,
                "order_book_depth": 10,
                "tick_interval_seconds": 1,
                "candle_intervals": ["1m", "5m", "15m", "1h", "4h", "1d"]
            },
            "monitoring": {
                "dashboard_enabled": False,
                "dashboard_port": 8050,
                "metrics_interval_seconds": 60,
                "alert_enabled": False,
                "performance_metrics": ["pnl", "sharpe_ratio", "drawdown", "win_rate", "volume"]
            }
        }
    
    def _initialize_components(self):
        """
        Initialise les composants du bot pour les tests.
        """
        # Initialiser le gestionnaire de données de marché
        self.market_data_manager = MarketDataManager(
            exchanges=self.exchanges,
            config=self.config.get("data", {})
        )
        
        # Initialiser le gestionnaire de risques
        self.risk_manager = RiskManager(
            config=self.config.get("risk_management", {}),
            market_data_manager=self.market_data_manager
        )
        
        # Initialiser l'exécuteur d'ordres
        self.order_executor = OrderExecutor(
            exchanges=self.exchanges,
            config=self.config.get("execution", {}),
            risk_manager=self.risk_manager
        )
        
        # Initialiser le moniteur
        self.monitor = Monitor(
            config=self.config.get("monitoring", {})
        )
        
        # Initialiser les stratégies
        self.strategies = []
        
        # Stratégie de market making de base
        mm_config = {
            "name": "MarketMaking",
            "enabled": True,
            "symbols": ["BTC/USDT"],
            "exchanges": ["binance"],
            "spread_bid": 0.1,
            "spread_ask": 0.1,
            "order_size": 0.01,
            "order_count": 3,
            "refresh_rate": 10,
            "min_profit": 0.05,
            "max_position": 1.0
        }
        
        mm_strategy = MarketMakingStrategy(
            strategy_id="mm_basic",
            market_data_manager=self.market_data_manager,
            order_executor=self.order_executor,
            risk_manager=self.risk_manager,
            config={"parameters": mm_config}
        )
        
        self.strategies.append(mm_strategy)
        
        # Stratégie d'arbitrage statistique
        arb_config = {
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
        
        arb_strategy = StatisticalArbitrageStrategy(
            arb_config,
            self.market_data_manager
        )
        
        self.strategies.append(arb_strategy)
        
        # Stratégie combinée
        combined_config = {
            "name": "CombinedStrategy",
            "enabled": True,
            "symbols": ["BTC/USDT", "ETH/USDT"],
            "exchanges": ["binance"],
            "weights": {
                "MarketMaking": 0.6,
                "StatisticalArbitrage": 0.4
            },
            "correlation_threshold": 0.7,
            "max_drawdown_threshold": 5.0,
            "rebalance_interval_hours": 24
        }
        
        combined_strategy = CombinedStrategy(
            combined_config,
            self.market_data_manager
        )
        
        # Ajouter les sous-stratégies
        combined_strategy.add_strategy(mm_strategy, 0.6)
        combined_strategy.add_strategy(arb_strategy, 0.4)
        
        self.strategies.append(combined_strategy)
    
    def test_market_data_manager_integration(self):
        """
        Teste l'intégration du gestionnaire de données de marché.
        """
        # Démarrer le gestionnaire de données
        self.market_data_manager.start()
        
        # Attendre un peu pour que le thread démarre
        time.sleep(0.1)
        
        # Vérifier que le gestionnaire de données est en cours d'exécution
        self.assertEqual(self.market_data_manager.running, True)
        
        # Récupérer un ticker
        ticker = self.market_data_manager.get_ticker("BTC/USDT", "binance")
        
        # Vérifier que le ticker est correctement récupéré
        self.assertIsNotNone(ticker)
        self.assertEqual(ticker["symbol"], "BTC/USDT")
        
        # Récupérer un carnet d'ordres
        order_book = self.market_data_manager.get_order_book("BTC/USDT", "binance")
        
        # Vérifier que le carnet d'ordres est correctement récupéré
        self.assertIsNotNone(order_book)
        self.assertEqual(len(order_book["bids"]), 3)
        
        # Calculer la volatilité
        volatility = self.market_data_manager.get_volatility("BTC/USDT", 3, "1h", "binance")
        
        # Vérifier que la volatilité est correctement calculée
        self.assertIsNotNone(volatility)
        
        # Arrêter le gestionnaire de données
        self.market_data_manager.stop()
        
        # Vérifier que le gestionnaire de données est arrêté
        self.assertEqual(self.market_data_manager.running, False)
    
    def test_risk_manager_integration(self):
        """
        Teste l'intégration du gestionnaire de risques.
        """
        # Vérifier la limite de position
        result = self.risk_manager.check_position_limit("BTC/USDT", "buy", 0.5)
        
        # La limite devrait être respectée
        self.assertTrue(result)
        
        # Vérifier la détection de manipulation
        is_manipulated = self.risk_manager.detect_market_manipulation("BTC/USDT", "binance")
        
        # Le marché ne devrait pas être considéré comme manipulé
        self.assertFalse(is_manipulated)
        
        # Vérifier le calcul du risque
        risk_score = self.risk_manager.calculate_risk_score("BTC/USDT", "binance")
        
        # Le score de risque devrait être calculé
        self.assertIsNotNone(risk_score)
        self.assertGreaterEqual(risk_score, 0.0)
        self.assertLessEqual(risk_score, 1.0)
    
    def test_order_executor_integration(self):
        """
        Teste l'intégration de l'exécuteur d'ordres.
        """
        # Placer un ordre d'achat
        order_id = self.order_executor.place_order(
            symbol="BTC/USDT",
            side="buy",
            order_type="limit",
            amount=0.1,
            price=50000.0,
            exchange_id="binance"
        )
        
        # Vérifier que l'ordre est correctement placé
        self.assertIsNotNone(order_id)
        
        # Récupérer l'ordre
        order = self.order_executor.get_order(order_id, "BTC/USDT", "binance")
        
        # Vérifier que l'ordre est correctement récupéré
        self.assertIsNotNone(order)
        self.assertEqual(order["id"], "123456")
        
        # Annuler l'ordre
        result = self.order_executor.cancel_order(order_id, "BTC/USDT", "binance")
        
        # Vérifier que l'ordre est correctement annulé
        self.assertTrue(result)
    
    def test_strategy_integration(self):
        """
        Teste l'intégration des stratégies.
        """
        # Démarrer le gestionnaire de données
        self.market_data_manager.start()
        
        # Attendre un peu pour que le thread démarre
        time.sleep(0.1)
        
        # Tester la stratégie de market making
        mm_strategy = self.strategies[0]
        mm_strategy.start()
        
        # Vérifier que la stratégie est en cours d'exécution
        self.assertTrue(mm_strategy.is_running)
        
        # Mettre à jour la stratégie
        mm_strategy.update()
        
        # Arrêter la stratégie
        mm_strategy.stop()
        
        # Vérifier que la stratégie est arrêtée
        self.assertFalse(mm_strategy.is_running)
        
        # Tester la stratégie d'arbitrage statistique
        arb_strategy = self.strategies[1]
        arb_strategy.start()
        
        # Vérifier que la stratégie est en cours d'exécution
        self.assertTrue(arb_strategy.is_running)
        
        # Mettre à jour la stratégie
        arb_strategy.update()
        
        # Arrêter la stratégie
        arb_strategy.stop()
        
        # Vérifier que la stratégie est arrêtée
        self.assertFalse(arb_strategy.is_running)
        
        # Tester la stratégie combinée
        combined_strategy = self.strategies[2]
        combined_strategy.start()
        
        # Vérifier que la stratégie est en cours d'exécution
        self.assertTrue(combined_strategy.is_running)
        
        # Mettre à jour la stratégie
        combined_strategy.update()
        
        # Récupérer les signaux
        signals = combined_strategy.get_signals("BTC/USDT", "binance")
        
        # Vérifier que les signaux sont correctement récupérés
        self.assertIsNotNone(signals)
        
        # Arrêter la stratégie
        combined_strategy.stop()
        
        # Vérifier que la stratégie est arrêtée
        self.assertFalse(combined_strategy.is_running)
        
        # Arrêter le gestionnaire de données
        self.market_data_manager.stop()
    
    def test_monitor_integration(self):
        """
        Teste l'intégration du moniteur.
        """
        # Démarrer le moniteur
        self.monitor.start()
        
        # Vérifier que le moniteur est en cours d'exécution
        self.assertTrue(self.monitor.running)
        
        # Ajouter une métrique
        self.monitor.add_metric("pnl", 100.0)
        
        # Récupérer la métrique
        metric = self.monitor.get_metrics("pnl")
        
        # Vérifier que la métrique est correctement récupérée
        self.assertIsNotNone(metric)
        self.assertEqual(metric["name"], "pnl")
        self.assertEqual(metric["values"][-1], 100.0)
        
        # Ajouter une alerte
        self.monitor.add_alert("test", "Alerte de test", "info")
        
        # Récupérer les alertes
        alerts = self.monitor.get_alerts()
        
        # Vérifier que l'alerte est correctement récupérée
        self.assertIsNotNone(alerts)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["type"], "test")
        self.assertEqual(alerts[0]["message"], "Alerte de test")
        
        # Arrêter le moniteur
        self.monitor.stop()
        
        # Vérifier que le moniteur est arrêté
        self.assertFalse(self.monitor.running)


if __name__ == "__main__":
    unittest.main()
