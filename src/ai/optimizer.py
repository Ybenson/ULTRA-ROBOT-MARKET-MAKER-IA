#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module d'optimisation par IA pour ULTRA-ROBOT MARKET MAKER IA.

Ce module implémente des algorithmes d'intelligence artificielle pour optimiser
les paramètres des stratégies de market making en fonction des conditions de marché.
"""

import numpy as np
import time
import threading
from typing import Dict, Any, List, Optional
from loguru import logger

try:
    import tensorflow as tf
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False
    logger.warning("TensorFlow non disponible. Certaines fonctionnalités d'IA seront limitées.")


class AIOptimizer:
    """
    Optimiseur IA pour les stratégies de market making.
    
    Cette classe utilise des techniques d'apprentissage par renforcement et d'autres
    algorithmes d'IA pour optimiser dynamiquement les paramètres des stratégies
    en fonction des conditions de marché.
    """
    
    def __init__(self, config: Dict[str, Any], market_data_manager=None, strategies=None):
        """
        Initialise l'optimiseur IA.
        
        Args:
            config: Configuration de l'optimiseur IA.
            market_data_manager: Gestionnaire de données de marché.
            strategies: Dictionnaire des stratégies à optimiser.
        """
        self.config = config
        self.market_data_manager = market_data_manager
        self.strategies = strategies or {}
        
        # Paramètres de l'optimiseur
        self.model_type = config.get("model_type", "reinforcement_learning")
        self.update_frequency = config.get("update_frequency_seconds", 300)
        self.learning_rate = config.get("learning_rate", 0.001)
        self.exploration_rate = config.get("exploration_rate", 0.1)
        self.batch_size = config.get("batch_size", 32)
        self.memory_size = config.get("memory_size", 10000)
        
        # État interne
        self.models = {}
        self.optimizers = {}
        self.experience_buffer = []
        self.last_update_time = time.time()
        self.is_training = False
        self.training_thread = None
        
        # Initialiser les modèles
        self._initialize_models()
        
        logger.info(f"Optimiseur IA initialisé avec modèle {self.model_type}")
    
    def _initialize_models(self):
        """
        Initialise les modèles d'IA en fonction du type spécifié.
        """
        if self.model_type == "reinforcement_learning":
            self._initialize_rl_models()
        elif self.model_type == "adaptive_parameters":
            self._initialize_adaptive_models()
        else:
            logger.warning(f"Type de modèle inconnu: {self.model_type}. Utilisation du modèle par défaut.")
            self._initialize_adaptive_models()
    
    def _initialize_rl_models(self):
        """
        Initialise les modèles d'apprentissage par renforcement.
        """
        if not TF_AVAILABLE:
            logger.warning("TensorFlow non disponible. Utilisation de modèles simplifiés.")
            self._initialize_adaptive_models()
            return
        
        try:
            # Créer un modèle pour chaque stratégie
            for strategy_id, strategy in self.strategies.items():
                # Définir l'architecture du modèle
                model = tf.keras.Sequential([
                    tf.keras.layers.Dense(64, activation='relu', input_shape=(20,)),
                    tf.keras.layers.Dense(32, activation='relu'),
                    tf.keras.layers.Dense(16, activation='relu'),
                    tf.keras.layers.Dense(5)  # Sortie: [spread_bid, spread_ask, order_size, order_count, refresh_rate]
                ])
                
                # Compiler le modèle
                optimizer = tf.keras.optimizers.Adam(learning_rate=self.learning_rate)
                model.compile(optimizer=optimizer, loss='mse')
                
                self.models[strategy_id] = model
                self.optimizers[strategy_id] = optimizer
                
                logger.info(f"Modèle RL initialisé pour la stratégie {strategy_id}")
                
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation des modèles RL: {str(e)}")
            self._initialize_adaptive_models()
    
    def _initialize_adaptive_models(self):
        """
        Initialise des modèles adaptatifs simples (fallback).
        """
        # Modèles adaptatifs simples basés sur des règles
        for strategy_id, strategy in self.strategies.items():
            self.models[strategy_id] = {
                "base_params": self._get_strategy_params(strategy),
                "volatility_factor": 1.0,
                "volume_factor": 1.0,
                "trend_factor": 0.0,
            }
            
            logger.info(f"Modèle adaptatif initialisé pour la stratégie {strategy_id}")
    
    def _get_strategy_params(self, strategy) -> Dict[str, Any]:
        """
        Obtient les paramètres actuels d'une stratégie.
        
        Args:
            strategy: Objet stratégie.
            
        Returns:
            Dictionnaire des paramètres de la stratégie.
        """
        params = {}
        
        # Extraire les paramètres communs
        if hasattr(strategy, "get_parameters"):
            params = strategy.get_parameters()
        else:
            # Extraction manuelle des paramètres courants
            if hasattr(strategy, "spread_bid"):
                params["spread_bid"] = strategy.spread_bid
            if hasattr(strategy, "spread_ask"):
                params["spread_ask"] = strategy.spread_ask
            if hasattr(strategy, "order_size"):
                params["order_size"] = strategy.order_size
            if hasattr(strategy, "order_count"):
                params["order_count"] = strategy.order_count
            if hasattr(strategy, "refresh_rate"):
                params["refresh_rate"] = strategy.refresh_rate
        
        return params
    
    def optimize(self):
        """
        Exécute l'optimisation des stratégies en fonction des conditions de marché actuelles.
        """
        current_time = time.time()
        
        # Vérifier si une mise à jour est nécessaire
        if current_time - self.last_update_time < self.update_frequency:
            return
        
        self.last_update_time = current_time
        logger.debug("Démarrage de l'optimisation IA...")
        
        # Optimiser chaque stratégie
        for strategy_id, strategy in self.strategies.items():
            try:
                if strategy_id not in self.models:
                    logger.warning(f"Pas de modèle pour la stratégie {strategy_id}")
                    continue
                
                # Obtenir les données de marché actuelles
                market_features = self._extract_market_features(strategy)
                
                # Optimiser les paramètres
                if self.model_type == "reinforcement_learning" and TF_AVAILABLE:
                    optimized_params = self._optimize_with_rl(strategy_id, market_features)
                else:
                    optimized_params = self._optimize_with_rules(strategy_id, market_features)
                
                # Appliquer les paramètres optimisés
                self._apply_optimized_params(strategy, optimized_params)
                
                logger.info(f"Paramètres optimisés pour la stratégie {strategy_id}")
                
            except Exception as e:
                logger.error(f"Erreur lors de l'optimisation de la stratégie {strategy_id}: {str(e)}")
    
    def _extract_market_features(self, strategy) -> np.ndarray:
        """
        Extrait les caractéristiques du marché pour l'optimisation.
        
        Args:
            strategy: Objet stratégie.
            
        Returns:
            Array numpy des caractéristiques du marché.
        """
        features = []
        
        # Si le gestionnaire de données de marché n'est pas disponible, retourner des valeurs par défaut
        if not self.market_data_manager:
            return np.zeros(20)
        
        try:
            # Obtenir les symboles de la stratégie
            symbols = []
            if hasattr(strategy, "symbols"):
                symbols = strategy.symbols
            elif hasattr(strategy, "symbol"):
                symbols = [strategy.symbol]
            
            # Pour chaque symbole, extraire les caractéristiques
            for symbol in symbols:
                # Volatilité
                volatility = self.market_data_manager.get_volatility(symbol, window=24)
                features.append(volatility)
                
                # Volume
                volume = self.market_data_manager.get_average_volume(symbol, window=24)
                features.append(volume)
                
                # Spread
                spread = self.market_data_manager.get_average_spread(symbol, window=24)
                features.append(spread)
                
                # Tendance
                trend = self.market_data_manager.get_trend_indicator(symbol, window=24)
                features.append(trend)
                
                # Profondeur du carnet d'ordres
                book_depth = self.market_data_manager.get_order_book_depth(symbol)
                features.append(book_depth)
            
            # Normaliser et compléter le vecteur de caractéristiques
            features = np.array(features, dtype=np.float32)
            
            # Assurer une taille fixe (padding ou troncature)
            if len(features) < 20:
                features = np.pad(features, (0, 20 - len(features)), 'constant')
            elif len(features) > 20:
                features = features[:20]
            
            return features
            
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction des caractéristiques: {str(e)}")
            return np.zeros(20)
    
    def _optimize_with_rl(self, strategy_id: str, market_features: np.ndarray) -> Dict[str, Any]:
        """
        Optimise les paramètres avec l'apprentissage par renforcement.
        
        Args:
            strategy_id: Identifiant de la stratégie.
            market_features: Caractéristiques du marché.
            
        Returns:
            Paramètres optimisés.
        """
        model = self.models[strategy_id]
        
        # Exploration vs exploitation
        if np.random.random() < self.exploration_rate:
            # Exploration: paramètres aléatoires
            predictions = np.random.normal(0, 1, 5)
        else:
            # Exploitation: utiliser le modèle
            predictions = model.predict(market_features.reshape(1, -1), verbose=0)[0]
        
        # Convertir les prédictions en paramètres
        optimized_params = {
            "spread_bid": max(0.01, 0.1 + predictions[0] * 0.05),  # 0.05% - 0.15%
            "spread_ask": max(0.01, 0.1 + predictions[1] * 0.05),  # 0.05% - 0.15%
            "order_size": max(0.001, 0.01 + predictions[2] * 0.01),  # 0.001 - 0.02
            "order_count": max(1, int(3 + predictions[3] * 2)),  # 1 - 5
            "refresh_rate": max(1, int(10 + predictions[4] * 5)),  # 5 - 15 secondes
        }
        
        # Stocker l'expérience pour l'entraînement
        self._store_experience(strategy_id, market_features, predictions)
        
        # Lancer l'entraînement en arrière-plan si nécessaire
        self._schedule_training()
        
        return optimized_params
    
    def _optimize_with_rules(self, strategy_id: str, market_features: np.ndarray) -> Dict[str, Any]:
        """
        Optimise les paramètres avec des règles adaptatives simples.
        
        Args:
            strategy_id: Identifiant de la stratégie.
            market_features: Caractéristiques du marché.
            
        Returns:
            Paramètres optimisés.
        """
        model = self.models[strategy_id]
        base_params = model["base_params"]
        
        # Extraire les facteurs de marché (simplifiés)
        volatility_factor = market_features[0] if len(market_features) > 0 else 1.0
        volume_factor = market_features[1] if len(market_features) > 1 else 1.0
        trend_factor = market_features[3] if len(market_features) > 3 else 0.0
        
        # Normaliser les facteurs
        volatility_factor = min(max(volatility_factor, 0.5), 2.0)
        volume_factor = min(max(volume_factor, 0.5), 2.0)
        trend_factor = min(max(trend_factor, -1.0), 1.0)
        
        # Mettre à jour les facteurs du modèle
        model["volatility_factor"] = volatility_factor
        model["volume_factor"] = volume_factor
        model["trend_factor"] = trend_factor
        
        # Ajuster les paramètres en fonction des facteurs de marché
        optimized_params = {}
        
        # Ajuster le spread en fonction de la volatilité
        if "spread_bid" in base_params:
            optimized_params["spread_bid"] = base_params["spread_bid"] * volatility_factor
        if "spread_ask" in base_params:
            optimized_params["spread_ask"] = base_params["spread_ask"] * volatility_factor
        
        # Ajuster la taille des ordres en fonction du volume
        if "order_size" in base_params:
            optimized_params["order_size"] = base_params["order_size"] * volume_factor
        
        # Ajuster le nombre d'ordres
        if "order_count" in base_params:
            optimized_params["order_count"] = max(1, int(base_params["order_count"] * (1 + trend_factor * 0.2)))
        
        # Ajuster la fréquence de rafraîchissement en fonction de la volatilité
        if "refresh_rate" in base_params:
            optimized_params["refresh_rate"] = max(1, int(base_params["refresh_rate"] / volatility_factor))
        
        return optimized_params
    
    def _apply_optimized_params(self, strategy, optimized_params: Dict[str, Any]):
        """
        Applique les paramètres optimisés à la stratégie.
        
        Args:
            strategy: Objet stratégie.
            optimized_params: Paramètres optimisés.
        """
        # Vérifier si la stratégie a une méthode pour mettre à jour les paramètres
        if hasattr(strategy, "update_parameters"):
            strategy.update_parameters(optimized_params)
        else:
            # Mise à jour manuelle des attributs
            for param, value in optimized_params.items():
                if hasattr(strategy, param):
                    setattr(strategy, param, value)
    
    def _store_experience(self, strategy_id: str, state: np.ndarray, action: np.ndarray):
        """
        Stocke une expérience dans le buffer pour l'apprentissage.
        
        Args:
            strategy_id: Identifiant de la stratégie.
            state: État du marché.
            action: Action prise (paramètres prédits).
        """
        # Pour l'instant, stocker simplement l'état et l'action
        # La récompense sera calculée lors de l'entraînement
        self.experience_buffer.append({
            "strategy_id": strategy_id,
            "state": state.copy(),
            "action": action.copy(),
            "timestamp": time.time()
        })
        
        # Limiter la taille du buffer
        if len(self.experience_buffer) > self.memory_size:
            self.experience_buffer.pop(0)
    
    def _schedule_training(self):
        """
        Planifie l'entraînement du modèle en arrière-plan.
        """
        # Vérifier si un entraînement est déjà en cours
        if self.is_training:
            return
        
        # Vérifier si nous avons assez d'expériences pour l'entraînement
        if len(self.experience_buffer) < self.batch_size:
            return
        
        # Lancer l'entraînement dans un thread séparé
        self.is_training = True
        self.training_thread = threading.Thread(target=self._train_models)
        self.training_thread.daemon = True
        self.training_thread.start()
    
    def _train_models(self):
        """
        Entraîne les modèles d'IA avec les expériences collectées.
        """
        try:
            logger.info("Démarrage de l'entraînement des modèles IA...")
            
            # Regrouper les expériences par stratégie
            experiences_by_strategy = {}
            for exp in self.experience_buffer:
                strategy_id = exp["strategy_id"]
                if strategy_id not in experiences_by_strategy:
                    experiences_by_strategy[strategy_id] = []
                experiences_by_strategy[strategy_id].append(exp)
            
            # Entraîner chaque modèle
            for strategy_id, experiences in experiences_by_strategy.items():
                if strategy_id not in self.models or not TF_AVAILABLE:
                    continue
                
                # Préparer les données d'entraînement
                states = np.array([exp["state"] for exp in experiences])
                actions = np.array([exp["action"] for exp in experiences])
                
                # Calculer les récompenses (simplifiées pour l'exemple)
                # Dans un système réel, les récompenses seraient basées sur les performances
                rewards = np.ones_like(actions[:, 0])  # Récompense uniforme pour l'exemple
                
                # Ajuster les actions en fonction des récompenses
                target_actions = actions.copy()
                for i, reward in enumerate(rewards):
                    target_actions[i] += 0.01 * reward  # Ajustement simple
                
                # Entraîner le modèle
                model = self.models[strategy_id]
                model.fit(
                    states, target_actions,
                    batch_size=min(self.batch_size, len(states)),
                    epochs=1,
                    verbose=0
                )
                
                logger.debug(f"Modèle pour la stratégie {strategy_id} entraîné sur {len(states)} exemples")
            
            logger.info("Entraînement des modèles IA terminé")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'entraînement des modèles: {str(e)}")
        
        finally:
            self.is_training = False
