#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Stratégie Combinée pour ULTRA-ROBOT MARKET MAKER IA.

Ce module implémente une stratégie qui combine plusieurs approches de trading
pour maximiser la rentabilité et minimiser les risques.
"""

import time
import threading
from typing import Dict, Any, List, Optional, Tuple
from loguru import logger

from src.strategies.base_strategy import BaseStrategy
from src.data.market_data_manager import MarketDataManager


class CombinedStrategy(BaseStrategy):
    """
    Stratégie qui combine plusieurs approches de trading.
    
    Cette classe permet d'exécuter simultanément plusieurs stratégies
    sur les mêmes paires de trading, en combinant leurs signaux et en
    gérant intelligemment les positions.
    """
    
    def __init__(self, config: Dict[str, Any], market_data_manager: MarketDataManager):
        """
        Initialise la stratégie combinée.
        
        Args:
            config: Configuration de la stratégie.
            market_data_manager: Gestionnaire de données de marché.
        """
        super().__init__(config, market_data_manager)
        
        # Paramètres spécifiques à la stratégie combinée
        self.sub_strategies = []
        self.weights = config.get("weights", {})
        self.correlation_threshold = config.get("correlation_threshold", 0.7)
        self.max_drawdown_threshold = config.get("max_drawdown_threshold", 5.0)
        self.rebalance_interval_hours = config.get("rebalance_interval_hours", 24)
        
        # État interne
        self.last_rebalance_time = time.time()
        self.strategy_performance = {}
        self.combined_signals = {}
        
        # Verrou pour les opérations thread-safe
        self.lock = threading.RLock()
        
        logger.info(f"Stratégie combinée {self.name} initialisée avec {len(self.weights)} sous-stratégies")
    
    def add_strategy(self, strategy: BaseStrategy, weight: float = 1.0):
        """
        Ajoute une sous-stratégie à la stratégie combinée.
        
        Args:
            strategy: Stratégie à ajouter.
            weight: Poids de la stratégie dans la combinaison.
        """
        with self.lock:
            self.sub_strategies.append(strategy)
            self.weights[strategy.get_name()] = weight
            
            # Initialiser les performances
            self.strategy_performance[strategy.get_name()] = {
                "signals": [],
                "accuracy": 0.0,
                "profit": 0.0,
                "drawdown": 0.0
            }
            
            logger.info(f"Stratégie {strategy.get_name()} ajoutée à la stratégie combinée {self.name} avec un poids de {weight}")
    
    def remove_strategy(self, strategy_name: str):
        """
        Supprime une sous-stratégie de la stratégie combinée.
        
        Args:
            strategy_name: Nom de la stratégie à supprimer.
        """
        with self.lock:
            # Rechercher la stratégie par son nom
            for i, strategy in enumerate(self.sub_strategies):
                if strategy.get_name() == strategy_name:
                    # Supprimer la stratégie
                    self.sub_strategies.pop(i)
                    
                    # Supprimer le poids
                    if strategy_name in self.weights:
                        del self.weights[strategy_name]
                    
                    # Supprimer les performances
                    if strategy_name in self.strategy_performance:
                        del self.strategy_performance[strategy_name]
                    
                    logger.info(f"Stratégie {strategy_name} supprimée de la stratégie combinée {self.name}")
                    return
            
            logger.warning(f"Stratégie {strategy_name} non trouvée dans la stratégie combinée {self.name}")
    
    def update(self):
        """
        Met à jour la stratégie combinée.
        
        Cette méthode est appelée périodiquement pour mettre à jour
        l'état de la stratégie et générer des signaux.
        """
        if not self.is_running or not self.enabled:
            return
        
        logger.debug(f"Mise à jour de la stratégie combinée {self.name}")
        
        try:
            # Mettre à jour les sous-stratégies
            for strategy in self.sub_strategies:
                if strategy.is_enabled():
                    strategy.update()
            
            # Combiner les signaux
            self._combine_signals()
            
            # Vérifier s'il faut rééquilibrer les poids
            current_time = time.time()
            if current_time - self.last_rebalance_time > self.rebalance_interval_hours * 3600:
                self._rebalance_weights()
                self.last_rebalance_time = current_time
        
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour de la stratégie combinée {self.name}: {str(e)}")
    
    def start(self):
        """
        Démarre la stratégie combinée et toutes ses sous-stratégies.
        """
        if self.is_running:
            logger.warning(f"La stratégie combinée {self.name} est déjà en cours d'exécution")
            return
        
        logger.info(f"Démarrage de la stratégie combinée {self.name}")
        
        # Démarrer les sous-stratégies
        for strategy in self.sub_strategies:
            if strategy.is_enabled() and not strategy.is_running:
                strategy.start()
        
        # Démarrer la stratégie combinée
        self.is_running = True
    
    def stop(self):
        """
        Arrête la stratégie combinée et toutes ses sous-stratégies.
        """
        if not self.is_running:
            logger.warning(f"La stratégie combinée {self.name} n'est pas en cours d'exécution")
            return
        
        logger.info(f"Arrêt de la stratégie combinée {self.name}")
        
        # Arrêter les sous-stratégies
        for strategy in self.sub_strategies:
            if strategy.is_running:
                strategy.stop()
        
        # Arrêter la stratégie combinée
        self.is_running = False
    
    def get_signals(self, symbol: str, exchange_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Récupère les signaux combinés pour un symbole.
        
        Args:
            symbol: Symbole de l'actif.
            exchange_id: Identifiant de l'exchange.
            
        Returns:
            Signaux combinés.
        """
        with self.lock:
            key = f"{symbol}_{exchange_id}" if exchange_id else symbol
            
            if key in self.combined_signals:
                return self.combined_signals[key]
            
            return {
                "signal": 0,  # 0 = neutre, 1 = achat, -1 = vente
                "strength": 0.0,  # Force du signal (0.0 à 1.0)
                "confidence": 0.0,  # Confiance dans le signal (0.0 à 1.0)
                "timestamp": time.time()
            }
    
    def _combine_signals(self):
        """
        Combine les signaux des sous-stratégies.
        """
        with self.lock:
            # Réinitialiser les signaux combinés
            self.combined_signals = {}
            
            # Récupérer les signaux de chaque sous-stratégie
            for symbol in self.symbols:
                for exchange_id in self.exchanges:
                    if not self.should_process_symbol(symbol, exchange_id):
                        continue
                    
                    key = f"{symbol}_{exchange_id}"
                    weighted_signal = 0.0
                    total_weight = 0.0
                    confidence = 0.0
                    
                    # Combiner les signaux pondérés
                    for strategy in self.sub_strategies:
                        if not strategy.is_enabled() or not strategy.should_process_symbol(symbol, exchange_id):
                            continue
                        
                        # Récupérer le signal de la sous-stratégie
                        strategy_name = strategy.get_name()
                        weight = self.weights.get(strategy_name, 1.0)
                        
                        # Vérifier si la stratégie a une méthode get_signals
                        if hasattr(strategy, 'get_signals') and callable(getattr(strategy, 'get_signals')):
                            signal_data = strategy.get_signals(symbol, exchange_id)
                            
                            # Ajouter le signal à l'historique des performances
                            if strategy_name in self.strategy_performance:
                                self.strategy_performance[strategy_name]["signals"].append(signal_data)
                                
                                # Limiter la taille de l'historique
                                if len(self.strategy_performance[strategy_name]["signals"]) > 100:
                                    self.strategy_performance[strategy_name]["signals"].pop(0)
                            
                            # Pondérer le signal
                            signal = signal_data.get("signal", 0)
                            strength = signal_data.get("strength", 0.0)
                            strategy_confidence = signal_data.get("confidence", 0.0)
                            
                            weighted_signal += signal * strength * weight
                            confidence += strategy_confidence * weight
                            total_weight += weight
                    
                    # Normaliser les signaux
                    if total_weight > 0:
                        weighted_signal /= total_weight
                        confidence /= total_weight
                        
                        # Déterminer le signal final
                        final_signal = 0
                        if weighted_signal > 0.3:
                            final_signal = 1
                        elif weighted_signal < -0.3:
                            final_signal = -1
                        
                        # Enregistrer le signal combiné
                        self.combined_signals[key] = {
                            "signal": final_signal,
                            "strength": abs(weighted_signal),
                            "confidence": confidence,
                            "timestamp": time.time()
                        }
    
    def _rebalance_weights(self):
        """
        Rééquilibre les poids des sous-stratégies en fonction de leurs performances.
        """
        with self.lock:
            logger.info(f"Rééquilibrage des poids de la stratégie combinée {self.name}")
            
            # Calculer les performances des sous-stratégies
            for strategy in self.sub_strategies:
                strategy_name = strategy.get_name()
                
                if strategy_name in self.strategy_performance:
                    # Récupérer les performances
                    performance = strategy.get_performance()
                    
                    # Mettre à jour les métriques de performance
                    self.strategy_performance[strategy_name]["profit"] = performance.get("profit_total", 0.0)
                    self.strategy_performance[strategy_name]["drawdown"] = performance.get("max_drawdown", 0.0)
                    
                    # Calculer la précision des signaux (simplifié)
                    signals = self.strategy_performance[strategy_name]["signals"]
                    if signals:
                        correct_signals = 0
                        for i in range(len(signals) - 1):
                            signal = signals[i]["signal"]
                            next_signal = signals[i + 1]["signal"]
                            
                            # Un signal est considéré comme correct si le signal suivant est dans la même direction
                            if (signal > 0 and next_signal > 0) or (signal < 0 and next_signal < 0):
                                correct_signals += 1
                        
                        accuracy = correct_signals / (len(signals) - 1) if len(signals) > 1 else 0.0
                        self.strategy_performance[strategy_name]["accuracy"] = accuracy
            
            # Calculer les nouveaux poids
            new_weights = {}
            total_score = 0.0
            
            for strategy_name, performance in self.strategy_performance.items():
                # Calculer un score basé sur les performances
                profit = max(0.0, performance["profit"])
                accuracy = performance["accuracy"]
                drawdown = performance["drawdown"]
                
                # Éviter la division par zéro
                if drawdown < 0.01:
                    drawdown = 0.01
                
                # Score = (profit * accuracy) / drawdown
                score = (profit * accuracy) / drawdown
                
                # Stocker le score
                new_weights[strategy_name] = score
                total_score += score
            
            # Normaliser les poids
            if total_score > 0:
                for strategy_name, score in new_weights.items():
                    new_weights[strategy_name] = score / total_score
            else:
                # Si le score total est nul, utiliser des poids égaux
                equal_weight = 1.0 / len(new_weights) if new_weights else 0.0
                for strategy_name in new_weights:
                    new_weights[strategy_name] = equal_weight
            
            # Mettre à jour les poids
            self.weights = new_weights
            
            logger.info(f"Nouveaux poids pour la stratégie combinée {self.name}: {self.weights}")
    
    def get_sub_strategies(self) -> List[BaseStrategy]:
        """
        Récupère la liste des sous-stratégies.
        
        Returns:
            Liste des sous-stratégies.
        """
        return self.sub_strategies
    
    def get_weights(self) -> Dict[str, float]:
        """
        Récupère les poids des sous-stratégies.
        
        Returns:
            Dictionnaire des poids.
        """
        return self.weights
    
    def get_strategy_performance(self) -> Dict[str, Dict[str, Any]]:
        """
        Récupère les performances des sous-stratégies.
        
        Returns:
            Dictionnaire des performances.
        """
        return self.strategy_performance
