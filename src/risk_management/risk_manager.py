#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module de gestion des risques pour ULTRA-ROBOT MARKET MAKER IA.

Ce module implémente des stratégies avancées de gestion des risques pour protéger
le capital et optimiser les performances du bot de market making.
"""

import time
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from loguru import logger


class RiskManager:
    """
    Gestionnaire de risques avancé pour le bot de market making.
    
    Cette classe implémente diverses stratégies de gestion des risques, notamment:
    - Limites de position maximale
    - Stop-loss dynamiques
    - Protection contre les manipulations de marché
    - Gestion du drawdown
    - Couverture intelligente
    """
    
    def __init__(self, config: Dict[str, Any], market_data_manager=None):
        """
        Initialise le gestionnaire de risques.
        
        Args:
            config: Configuration de la gestion des risques.
            market_data_manager: Gestionnaire de données de marché pour l'analyse.
        """
        self.config = config
        self.market_data_manager = market_data_manager
        
        # Paramètres de gestion des risques
        self.max_position_size = config.get("max_position_size", 1000)
        self.max_drawdown_percent = config.get("max_drawdown_percent", 5.0)
        self.stop_loss_percent = config.get("stop_loss_percent", 2.0)
        self.take_profit_percent = config.get("take_profit_percent", 5.0)
        self.max_open_orders = config.get("max_open_orders", 10)
        
        # Paramètres de détection de manipulation
        self.manipulation_detection_enabled = config.get("manipulation_detection_enabled", True)
        self.volatility_threshold = config.get("volatility_threshold", 3.0)
        self.volume_spike_threshold = config.get("volume_spike_threshold", 5.0)
        self.spread_anomaly_threshold = config.get("spread_anomaly_threshold", 3.0)
        
        # État interne
        self.positions = {}  # Positions actuelles par symbole
        self.open_orders = {}  # Ordres ouverts par symbole
        self.initial_capital = config.get("initial_capital", 10000)
        self.current_capital = self.initial_capital
        self.peak_capital = self.initial_capital
        self.drawdown_history = []
        
        # Métriques de performance
        self.daily_pnl = []
        self.risk_metrics = {
            "sharpe_ratio": 0.0,
            "sortino_ratio": 0.0,
            "max_drawdown": 0.0,
            "volatility": 0.0,
            "win_rate": 0.0,
        }
        
        logger.info("Gestionnaire de risques initialisé")
    
    def check_position_limit(self, symbol: str, side: str, amount: float) -> bool:
        """
        Vérifie si une nouvelle position respecte les limites de position.
        
        Args:
            symbol: Symbole de l'actif.
            side: Côté de l'ordre ('buy' ou 'sell').
            amount: Montant de l'ordre.
            
        Returns:
            True si la position est dans les limites, False sinon.
        """
        current_position = self.positions.get(symbol, 0)
        
        # Calculer la nouvelle position
        new_position = current_position + amount if side == "buy" else current_position - amount
        
        # Vérifier si la position absolue dépasse la limite
        if abs(new_position) > self.max_position_size:
            logger.warning(f"Limite de position dépassée pour {symbol}: {abs(new_position)} > {self.max_position_size}")
            return False
        
        return True
    
    def check_drawdown_limit(self) -> bool:
        """
        Vérifie si le drawdown actuel dépasse la limite configurée.
        
        Returns:
            True si le drawdown est dans les limites, False sinon.
        """
        if self.current_capital <= 0 or self.peak_capital <= 0:
            return False
        
        # Calculer le drawdown actuel
        drawdown_percent = (1 - self.current_capital / self.peak_capital) * 100
        
        # Mettre à jour l'historique du drawdown
        self.drawdown_history.append(drawdown_percent)
        
        # Mettre à jour le drawdown maximum
        self.risk_metrics["max_drawdown"] = max(self.risk_metrics["max_drawdown"], drawdown_percent)
        
        # Vérifier si le drawdown dépasse la limite
        if drawdown_percent > self.max_drawdown_percent:
            logger.warning(f"Limite de drawdown dépassée: {drawdown_percent:.2f}% > {self.max_drawdown_percent}%")
            return False
        
        return True
    
    def calculate_dynamic_stop_loss(self, symbol: str, entry_price: float, side: str) -> float:
        """
        Calcule un niveau de stop-loss dynamique basé sur la volatilité du marché.
        
        Args:
            symbol: Symbole de l'actif.
            entry_price: Prix d'entrée de la position.
            side: Côté de la position ('long' ou 'short').
            
        Returns:
            Prix du stop-loss dynamique.
        """
        if not self.market_data_manager:
            # Utiliser un stop-loss fixe si le gestionnaire de données n'est pas disponible
            if side == "long":
                return entry_price * (1 - self.stop_loss_percent / 100)
            else:
                return entry_price * (1 + self.stop_loss_percent / 100)
        
        # Obtenir la volatilité récente
        volatility = self.market_data_manager.get_volatility(symbol, window=24)
        
        # Ajuster le pourcentage de stop-loss en fonction de la volatilité
        adjusted_stop_loss_percent = self.stop_loss_percent * (1 + volatility / 100)
        
        # Calculer le prix du stop-loss
        if side == "long":
            stop_loss_price = entry_price * (1 - adjusted_stop_loss_percent / 100)
        else:
            stop_loss_price = entry_price * (1 + adjusted_stop_loss_percent / 100)
        
        logger.debug(f"Stop-loss dynamique pour {symbol}: {stop_loss_price:.8f} (volatilité: {volatility:.2f}%)")
        return stop_loss_price
    
    def detect_market_manipulation(self, symbol: str) -> bool:
        """
        Détecte les signes potentiels de manipulation du marché.
        
        Args:
            symbol: Symbole de l'actif à analyser.
            
        Returns:
            True si une manipulation est détectée, False sinon.
        """
        if not self.manipulation_detection_enabled or not self.market_data_manager:
            return False
        
        try:
            # Obtenir les données récentes
            recent_candles = self.market_data_manager.get_recent_candles(symbol, limit=20)
            
            if not recent_candles or len(recent_candles) < 10:
                return False
            
            # Extraire les prix et volumes
            closes = [candle['close'] for candle in recent_candles]
            volumes = [candle['volume'] for candle in recent_candles]
            
            # Calculer les variations de prix
            returns = np.diff(closes) / closes[:-1] * 100
            
            # Calculer la volatilité récente (écart-type des rendements)
            volatility = np.std(returns)
            
            # Détecter les pics de volatilité
            if volatility > self.volatility_threshold * np.mean(np.abs(returns)):
                logger.warning(f"Pic de volatilité détecté pour {symbol}: {volatility:.2f}%")
                return True
            
            # Détecter les pics de volume
            avg_volume = np.mean(volumes[:-1])
            if volumes[-1] > self.volume_spike_threshold * avg_volume:
                logger.warning(f"Pic de volume détecté pour {symbol}: {volumes[-1]:.2f} > {self.volume_spike_threshold * avg_volume:.2f}")
                return True
            
            # Détecter les anomalies de spread si disponible
            if hasattr(self.market_data_manager, "get_current_spread"):
                current_spread = self.market_data_manager.get_current_spread(symbol)
                avg_spread = self.market_data_manager.get_average_spread(symbol, window=100)
                
                if current_spread > self.spread_anomaly_threshold * avg_spread:
                    logger.warning(f"Anomalie de spread détectée pour {symbol}: {current_spread:.8f} > {self.spread_anomaly_threshold * avg_spread:.8f}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Erreur lors de la détection de manipulation pour {symbol}: {str(e)}")
            return False
    
    def update_position(self, symbol: str, amount: float, price: float, side: str):
        """
        Met à jour les positions internes après une exécution d'ordre.
        
        Args:
            symbol: Symbole de l'actif.
            amount: Montant de l'ordre.
            price: Prix d'exécution.
            side: Côté de l'ordre ('buy' ou 'sell').
        """
        # Mettre à jour la position
        current_position = self.positions.get(symbol, 0)
        
        if side == "buy":
            self.positions[symbol] = current_position + amount
        else:
            self.positions[symbol] = current_position - amount
        
        # Mettre à jour le capital
        trade_value = amount * price
        fee_rate = 0.001  # Taux de frais estimé
        fees = trade_value * fee_rate
        
        if side == "buy":
            self.current_capital -= trade_value + fees
        else:
            self.current_capital += trade_value - fees
        
        # Mettre à jour le capital maximum
        if self.current_capital > self.peak_capital:
            self.peak_capital = self.current_capital
        
        logger.debug(f"Position mise à jour pour {symbol}: {self.positions[symbol]:.8f}, Capital: {self.current_capital:.2f}")
    
    def calculate_risk_metrics(self):
        """
        Calcule les métriques de risque basées sur l'historique des performances.
        
        Met à jour les métriques de risque internes comme le ratio de Sharpe,
        le ratio de Sortino, le drawdown maximum, etc.
        """
        if not self.daily_pnl or len(self.daily_pnl) < 5:
            return
        
        # Convertir en array numpy pour les calculs
        daily_returns = np.array(self.daily_pnl)
        
        # Calculer la volatilité (écart-type des rendements)
        volatility = np.std(daily_returns)
        self.risk_metrics["volatility"] = volatility
        
        # Calculer le ratio de Sharpe (en supposant un taux sans risque de 0%)
        avg_return = np.mean(daily_returns)
        if volatility > 0:
            sharpe_ratio = avg_return / volatility * np.sqrt(252)  # Annualisé
            self.risk_metrics["sharpe_ratio"] = sharpe_ratio
        
        # Calculer le ratio de Sortino (en utilisant uniquement les rendements négatifs)
        negative_returns = daily_returns[daily_returns < 0]
        if len(negative_returns) > 0:
            downside_deviation = np.std(negative_returns)
            if downside_deviation > 0:
                sortino_ratio = avg_return / downside_deviation * np.sqrt(252)  # Annualisé
                self.risk_metrics["sortino_ratio"] = sortino_ratio
        
        # Calculer le taux de réussite
        win_count = np.sum(daily_returns > 0)
        total_count = len(daily_returns)
        win_rate = win_count / total_count if total_count > 0 else 0
        self.risk_metrics["win_rate"] = win_rate
        
        logger.info(f"Métriques de risque mises à jour: Sharpe={self.risk_metrics['sharpe_ratio']:.2f}, "
                   f"Sortino={self.risk_metrics['sortino_ratio']:.2f}, "
                   f"Max Drawdown={self.risk_metrics['max_drawdown']:.2f}%, "
                   f"Win Rate={self.risk_metrics['win_rate']*100:.2f}%")
    
    def should_hedge_position(self, symbol: str) -> Tuple[bool, str, float]:
        """
        Détermine si une position doit être couverte pour réduire le risque.
        
        Args:
            symbol: Symbole de l'actif.
            
        Returns:
            Tuple (hedge_needed, hedge_instrument, hedge_amount)
        """
        current_position = self.positions.get(symbol, 0)
        
        # Si pas de position, pas besoin de couverture
        if abs(current_position) < 0.001:
            return False, "", 0
        
        # Si le marché montre des signes de manipulation, envisager une couverture
        if self.detect_market_manipulation(symbol):
            # Déterminer l'instrument de couverture (peut être un actif corrélé)
            hedge_instrument = self._find_hedge_instrument(symbol)
            
            # Déterminer le montant à couvrir (généralement une partie de la position)
            hedge_ratio = 0.5  # Couvrir 50% de la position
            hedge_amount = abs(current_position) * hedge_ratio
            
            logger.info(f"Couverture recommandée pour {symbol}: {hedge_amount:.8f} sur {hedge_instrument}")
            return True, hedge_instrument, hedge_amount
        
        return False, "", 0
    
    def _find_hedge_instrument(self, symbol: str) -> str:
        """
        Trouve un instrument approprié pour couvrir une position.
        
        Args:
            symbol: Symbole de l'actif à couvrir.
            
        Returns:
            Symbole de l'instrument de couverture.
        """
        # Cette méthode devrait être adaptée en fonction du marché
        # Par exemple, pour BTC/USD, un hedge pourrait être un short sur un contrat à terme BTC
        
        # Logique simplifiée pour l'exemple
        if "BTC" in symbol:
            return "BTC-PERP"  # Contrat perpétuel BTC
        elif "ETH" in symbol:
            return "ETH-PERP"  # Contrat perpétuel ETH
        else:
            # Par défaut, utiliser un indice ou un ETF lié au marché
            return symbol + "-PERP"
    
    def get_risk_report(self) -> Dict[str, Any]:
        """
        Génère un rapport détaillé sur l'état actuel des risques.
        
        Returns:
            Dictionnaire contenant les métriques de risque et l'état des positions.
        """
        return {
            "capital": {
                "initial": self.initial_capital,
                "current": self.current_capital,
                "peak": self.peak_capital,
                "drawdown_percent": (1 - self.current_capital / self.peak_capital) * 100 if self.peak_capital > 0 else 0,
            },
            "positions": self.positions,
            "metrics": self.risk_metrics,
            "limits": {
                "max_position_size": self.max_position_size,
                "max_drawdown_percent": self.max_drawdown_percent,
                "max_open_orders": self.max_open_orders,
            }
        }
