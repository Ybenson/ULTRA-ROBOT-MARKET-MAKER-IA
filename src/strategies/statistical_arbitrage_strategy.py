#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Stratégie d'arbitrage statistique pour ULTRA-ROBOT MARKET MAKER IA.

Cette stratégie recherche des opportunités d'arbitrage statistique entre des paires
d'actifs corrélés, en exploitant les déviations temporaires de leur relation historique.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple, Union
from loguru import logger
from datetime import datetime, timedelta

from src.strategies.base_strategy import BaseStrategy
from src.data.market_data_manager import MarketDataManager


class StatisticalArbitrageStrategy(BaseStrategy):
    """
    Stratégie d'arbitrage statistique.
    
    Cette stratégie identifie des paires d'actifs corrélés et exploite les déviations
    temporaires de leur relation historique pour générer des profits.
    """
    
    def __init__(self, config: Dict[str, Any], market_data_manager: MarketDataManager):
        """
        Initialise la stratégie d'arbitrage statistique.
        
        Args:
            config: Configuration de la stratégie.
            market_data_manager: Gestionnaire de données de marché.
        """
        super().__init__(config, market_data_manager)
        
        # Paramètres de configuration
        self.pairs = config.get("pairs", [])  # Liste des paires à surveiller
        self.lookback_period = config.get("lookback_period", 30)  # Période d'historique en jours
        self.z_score_threshold = config.get("z_score_threshold", 2.0)  # Seuil de Z-score pour les signaux
        self.position_size_pct = config.get("position_size_pct", 0.1)  # Taille de position en % du capital
        self.max_positions = config.get("max_positions", 5)  # Nombre maximum de positions simultanées
        self.profit_target_pct = config.get("profit_target_pct", 0.02)  # Objectif de profit en %
        self.stop_loss_pct = config.get("stop_loss_pct", 0.05)  # Stop loss en %
        self.timeframe = config.get("timeframe", "1h")  # Intervalle des données
        self.rebalance_interval = config.get("rebalance_interval", 24)  # Intervalle de rééquilibrage en heures
        
        # État interne
        self.pair_models = {}  # Modèles pour chaque paire
        self.active_positions = {}  # Positions actives
        self.last_rebalance_time = datetime.now()
        
        # Initialiser les modèles
        self._initialize_models()
        
        logger.info("Stratégie d'arbitrage statistique initialisée")
    
    def _initialize_models(self):
        """
        Initialise les modèles pour chaque paire.
        """
        for pair_config in self.pairs:
            try:
                pair_id = f"{pair_config['asset1']}_{pair_config['asset2']}"
                
                # Récupérer les données historiques
                asset1_prices = self._get_historical_prices(pair_config["asset1"], pair_config.get("exchange1"))
                asset2_prices = self._get_historical_prices(pair_config["asset2"], pair_config.get("exchange2"))
                
                if asset1_prices is None or asset2_prices is None:
                    logger.warning(f"Données insuffisantes pour la paire {pair_id}, modèle non initialisé")
                    continue
                
                # Calculer la régression linéaire
                slope, intercept, correlation = self._calculate_regression(asset1_prices, asset2_prices)
                
                # Calculer la série de spread
                spread_series = self._calculate_spread_series(asset1_prices, asset2_prices, slope, intercept)
                
                # Calculer les statistiques du spread
                spread_mean = np.mean(spread_series)
                spread_std = np.std(spread_series)
                
                # Stocker le modèle
                self.pair_models[pair_id] = {
                    "asset1": pair_config["asset1"],
                    "asset2": pair_config["asset2"],
                    "exchange1": pair_config.get("exchange1"),
                    "exchange2": pair_config.get("exchange2"),
                    "slope": slope,
                    "intercept": intercept,
                    "correlation": correlation,
                    "spread_mean": spread_mean,
                    "spread_std": spread_std,
                    "last_update": datetime.now()
                }
                
                logger.info(f"Modèle initialisé pour la paire {pair_id} avec corrélation {correlation:.2f}")
                
            except Exception as e:
                logger.error(f"Erreur lors de l'initialisation du modèle pour la paire {pair_config}: {str(e)}")
    
    def _get_historical_prices(self, symbol: str, exchange_id: Optional[str] = None) -> Optional[List[float]]:
        """
        Récupère les prix historiques pour un symbole.
        
        Args:
            symbol: Symbole de l'actif.
            exchange_id: Identifiant de l'exchange.
            
        Returns:
            Liste des prix historiques, ou None si non disponible.
        """
        try:
            # Calculer le nombre de bougies nécessaires
            candle_intervals = {
                "1m": 60 * 24 * self.lookback_period,
                "5m": 12 * 24 * self.lookback_period,
                "15m": 4 * 24 * self.lookback_period,
                "1h": 24 * self.lookback_period,
                "4h": 6 * self.lookback_period,
                "1d": self.lookback_period
            }
            
            limit = candle_intervals.get(self.timeframe, 100)
            
            # Récupérer les bougies
            candles = self.market_data_manager.get_recent_candles(
                symbol=symbol,
                interval=self.timeframe,
                limit=limit,
                exchange_id=exchange_id
            )
            
            if not candles or len(candles) < 30:  # Minimum 30 points de données
                logger.warning(f"Données insuffisantes pour {symbol}")
                return None
            
            # Extraire les prix de clôture
            prices = [candle["close"] for candle in candles]
            
            return prices
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des prix historiques pour {symbol}: {str(e)}")
            return None
    
    def _calculate_regression(self, x_prices: List[float], y_prices: List[float]) -> Tuple[float, float, float]:
        """
        Calcule la régression linéaire entre deux séries de prix.
        
        Args:
            x_prices: Prix de l'actif X.
            y_prices: Prix de l'actif Y.
            
        Returns:
            Tuple contenant la pente, l'ordonnée à l'origine et la corrélation.
        """
        # Assurer que les séries ont la même longueur
        min_length = min(len(x_prices), len(y_prices))
        x_prices = x_prices[-min_length:]
        y_prices = y_prices[-min_length:]
        
        # Convertir en arrays numpy
        x = np.array(x_prices)
        y = np.array(y_prices)
        
        # Calculer la régression linéaire
        slope, intercept = np.polyfit(x, y, 1)
        
        # Calculer la corrélation
        correlation = np.corrcoef(x, y)[0, 1]
        
        return slope, intercept, correlation
    
    def _calculate_spread_series(self, x_prices: List[float], y_prices: List[float], 
                                slope: float, intercept: float) -> List[float]:
        """
        Calcule la série de spread entre deux actifs.
        
        Args:
            x_prices: Prix de l'actif X.
            y_prices: Prix de l'actif Y.
            slope: Pente de la régression.
            intercept: Ordonnée à l'origine de la régression.
            
        Returns:
            Série de spread.
        """
        # Assurer que les séries ont la même longueur
        min_length = min(len(x_prices), len(y_prices))
        x_prices = x_prices[-min_length:]
        y_prices = y_prices[-min_length:]
        
        # Convertir en arrays numpy
        x = np.array(x_prices)
        y = np.array(y_prices)
        
        # Calculer la valeur théorique de Y
        y_hat = slope * x + intercept
        
        # Calculer le spread (différence entre Y réel et Y théorique)
        spread = y - y_hat
        
        return spread.tolist()
    
    def _calculate_z_score(self, current_spread: float, pair_id: str) -> float:
        """
        Calcule le Z-score pour un spread actuel.
        
        Args:
            current_spread: Spread actuel.
            pair_id: Identifiant de la paire.
            
        Returns:
            Z-score du spread.
        """
        model = self.pair_models.get(pair_id)
        if not model:
            return 0.0
        
        spread_mean = model["spread_mean"]
        spread_std = model["spread_std"]
        
        if spread_std == 0:
            return 0.0
        
        z_score = (current_spread - spread_mean) / spread_std
        
        return z_score
    
    def _update_models(self):
        """
        Met à jour les modèles pour toutes les paires.
        """
        for pair_id, model in self.pair_models.items():
            try:
                # Vérifier si une mise à jour est nécessaire
                time_since_update = datetime.now() - model["last_update"]
                if time_since_update < timedelta(hours=24):
                    continue
                
                # Récupérer les données historiques
                asset1_prices = self._get_historical_prices(model["asset1"], model.get("exchange1"))
                asset2_prices = self._get_historical_prices(model["asset2"], model.get("exchange2"))
                
                if asset1_prices is None or asset2_prices is None:
                    logger.warning(f"Données insuffisantes pour la paire {pair_id}, modèle non mis à jour")
                    continue
                
                # Calculer la régression linéaire
                slope, intercept, correlation = self._calculate_regression(asset1_prices, asset2_prices)
                
                # Calculer la série de spread
                spread_series = self._calculate_spread_series(asset1_prices, asset2_prices, slope, intercept)
                
                # Calculer les statistiques du spread
                spread_mean = np.mean(spread_series)
                spread_std = np.std(spread_series)
                
                # Mettre à jour le modèle
                model["slope"] = slope
                model["intercept"] = intercept
                model["correlation"] = correlation
                model["spread_mean"] = spread_mean
                model["spread_std"] = spread_std
                model["last_update"] = datetime.now()
                
                logger.info(f"Modèle mis à jour pour la paire {pair_id} avec corrélation {correlation:.2f}")
                
            except Exception as e:
                logger.error(f"Erreur lors de la mise à jour du modèle pour la paire {pair_id}: {str(e)}")
    
    def _check_rebalance(self):
        """
        Vérifie si un rééquilibrage est nécessaire.
        
        Returns:
            True si un rééquilibrage est nécessaire, False sinon.
        """
        time_since_rebalance = datetime.now() - self.last_rebalance_time
        return time_since_rebalance >= timedelta(hours=self.rebalance_interval)
    
    def _get_position_size(self, symbol: str, exchange_id: Optional[str] = None) -> float:
        """
        Calcule la taille de position pour un symbole.
        
        Args:
            symbol: Symbole de l'actif.
            exchange_id: Identifiant de l'exchange.
            
        Returns:
            Taille de position.
        """
        # Cette méthode devrait être adaptée en fonction de la logique de gestion du capital
        # Pour simplifier, nous utilisons un pourcentage fixe du capital disponible
        
        # Exemple: 10% du capital disponible
        return self.position_size_pct
    
    def update(self):
        """
        Met à jour la stratégie.
        
        Cette méthode est appelée périodiquement pour mettre à jour
        l'état de la stratégie et générer des signaux.
        """
        try:
            # Mettre à jour les modèles si nécessaire
            self._update_models()
            
            # Vérifier si un rééquilibrage est nécessaire
            if self._check_rebalance():
                self._rebalance_portfolio()
                self.last_rebalance_time = datetime.now()
            
            # Vérifier les opportunités d'arbitrage
            self._check_arbitrage_opportunities()
            
            # Gérer les positions existantes
            self._manage_positions()
            
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour de la stratégie d'arbitrage statistique: {str(e)}")
    
    def _rebalance_portfolio(self):
        """
        Rééquilibre le portefeuille.
        """
        logger.info("Rééquilibrage du portefeuille")
        
        # Logique de rééquilibrage à implémenter
        # Par exemple, fermer les positions les moins performantes
        # et allouer le capital aux meilleures opportunités
    
    def _check_arbitrage_opportunities(self):
        """
        Vérifie les opportunités d'arbitrage statistique.
        """
        # Vérifier si nous pouvons ouvrir de nouvelles positions
        if len(self.active_positions) >= self.max_positions:
            return
        
        for pair_id, model in self.pair_models.items():
            try:
                # Vérifier si nous avons déjà une position sur cette paire
                if pair_id in self.active_positions:
                    continue
                
                # Récupérer les prix actuels
                asset1_price = self._get_current_price(model["asset1"], model.get("exchange1"))
                asset2_price = self._get_current_price(model["asset2"], model.get("exchange2"))
                
                if asset1_price is None or asset2_price is None:
                    continue
                
                # Calculer le spread actuel
                current_spread = asset2_price - (model["slope"] * asset1_price + model["intercept"])
                
                # Calculer le Z-score
                z_score = self._calculate_z_score(current_spread, pair_id)
                
                # Générer des signaux en fonction du Z-score
                if z_score > self.z_score_threshold:
                    # Spread trop élevé: vendre asset2, acheter asset1
                    self._open_arbitrage_position(pair_id, "short", asset1_price, asset2_price, z_score)
                    
                elif z_score < -self.z_score_threshold:
                    # Spread trop bas: acheter asset2, vendre asset1
                    self._open_arbitrage_position(pair_id, "long", asset1_price, asset2_price, z_score)
                
            except Exception as e:
                logger.error(f"Erreur lors de la vérification des opportunités pour la paire {pair_id}: {str(e)}")
    
    def _get_current_price(self, symbol: str, exchange_id: Optional[str] = None) -> Optional[float]:
        """
        Récupère le prix actuel d'un symbole.
        
        Args:
            symbol: Symbole de l'actif.
            exchange_id: Identifiant de l'exchange.
            
        Returns:
            Prix actuel, ou None si non disponible.
        """
        try:
            ticker = self.market_data_manager.get_ticker(symbol, exchange_id)
            if ticker and "last" in ticker:
                return ticker["last"]
            return None
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du prix pour {symbol}: {str(e)}")
            return None
    
    def _open_arbitrage_position(self, pair_id: str, direction: str, asset1_price: float, 
                               asset2_price: float, z_score: float):
        """
        Ouvre une position d'arbitrage statistique.
        
        Args:
            pair_id: Identifiant de la paire.
            direction: Direction de la position ('long' ou 'short').
            asset1_price: Prix de l'actif 1.
            asset2_price: Prix de l'actif 2.
            z_score: Z-score actuel.
        """
        try:
            # Vérifier si nous pouvons ouvrir une nouvelle position
            if len(self.active_positions) >= self.max_positions:
                return
            
            model = self.pair_models.get(pair_id)
            if not model:
                return
            
            # Calculer les tailles de position
            position_size1 = self._get_position_size(model["asset1"], model.get("exchange1"))
            position_size2 = self._get_position_size(model["asset2"], model.get("exchange2"))
            
            # Ajuster les tailles pour maintenir une position neutre en valeur
            ratio = model["slope"]
            if direction == "long":
                # Acheter asset2, vendre asset1
                asset1_amount = position_size1 / asset1_price
                asset2_amount = (position_size1 * ratio) / asset2_price
                
                # Créer les ordres
                order1 = self._create_order(model["asset1"], "sell", asset1_amount, model.get("exchange1"))
                order2 = self._create_order(model["asset2"], "buy", asset2_amount, model.get("exchange2"))
                
            else:  # direction == "short"
                # Vendre asset2, acheter asset1
                asset1_amount = position_size1 / asset1_price
                asset2_amount = (position_size1 * ratio) / asset2_price
                
                # Créer les ordres
                order1 = self._create_order(model["asset1"], "buy", asset1_amount, model.get("exchange1"))
                order2 = self._create_order(model["asset2"], "sell", asset2_amount, model.get("exchange2"))
            
            # Enregistrer la position
            if order1 and order2:
                self.active_positions[pair_id] = {
                    "direction": direction,
                    "asset1": model["asset1"],
                    "asset2": model["asset2"],
                    "exchange1": model.get("exchange1"),
                    "exchange2": model.get("exchange2"),
                    "entry_asset1_price": asset1_price,
                    "entry_asset2_price": asset2_price,
                    "entry_spread": asset2_price - (model["slope"] * asset1_price + model["intercept"]),
                    "entry_z_score": z_score,
                    "asset1_amount": asset1_amount,
                    "asset2_amount": asset2_amount,
                    "order1_id": order1.get("id"),
                    "order2_id": order2.get("id"),
                    "entry_time": datetime.now(),
                    "target_z_score": 0.0,  # Cible: retour à la moyenne
                    "stop_loss_z_score": z_score * (1 + self.stop_loss_pct * (1 if direction == "long" else -1))
                }
                
                logger.info(f"Position d'arbitrage ouverte pour {pair_id} en direction {direction} avec Z-score {z_score:.2f}")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'ouverture de la position pour {pair_id}: {str(e)}")
    
    def _create_order(self, symbol: str, side: str, amount: float, exchange_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Crée un ordre.
        
        Args:
            symbol: Symbole de l'actif.
            side: Côté de l'ordre ('buy' ou 'sell').
            amount: Quantité à acheter/vendre.
            exchange_id: Identifiant de l'exchange.
            
        Returns:
            Informations sur l'ordre créé.
        """
        # Cette méthode devrait être implémentée pour créer un ordre réel
        # via l'exécuteur d'ordres du bot
        
        # Pour l'exemple, nous retournons un ordre fictif
        return {
            "id": f"order_{symbol}_{side}_{int(time.time())}",
            "symbol": symbol,
            "side": side,
            "amount": amount,
            "status": "open"
        }
    
    def _manage_positions(self):
        """
        Gère les positions existantes.
        """
        positions_to_close = []
        
        for pair_id, position in self.active_positions.items():
            try:
                model = self.pair_models.get(pair_id)
                if not model:
                    continue
                
                # Récupérer les prix actuels
                asset1_price = self._get_current_price(position["asset1"], position.get("exchange1"))
                asset2_price = self._get_current_price(position["asset2"], position.get("exchange2"))
                
                if asset1_price is None or asset2_price is None:
                    continue
                
                # Calculer le spread actuel
                current_spread = asset2_price - (model["slope"] * asset1_price + model["intercept"])
                
                # Calculer le Z-score actuel
                current_z_score = self._calculate_z_score(current_spread, pair_id)
                
                # Vérifier les conditions de clôture
                if position["direction"] == "long":
                    # Position longue: acheter asset2, vendre asset1
                    # Fermer si le Z-score est revenu à la cible ou a atteint le stop loss
                    if (current_z_score >= position["target_z_score"] or 
                        current_z_score <= position["stop_loss_z_score"]):
                        positions_to_close.append(pair_id)
                        
                else:  # position["direction"] == "short"
                    # Position courte: vendre asset2, acheter asset1
                    # Fermer si le Z-score est revenu à la cible ou a atteint le stop loss
                    if (current_z_score <= position["target_z_score"] or 
                        current_z_score >= position["stop_loss_z_score"]):
                        positions_to_close.append(pair_id)
                
            except Exception as e:
                logger.error(f"Erreur lors de la gestion de la position pour {pair_id}: {str(e)}")
        
        # Fermer les positions
        for pair_id in positions_to_close:
            self._close_position(pair_id)
    
    def _close_position(self, pair_id: str):
        """
        Ferme une position d'arbitrage statistique.
        
        Args:
            pair_id: Identifiant de la paire.
        """
        try:
            position = self.active_positions.get(pair_id)
            if not position:
                return
            
            # Créer les ordres de clôture
            if position["direction"] == "long":
                # Fermer une position longue: vendre asset2, acheter asset1
                order1 = self._create_order(position["asset1"], "buy", position["asset1_amount"], position.get("exchange1"))
                order2 = self._create_order(position["asset2"], "sell", position["asset2_amount"], position.get("exchange2"))
                
            else:  # position["direction"] == "short"
                # Fermer une position courte: acheter asset2, vendre asset1
                order1 = self._create_order(position["asset1"], "sell", position["asset1_amount"], position.get("exchange1"))
                order2 = self._create_order(position["asset2"], "buy", position["asset2_amount"], position.get("exchange2"))
            
            # Calculer le P&L
            asset1_price = self._get_current_price(position["asset1"], position.get("exchange1"))
            asset2_price = self._get_current_price(position["asset2"], position.get("exchange2"))
            
            if asset1_price and asset2_price:
                if position["direction"] == "long":
                    # P&L = (asset2_exit - asset2_entry) - (asset1_exit - asset1_entry) * ratio
                    pnl = ((asset2_price - position["entry_asset2_price"]) * position["asset2_amount"] - 
                           (asset1_price - position["entry_asset1_price"]) * position["asset1_amount"])
                else:
                    # P&L = (asset2_entry - asset2_exit) - (asset1_entry - asset1_exit) * ratio
                    pnl = ((position["entry_asset2_price"] - asset2_price) * position["asset2_amount"] - 
                           (position["entry_asset1_price"] - asset1_price) * position["asset1_amount"])
                
                logger.info(f"Position fermée pour {pair_id} avec P&L {pnl:.2f}")
            
            # Supprimer la position
            del self.active_positions[pair_id]
            
        except Exception as e:
            logger.error(f"Erreur lors de la fermeture de la position pour {pair_id}: {str(e)}")
    
    def get_active_positions(self) -> Dict[str, Dict[str, Any]]:
        """
        Récupère les positions actives.
        
        Returns:
            Dictionnaire des positions actives.
        """
        return self.active_positions
    
    def get_pair_models(self) -> Dict[str, Dict[str, Any]]:
        """
        Récupère les modèles de paires.
        
        Returns:
            Dictionnaire des modèles de paires.
        """
        return self.pair_models
