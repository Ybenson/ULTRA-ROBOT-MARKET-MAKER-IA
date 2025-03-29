#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module d'exécution des ordres pour ULTRA-ROBOT MARKET MAKER IA.

Ce module gère l'exécution des ordres sur différents exchanges, avec une
optimisation pour minimiser la latence et gérer les erreurs.
"""

import time
import threading
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from loguru import logger


class OrderExecutor:
    """
    Exécuteur d'ordres optimisé pour le market making haute fréquence.
    
    Cette classe gère l'exécution des ordres sur différents exchanges,
    avec une optimisation pour minimiser la latence et gérer les erreurs.
    """
    
    def __init__(self, exchanges: Dict[str, Any], config: Dict[str, Any], risk_manager=None):
        """
        Initialise l'exécuteur d'ordres.
        
        Args:
            exchanges: Dictionnaire des connexions aux exchanges.
            config: Configuration de l'exécution des ordres.
            risk_manager: Gestionnaire de risques.
        """
        self.exchanges = exchanges
        self.config = config
        self.risk_manager = risk_manager
        
        # Paramètres d'exécution
        self.order_type = config.get("order_type", "limit")
        self.max_slippage_percent = config.get("max_slippage_percent", 0.1)
        self.retry_attempts = config.get("retry_attempts", 3)
        self.retry_delay_seconds = config.get("retry_delay_seconds", 1)
        self.use_iceberg_orders = config.get("use_iceberg_orders", False)
        self.max_order_age_seconds = config.get("max_order_age_seconds", 300)
        
        # État interne
        self.active_orders = {}  # Ordres actifs par symbole et exchange
        self.order_history = []  # Historique des ordres exécutés
        self.execution_stats = {
            "orders_placed": 0,
            "orders_filled": 0,
            "orders_cancelled": 0,
            "orders_rejected": 0,
            "total_volume": 0.0,
            "average_latency_ms": 0.0,
        }
        
        # Verrous pour les opérations thread-safe
        self.order_lock = threading.RLock()
        
        # File d'attente pour les exécutions asynchrones
        self.order_queue = asyncio.Queue()
        
        # Démarrer le thread d'exécution asynchrone
        self.running = True
        self.execution_thread = threading.Thread(target=self._execution_loop)
        self.execution_thread.daemon = True
        self.execution_thread.start()
        
        logger.info("Exécuteur d'ordres initialisé")
    
    def place_order(self, symbol: str, side: str, order_type: str, amount: float, price: Optional[float] = None,
                   exchange_id: Optional[str] = None, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Place un ordre sur l'exchange.
        
        Args:
            symbol: Symbole de l'actif.
            side: Côté de l'ordre ('buy' ou 'sell').
            order_type: Type d'ordre ('limit', 'market', etc.).
            amount: Montant de l'ordre.
            price: Prix de l'ordre (requis pour les ordres limit).
            exchange_id: Identifiant de l'exchange (si None, utilise l'exchange par défaut).
            params: Paramètres supplémentaires pour l'ordre.
            
        Returns:
            Informations sur l'ordre placé, ou None si l'ordre a échoué.
        """
        # Vérifier les paramètres
        if not symbol or not side or not order_type or amount <= 0:
            logger.error(f"Paramètres d'ordre invalides: {symbol}, {side}, {order_type}, {amount}")
            return None
        
        if order_type == "limit" and (price is None or price <= 0):
            logger.error(f"Prix invalide pour un ordre limit: {price}")
            return None
        
        # Déterminer l'exchange à utiliser
        exchange = self._get_exchange_for_symbol(symbol, exchange_id)
        if not exchange:
            logger.error(f"Aucun exchange trouvé pour {symbol}")
            return None
        
        # Vérifier les limites de risque
        if self.risk_manager and not self.risk_manager.check_position_limit(symbol, side, amount):
            logger.warning(f"Limite de position dépassée pour {symbol}, {side}, {amount}")
            return None
        
        # Préparer les paramètres de l'ordre
        order_params = params or {}
        
        # Ajouter les paramètres pour les ordres iceberg si activés
        if self.use_iceberg_orders and order_type == "limit" and amount > 0.1:
            order_params["iceberg"] = True
            order_params["visible_size"] = amount * 0.2  # 20% visible
        
        # Ajouter un identifiant unique pour suivre l'ordre
        order_id = f"ultra_mm_{int(time.time() * 1000)}_{hash(symbol + side)}"
        order_params["clientOrderId"] = order_id
        
        # Mesurer la latence
        start_time = time.time()
        
        try:
            # Placer l'ordre
            with self.order_lock:
                if exchange_id not in self.active_orders:
                    self.active_orders[exchange_id] = {}
                
                # Placer l'ordre sur l'exchange
                if order_type == "limit":
                    order = exchange.create_limit_order(symbol, side, amount, price, order_params)
                elif order_type == "market":
                    order = exchange.create_market_order(symbol, side, amount, order_params)
                else:
                    logger.error(f"Type d'ordre non supporté: {order_type}")
                    return None
                
                # Calculer la latence
                latency_ms = (time.time() - start_time) * 1000
                
                # Mettre à jour les statistiques
                self.execution_stats["orders_placed"] += 1
                self.execution_stats["average_latency_ms"] = (
                    (self.execution_stats["average_latency_ms"] * (self.execution_stats["orders_placed"] - 1) + latency_ms) /
                    self.execution_stats["orders_placed"]
                )
                
                # Stocker l'ordre dans les ordres actifs
                if symbol not in self.active_orders[exchange_id]:
                    self.active_orders[exchange_id][symbol] = []
                
                order_info = {
                    "id": order["id"],
                    "client_id": order_id,
                    "symbol": symbol,
                    "side": side,
                    "type": order_type,
                    "amount": amount,
                    "price": price,
                    "status": order["status"],
                    "filled": order.get("filled", 0),
                    "remaining": order.get("remaining", amount),
                    "timestamp": time.time(),
                    "exchange_id": exchange_id,
                    "raw_order": order
                }
                
                self.active_orders[exchange_id][symbol].append(order_info)
                
                # Ajouter à l'historique des ordres
                self.order_history.append(order_info)
                
                logger.debug(f"Ordre placé: {symbol}, {side}, {order_type}, {amount}, {price}, latence: {latency_ms:.2f}ms")
                
                # Si l'ordre est déjà rempli, mettre à jour les statistiques
                if order["status"] == "closed" or order["status"] == "filled":
                    self.execution_stats["orders_filled"] += 1
                    self.execution_stats["total_volume"] += amount
                    
                    # Mettre à jour la position dans le gestionnaire de risques
                    if self.risk_manager:
                        self.risk_manager.update_position(symbol, amount, price, side)
                
                return order_info
                
        except Exception as e:
            logger.error(f"Erreur lors du placement de l'ordre: {str(e)}")
            
            # Réessayer si configuré
            if self.retry_attempts > 0:
                logger.info(f"Tentative de réessai ({self.retry_attempts} restantes)")
                time.sleep(self.retry_delay_seconds)
                return self.place_order(
                    symbol=symbol,
                    side=side,
                    order_type=order_type,
                    amount=amount,
                    price=price,
                    exchange_id=exchange_id,
                    params=params
                )
            
            return None
    
    def cancel_order(self, symbol: str, order_id: str, exchange_id: Optional[str] = None) -> bool:
        """
        Annule un ordre existant.
        
        Args:
            symbol: Symbole de l'actif.
            order_id: Identifiant de l'ordre à annuler.
            exchange_id: Identifiant de l'exchange (si None, utilise l'exchange par défaut).
            
        Returns:
            True si l'ordre a été annulé avec succès, False sinon.
        """
        # Déterminer l'exchange à utiliser
        exchange = self._get_exchange_for_symbol(symbol, exchange_id)
        if not exchange:
            logger.error(f"Aucun exchange trouvé pour {symbol}")
            return False
        
        try:
            # Annuler l'ordre
            with self.order_lock:
                result = exchange.cancel_order(order_id, symbol)
                
                # Mettre à jour les statistiques
                self.execution_stats["orders_cancelled"] += 1
                
                # Mettre à jour l'état de l'ordre dans les ordres actifs
                if exchange_id in self.active_orders and symbol in self.active_orders[exchange_id]:
                    for i, order in enumerate(self.active_orders[exchange_id][symbol]):
                        if order["id"] == order_id:
                            self.active_orders[exchange_id][symbol][i]["status"] = "canceled"
                            break
                
                logger.debug(f"Ordre annulé: {symbol}, {order_id}")
                
                return True
                
        except Exception as e:
            logger.error(f"Erreur lors de l'annulation de l'ordre: {str(e)}")
            
            # Réessayer si configuré
            if self.retry_attempts > 0:
                logger.info(f"Tentative de réessai ({self.retry_attempts} restantes)")
                time.sleep(self.retry_delay_seconds)
                return self.cancel_order(symbol, order_id, exchange_id)
            
            return False
    
    def cancel_all_orders(self, symbol: Optional[str] = None, exchange_id: Optional[str] = None) -> bool:
        """
        Annule tous les ordres actifs.
        
        Args:
            symbol: Symbole de l'actif (si None, annule pour tous les symboles).
            exchange_id: Identifiant de l'exchange (si None, annule pour tous les exchanges).
            
        Returns:
            True si tous les ordres ont été annulés avec succès, False sinon.
        """
        success = True
        
        with self.order_lock:
            # Déterminer les exchanges à utiliser
            exchanges_to_use = [exchange_id] if exchange_id else list(self.exchanges.keys())
            
            for ex_id in exchanges_to_use:
                if ex_id not in self.exchanges:
                    logger.warning(f"Exchange {ex_id} non trouvé")
                    continue
                
                exchange = self.exchanges[ex_id]
                
                try:
                    # Si un symbole est spécifié, annuler uniquement pour ce symbole
                    if symbol:
                        result = exchange.cancel_all_orders(symbol)
                        
                        # Mettre à jour les ordres actifs
                        if ex_id in self.active_orders and symbol in self.active_orders[ex_id]:
                            cancelled_count = len(self.active_orders[ex_id][symbol])
                            self.execution_stats["orders_cancelled"] += cancelled_count
                            self.active_orders[ex_id][symbol] = []
                        
                        logger.info(f"Tous les ordres annulés pour {symbol} sur {ex_id}")
                        
                    # Sinon, annuler pour tous les symboles
                    else:
                        # Pour certains exchanges, nous devons annuler par symbole
                        if ex_id in self.active_orders:
                            for sym in list(self.active_orders[ex_id].keys()):
                                try:
                                    exchange.cancel_all_orders(sym)
                                    
                                    # Mettre à jour les ordres actifs
                                    cancelled_count = len(self.active_orders[ex_id][sym])
                                    self.execution_stats["orders_cancelled"] += cancelled_count
                                    self.active_orders[ex_id][sym] = []
                                    
                                except Exception as e:
                                    logger.error(f"Erreur lors de l'annulation des ordres pour {sym} sur {ex_id}: {str(e)}")
                                    success = False
                        
                        logger.info(f"Tous les ordres annulés sur {ex_id}")
                    
                except Exception as e:
                    logger.error(f"Erreur lors de l'annulation de tous les ordres sur {ex_id}: {str(e)}")
                    success = False
        
        return success
    
    def get_order_status(self, symbol: str, order_id: str, exchange_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Obtient le statut d'un ordre.
        
        Args:
            symbol: Symbole de l'actif.
            order_id: Identifiant de l'ordre.
            exchange_id: Identifiant de l'exchange (si None, utilise l'exchange par défaut).
            
        Returns:
            Informations sur l'ordre, ou None si l'ordre n'est pas trouvé.
        """
        # Déterminer l'exchange à utiliser
        exchange = self._get_exchange_for_symbol(symbol, exchange_id)
        if not exchange:
            logger.error(f"Aucun exchange trouvé pour {symbol}")
            return None
        
        try:
            # Obtenir le statut de l'ordre
            order = exchange.fetch_order(order_id, symbol)
            
            # Mettre à jour l'état de l'ordre dans les ordres actifs
            with self.order_lock:
                if exchange_id in self.active_orders and symbol in self.active_orders[exchange_id]:
                    for i, active_order in enumerate(self.active_orders[exchange_id][symbol]):
                        if active_order["id"] == order_id:
                            self.active_orders[exchange_id][symbol][i]["status"] = order["status"]
                            self.active_orders[exchange_id][symbol][i]["filled"] = order.get("filled", 0)
                            self.active_orders[exchange_id][symbol][i]["remaining"] = order.get("remaining", 0)
                            break
            
            return order
            
        except Exception as e:
            logger.error(f"Erreur lors de l'obtention du statut de l'ordre: {str(e)}")
            return None
    
    def update_orders(self):
        """
        Met à jour le statut de tous les ordres actifs.
        
        Cette méthode est appelée régulièrement pour maintenir à jour
        l'état des ordres actifs et détecter les ordres remplis.
        """
        with self.order_lock:
            for exchange_id, exchange_orders in self.active_orders.items():
                if exchange_id not in self.exchanges:
                    continue
                
                exchange = self.exchanges[exchange_id]
                
                for symbol, orders in exchange_orders.items():
                    # Filtrer les ordres qui ne sont pas encore terminés
                    active_orders = [order for order in orders if order["status"] not in ["filled", "canceled", "closed"]]
                    
                    # Mettre à jour le statut de chaque ordre
                    for order in active_orders:
                        try:
                            updated_order = exchange.fetch_order(order["id"], symbol)
                            
                            # Mettre à jour l'état de l'ordre
                            order["status"] = updated_order["status"]
                            order["filled"] = updated_order.get("filled", 0)
                            order["remaining"] = updated_order.get("remaining", 0)
                            
                            # Si l'ordre est rempli, mettre à jour les statistiques
                            if updated_order["status"] in ["filled", "closed"]:
                                self.execution_stats["orders_filled"] += 1
                                self.execution_stats["total_volume"] += order["amount"]
                                
                                # Mettre à jour la position dans le gestionnaire de risques
                                if self.risk_manager:
                                    self.risk_manager.update_position(
                                        symbol=symbol,
                                        amount=order["amount"],
                                        price=order["price"],
                                        side=order["side"]
                                    )
                            
                        except Exception as e:
                            logger.error(f"Erreur lors de la mise à jour de l'ordre {order['id']} pour {symbol}: {str(e)}")
                    
                    # Nettoyer les ordres terminés ou trop anciens
                    current_time = time.time()
                    exchange_orders[symbol] = [
                        order for order in orders
                        if (order["status"] not in ["filled", "canceled", "closed"]) and
                           (current_time - order["timestamp"] < self.max_order_age_seconds)
                    ]
    
    def _get_exchange_for_symbol(self, symbol: str, exchange_id: Optional[str] = None) -> Any:
        """
        Obtient l'exchange approprié pour un symbole.
        
        Args:
            symbol: Symbole de l'actif.
            exchange_id: Identifiant de l'exchange (si None, détermine automatiquement).
            
        Returns:
            Objet exchange, ou None si non trouvé.
        """
        # Si un exchange_id est spécifié, l'utiliser
        if exchange_id and exchange_id in self.exchanges:
            return self.exchanges[exchange_id]
        
        # Sinon, déterminer l'exchange en fonction du symbole
        for ex_id, exchange in self.exchanges.items():
            try:
                # Vérifier si le symbole est supporté par cet exchange
                markets = exchange.load_markets()
                if symbol in markets:
                    return exchange
            except Exception:
                continue
        
        # Si aucun exchange n'est trouvé, utiliser le premier disponible
        if self.exchanges:
            first_exchange_id = next(iter(self.exchanges))
            logger.warning(f"Aucun exchange trouvé pour {symbol}, utilisation de {first_exchange_id}")
            return self.exchanges[first_exchange_id]
        
        return None
    
    def _execution_loop(self):
        """
        Boucle d'exécution asynchrone pour traiter les ordres en file d'attente.
        """
        # Créer une nouvelle boucle d'événements asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def process_queue():
            while self.running:
                try:
                    # Mettre à jour les ordres actifs
                    self.update_orders()
                    
                    # Attendre un court instant
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Erreur dans la boucle d'exécution: {str(e)}")
                    await asyncio.sleep(1)
        
        # Exécuter la boucle de traitement
        try:
            loop.run_until_complete(process_queue())
        except Exception as e:
            logger.error(f"Erreur fatale dans la boucle d'exécution: {str(e)}")
        finally:
            loop.close()
    
    def stop(self):
        """
        Arrête l'exécuteur d'ordres.
        """
        self.running = False
        
        # Annuler tous les ordres actifs
        self.cancel_all_orders()
        
        # Attendre que le thread d'exécution se termine
        if self.execution_thread and self.execution_thread.is_alive():
            self.execution_thread.join(timeout=10)
        
        logger.info("Exécuteur d'ordres arrêté")
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """
        Obtient les statistiques d'exécution.
        
        Returns:
            Dictionnaire des statistiques d'exécution.
        """
        return self.execution_stats.copy()
    
    def get_active_orders(self, symbol: Optional[str] = None, exchange_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Obtient les ordres actifs.
        
        Args:
            symbol: Symbole de l'actif (si None, retourne pour tous les symboles).
            exchange_id: Identifiant de l'exchange (si None, retourne pour tous les exchanges).
            
        Returns:
            Liste des ordres actifs.
        """
        active_orders = []
        
        with self.order_lock:
            # Filtrer par exchange_id si spécifié
            exchanges_to_check = [exchange_id] if exchange_id else self.active_orders.keys()
            
            for ex_id in exchanges_to_check:
                if ex_id not in self.active_orders:
                    continue
                
                # Filtrer par symbole si spécifié
                symbols_to_check = [symbol] if symbol else self.active_orders[ex_id].keys()
                
                for sym in symbols_to_check:
                    if sym not in self.active_orders[ex_id]:
                        continue
                    
                    active_orders.extend(self.active_orders[ex_id][sym])
        
        return active_orders
