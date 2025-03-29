#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Connecteur pour l'exchange Binance dans ULTRA-ROBOT MARKET MAKER IA.

Ce module implémente les méthodes spécifiques pour interagir avec l'API de Binance.
"""

import time
import hmac
import hashlib
import requests
import json
from typing import Dict, Any, List, Optional, Tuple, Union
from urllib.parse import urlencode
from loguru import logger

from src.exchanges.base_exchange import BaseExchange


class BinanceExchange(BaseExchange):
    """
    Connecteur pour l'exchange Binance.
    
    Cette classe implémente les méthodes spécifiques pour interagir
    avec l'API de Binance.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialise le connecteur Binance.
        
        Args:
            config: Configuration du connecteur.
        """
        super().__init__(config)
        
        # URLs de l'API
        self.base_url = "https://api.binance.com"
        self.api_url = self.base_url + "/api"
        self.wapi_url = self.base_url + "/wapi"
        self.sapi_url = self.base_url + "/sapi"
        self.fapi_url = self.base_url + "/fapi"  # Futures API
        self.dapi_url = self.base_url + "/dapi"  # Delivery API
        
        # URL du WebSocket
        self.ws_url = "wss://stream.binance.com:9443/ws"
        
        # Mettre à jour les capacités
        self.has["ws"] = True
        
        # Informations sur les symboles
        self.symbol_info = {}
        
        # Limites de taux de requêtes
        self.rate_limits = {
            "order": 10,  # 10 ordres par seconde
            "request": 1200  # 1200 requêtes par minute
        }
        
        # Dernière requête timestamp
        self.last_request_time = {}
        
        # Session HTTP
        self.session = requests.Session()
        
        # Testnet
        self.testnet = config.get("testnet", False)
        if self.testnet:
            self.base_url = "https://testnet.binance.vision"
            self.api_url = self.base_url + "/api"
            self.ws_url = "wss://testnet.binance.vision/ws"
            logger.info("Utilisation de l'environnement Testnet Binance")
    
    def connect(self) -> bool:
        """
        Établit la connexion avec Binance.
        
        Returns:
            True si la connexion est établie avec succès, False sinon.
        """
        try:
            # Vérifier la connectivité
            response = self.session.get(f"{self.api_url}/v3/ping")
            if response.status_code == 200:
                # Récupérer les informations sur les symboles
                self._load_markets()
                self.connected = True
                logger.info("Connexion à Binance établie avec succès")
                return True
            else:
                logger.error(f"Échec de la connexion à Binance: {response.status_code} {response.text}")
                return False
        except Exception as e:
            logger.error(f"Erreur lors de la connexion à Binance: {str(e)}")
            return False
    
    def disconnect(self) -> bool:
        """
        Ferme la connexion avec Binance.
        
        Returns:
            True si la déconnexion est réussie, False sinon.
        """
        try:
            self.session.close()
            self.connected = False
            logger.info("Déconnexion de Binance réussie")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la déconnexion de Binance: {str(e)}")
            return False
    
    def _load_markets(self):
        """
        Charge les informations sur les marchés disponibles sur Binance.
        """
        try:
            response = self.session.get(f"{self.api_url}/v3/exchangeInfo")
            if response.status_code == 200:
                data = response.json()
                
                # Traiter les informations sur les symboles
                for symbol_data in data.get("symbols", []):
                    symbol = symbol_data.get("symbol")
                    
                    # Stocker les informations sur le symbole
                    self.symbol_info[symbol] = {
                        "baseAsset": symbol_data.get("baseAsset"),
                        "quoteAsset": symbol_data.get("quoteAsset"),
                        "status": symbol_data.get("status"),
                        "filters": symbol_data.get("filters", []),
                        "permissions": symbol_data.get("permissions", [])
                    }
                    
                    # Ajouter le symbole à la liste des symboles supportés
                    if symbol_data.get("status") == "TRADING" and symbol not in self.symbols:
                        self.symbols.append(symbol)
                
                logger.info(f"Informations sur les marchés chargées: {len(self.symbols)} symboles disponibles")
            else:
                logger.error(f"Échec du chargement des marchés: {response.status_code} {response.text}")
        except Exception as e:
            logger.error(f"Erreur lors du chargement des marchés: {str(e)}")
    
    def _get_symbol_filters(self, symbol: str) -> Dict[str, Any]:
        """
        Récupère les filtres pour un symbole.
        
        Args:
            symbol: Symbole de l'actif.
            
        Returns:
            Dictionnaire contenant les filtres pour le symbole.
        """
        filters = {}
        
        if symbol in self.symbol_info:
            symbol_filters = self.symbol_info[symbol].get("filters", [])
            
            for filter_data in symbol_filters:
                filter_type = filter_data.get("filterType")
                
                if filter_type == "PRICE_FILTER":
                    filters["minPrice"] = float(filter_data.get("minPrice", 0))
                    filters["maxPrice"] = float(filter_data.get("maxPrice", 0))
                    filters["tickSize"] = float(filter_data.get("tickSize", 0))
                
                elif filter_type == "LOT_SIZE":
                    filters["minQty"] = float(filter_data.get("minQty", 0))
                    filters["maxQty"] = float(filter_data.get("maxQty", 0))
                    filters["stepSize"] = float(filter_data.get("stepSize", 0))
                
                elif filter_type == "MIN_NOTIONAL":
                    filters["minNotional"] = float(filter_data.get("minNotional", 0))
        
        return filters
    
    def _sign_request(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Signe une requête avec la clé API secrète.
        
        Args:
            params: Paramètres de la requête.
            
        Returns:
            Paramètres signés.
        """
        # Ajouter le timestamp
        params["timestamp"] = int(time.time() * 1000)
        
        # Créer la chaîne de requête
        query_string = urlencode(params)
        
        # Signer la requête
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        
        # Ajouter la signature aux paramètres
        params["signature"] = signature
        
        return params
    
    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """
        Traite la réponse de l'API.
        
        Args:
            response: Réponse de l'API.
            
        Returns:
            Données de la réponse.
            
        Raises:
            Exception: Si la réponse contient une erreur.
        """
        if response.status_code == 200:
            return response.json()
        else:
            error_msg = f"Erreur API Binance: {response.status_code} {response.text}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def _request(self, method: str, endpoint: str, params: Dict[str, Any] = None, 
                signed: bool = False, api_version: str = "v3") -> Dict[str, Any]:
        """
        Envoie une requête à l'API Binance.
        
        Args:
            method: Méthode HTTP (GET, POST, DELETE, etc.).
            endpoint: Point de terminaison de l'API.
            params: Paramètres de la requête.
            signed: Si la requête doit être signée.
            api_version: Version de l'API.
            
        Returns:
            Données de la réponse.
        """
        # Initialiser les paramètres si nécessaire
        if params is None:
            params = {}
        
        # Construire l'URL
        url = f"{self.api_url}/{api_version}/{endpoint}"
        
        # Signer la requête si nécessaire
        if signed:
            params = self._sign_request(params)
            headers = {"X-MBX-APIKEY": self.api_key}
        else:
            headers = {}
        
        # Limiter le taux de requêtes
        self._limit_request_rate()
        
        # Envoyer la requête
        if method == "GET":
            response = self.session.get(url, params=params, headers=headers)
        elif method == "POST":
            response = self.session.post(url, data=params, headers=headers)
        elif method == "DELETE":
            response = self.session.delete(url, params=params, headers=headers)
        else:
            raise ValueError(f"Méthode HTTP non supportée: {method}")
        
        # Traiter la réponse
        return self._handle_response(response)
    
    def _limit_request_rate(self):
        """
        Limite le taux de requêtes pour respecter les limites de l'API.
        """
        current_time = time.time()
        
        # Limiter le taux de requêtes global
        if "global" in self.last_request_time:
            elapsed = current_time - self.last_request_time["global"]
            if elapsed < 1.0 / self.rate_limits["request"] * 60:
                time.sleep(1.0 / self.rate_limits["request"] * 60 - elapsed)
        
        self.last_request_time["global"] = time.time()
    
    def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Récupère le ticker pour un symbole.
        
        Args:
            symbol: Symbole de l'actif.
            
        Returns:
            Dictionnaire contenant les informations du ticker.
        """
        try:
            response = self._request("GET", "ticker/24hr", {"symbol": symbol})
            
            # Formater le ticker
            ticker = {
                "symbol": response.get("symbol"),
                "bid": float(response.get("bidPrice", 0)),
                "ask": float(response.get("askPrice", 0)),
                "last": float(response.get("lastPrice", 0)),
                "high": float(response.get("highPrice", 0)),
                "low": float(response.get("lowPrice", 0)),
                "volume": float(response.get("volume", 0)),
                "quoteVolume": float(response.get("quoteVolume", 0)),
                "timestamp": response.get("closeTime", 0),
                "change": float(response.get("priceChange", 0)),
                "percentage": float(response.get("priceChangePercent", 0)),
                "vwap": float(response.get("weightedAvgPrice", 0))
            }
            
            return ticker
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du ticker pour {symbol}: {str(e)}")
            return {}
    
    def fetch_order_book(self, symbol: str, limit: int = 10) -> Dict[str, Any]:
        """
        Récupère le carnet d'ordres pour un symbole.
        
        Args:
            symbol: Symbole de l'actif.
            limit: Nombre maximum d'ordres à récupérer.
            
        Returns:
            Dictionnaire contenant le carnet d'ordres.
        """
        try:
            response = self._request("GET", "depth", {"symbol": symbol, "limit": limit})
            
            # Formater le carnet d'ordres
            order_book = {
                "symbol": symbol,
                "bids": [[float(price), float(amount)] for price, amount in response.get("bids", [])],
                "asks": [[float(price), float(amount)] for price, amount in response.get("asks", [])],
                "timestamp": int(time.time() * 1000),
                "nonce": response.get("lastUpdateId", 0)
            }
            
            return order_book
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du carnet d'ordres pour {symbol}: {str(e)}")
            return {}
    
    def fetch_ohlcv(self, symbol: str, timeframe: str = "1h", limit: int = 100) -> List[List[float]]:
        """
        Récupère les bougies OHLCV pour un symbole.
        
        Args:
            symbol: Symbole de l'actif.
            timeframe: Intervalle des bougies (1m, 5m, 15m, 1h, 4h, 1d).
            limit: Nombre maximum de bougies à récupérer.
            
        Returns:
            Liste des bougies OHLCV.
        """
        try:
            # Convertir l'intervalle au format Binance
            interval_map = {
                "1m": "1m",
                "5m": "5m",
                "15m": "15m",
                "1h": "1h",
                "4h": "4h",
                "1d": "1d"
            }
            
            interval = interval_map.get(timeframe, "1h")
            
            response = self._request("GET", "klines", {
                "symbol": symbol,
                "interval": interval,
                "limit": limit
            })
            
            # Formater les bougies
            candles = []
            for candle_data in response:
                candle = [
                    candle_data[0],  # Timestamp d'ouverture
                    float(candle_data[1]),  # Prix d'ouverture
                    float(candle_data[2]),  # Prix le plus haut
                    float(candle_data[3]),  # Prix le plus bas
                    float(candle_data[4]),  # Prix de clôture
                    float(candle_data[5])   # Volume
                ]
                candles.append(candle)
            
            return candles
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des bougies pour {symbol}: {str(e)}")
            return []
    
    def fetch_balance(self) -> Dict[str, Any]:
        """
        Récupère le solde du compte.
        
        Returns:
            Dictionnaire contenant les soldes pour chaque actif.
        """
        try:
            response = self._request("GET", "account", {}, signed=True)
            
            # Formater les soldes
            balances = {}
            for balance_data in response.get("balances", []):
                asset = balance_data.get("asset")
                free = float(balance_data.get("free", 0))
                locked = float(balance_data.get("locked", 0))
                
                if free > 0 or locked > 0:
                    balances[asset] = {
                        "free": free,
                        "used": locked,
                        "total": free + locked
                    }
            
            return {
                "info": response,
                "balances": balances
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des soldes: {str(e)}")
            return {"balances": {}}
    
    def create_order(self, symbol: str, order_type: str, side: str, amount: float, 
                    price: Optional[float] = None, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Crée un ordre sur Binance.
        
        Args:
            symbol: Symbole de l'actif.
            order_type: Type d'ordre (LIMIT, MARKET, etc.).
            side: Côté de l'ordre (BUY, SELL).
            amount: Quantité à acheter/vendre.
            price: Prix de l'ordre (pour les ordres LIMIT).
            params: Paramètres supplémentaires.
            
        Returns:
            Dictionnaire contenant les informations de l'ordre créé.
        """
        try:
            # Initialiser les paramètres si nécessaire
            if params is None:
                params = {}
            
            # Préparer les paramètres de base
            order_params = {
                "symbol": symbol,
                "side": side.upper(),
                "type": order_type.upper(),
                "quantity": self._format_amount(symbol, amount)
            }
            
            # Ajouter le prix pour les ordres LIMIT
            if order_type.upper() == "LIMIT":
                if price is None:
                    raise ValueError("Le prix est requis pour les ordres LIMIT")
                
                order_params["price"] = self._format_price(symbol, price)
                order_params["timeInForce"] = params.get("timeInForce", "GTC")
            
            # Ajouter les paramètres supplémentaires
            order_params.update(params)
            
            # Créer l'ordre
            response = self._request("POST", "order", order_params, signed=True)
            
            # Formater la réponse
            order = {
                "id": str(response.get("orderId")),
                "symbol": response.get("symbol"),
                "type": response.get("type").lower(),
                "side": response.get("side").lower(),
                "price": float(response.get("price", 0)),
                "amount": float(response.get("origQty", 0)),
                "filled": float(response.get("executedQty", 0)),
                "status": response.get("status").lower(),
                "timestamp": response.get("transactTime", 0),
                "info": response
            }
            
            return order
            
        except Exception as e:
            logger.error(f"Erreur lors de la création de l'ordre pour {symbol}: {str(e)}")
            return {}
    
    def cancel_order(self, order_id: str, symbol: Optional[str] = None) -> Dict[str, Any]:
        """
        Annule un ordre sur Binance.
        
        Args:
            order_id: Identifiant de l'ordre à annuler.
            symbol: Symbole de l'actif (requis par Binance).
            
        Returns:
            Dictionnaire contenant les informations de l'ordre annulé.
        """
        try:
            if symbol is None:
                raise ValueError("Le symbole est requis pour annuler un ordre sur Binance")
            
            response = self._request("DELETE", "order", {
                "symbol": symbol,
                "orderId": order_id
            }, signed=True)
            
            # Formater la réponse
            order = {
                "id": str(response.get("orderId")),
                "symbol": response.get("symbol"),
                "status": "canceled",
                "info": response
            }
            
            return order
            
        except Exception as e:
            logger.error(f"Erreur lors de l'annulation de l'ordre {order_id}: {str(e)}")
            return {}
    
    def fetch_order(self, order_id: str, symbol: Optional[str] = None) -> Dict[str, Any]:
        """
        Récupère les informations d'un ordre.
        
        Args:
            order_id: Identifiant de l'ordre.
            symbol: Symbole de l'actif (requis par Binance).
            
        Returns:
            Dictionnaire contenant les informations de l'ordre.
        """
        try:
            if symbol is None:
                raise ValueError("Le symbole est requis pour récupérer un ordre sur Binance")
            
            response = self._request("GET", "order", {
                "symbol": symbol,
                "orderId": order_id
            }, signed=True)
            
            # Formater la réponse
            order = {
                "id": str(response.get("orderId")),
                "symbol": response.get("symbol"),
                "type": response.get("type").lower(),
                "side": response.get("side").lower(),
                "price": float(response.get("price", 0)),
                "amount": float(response.get("origQty", 0)),
                "filled": float(response.get("executedQty", 0)),
                "status": response.get("status").lower(),
                "timestamp": response.get("time", 0),
                "info": response
            }
            
            return order
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de l'ordre {order_id}: {str(e)}")
            return {}
    
    def fetch_orders(self, symbol: Optional[str] = None, since: Optional[int] = None, 
                    limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Récupère la liste des ordres.
        
        Args:
            symbol: Symbole de l'actif (requis par Binance).
            since: Timestamp à partir duquel récupérer les ordres.
            limit: Nombre maximum d'ordres à récupérer.
            
        Returns:
            Liste des ordres.
        """
        try:
            if symbol is None:
                raise ValueError("Le symbole est requis pour récupérer les ordres sur Binance")
            
            params = {"symbol": symbol}
            
            if since is not None:
                params["startTime"] = since
            
            if limit is not None:
                params["limit"] = limit
            
            response = self._request("GET", "allOrders", params, signed=True)
            
            # Formater la réponse
            orders = []
            for order_data in response:
                order = {
                    "id": str(order_data.get("orderId")),
                    "symbol": order_data.get("symbol"),
                    "type": order_data.get("type").lower(),
                    "side": order_data.get("side").lower(),
                    "price": float(order_data.get("price", 0)),
                    "amount": float(order_data.get("origQty", 0)),
                    "filled": float(order_data.get("executedQty", 0)),
                    "status": order_data.get("status").lower(),
                    "timestamp": order_data.get("time", 0),
                    "info": order_data
                }
                orders.append(order)
            
            return orders
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des ordres pour {symbol}: {str(e)}")
            return []
    
    def fetch_open_orders(self, symbol: Optional[str] = None, since: Optional[int] = None, 
                         limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Récupère la liste des ordres ouverts.
        
        Args:
            symbol: Symbole de l'actif (optionnel pour Binance).
            since: Timestamp à partir duquel récupérer les ordres (non utilisé par Binance).
            limit: Nombre maximum d'ordres à récupérer (non utilisé par Binance).
            
        Returns:
            Liste des ordres ouverts.
        """
        try:
            params = {}
            
            if symbol is not None:
                params["symbol"] = symbol
            
            response = self._request("GET", "openOrders", params, signed=True)
            
            # Formater la réponse
            orders = []
            for order_data in response:
                order = {
                    "id": str(order_data.get("orderId")),
                    "symbol": order_data.get("symbol"),
                    "type": order_data.get("type").lower(),
                    "side": order_data.get("side").lower(),
                    "price": float(order_data.get("price", 0)),
                    "amount": float(order_data.get("origQty", 0)),
                    "filled": float(order_data.get("executedQty", 0)),
                    "status": order_data.get("status").lower(),
                    "timestamp": order_data.get("time", 0),
                    "info": order_data
                }
                orders.append(order)
            
            return orders
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des ordres ouverts: {str(e)}")
            return []
    
    def _format_price(self, symbol: str, price: float) -> str:
        """
        Formate le prix selon les règles de Binance.
        
        Args:
            symbol: Symbole de l'actif.
            price: Prix à formater.
            
        Returns:
            Prix formaté.
        """
        filters = self._get_symbol_filters(symbol)
        
        if "tickSize" in filters and filters["tickSize"] > 0:
            tick_size = filters["tickSize"]
            return str(round(price / tick_size) * tick_size)
        
        return str(price)
    
    def _format_amount(self, symbol: str, amount: float) -> str:
        """
        Formate la quantité selon les règles de Binance.
        
        Args:
            symbol: Symbole de l'actif.
            amount: Quantité à formater.
            
        Returns:
            Quantité formatée.
        """
        filters = self._get_symbol_filters(symbol)
        
        if "stepSize" in filters and filters["stepSize"] > 0:
            step_size = filters["stepSize"]
            return str(round(amount / step_size) * step_size)
        
        return str(amount)
    
    def get_min_order_amount(self, symbol: str) -> float:
        """
        Récupère le montant minimum pour un ordre.
        
        Args:
            symbol: Symbole de l'actif.
            
        Returns:
            Montant minimum pour un ordre.
        """
        filters = self._get_symbol_filters(symbol)
        
        if "minQty" in filters:
            return filters["minQty"]
        
        return super().get_min_order_amount(symbol)
    
    def get_min_price_increment(self, symbol: str) -> float:
        """
        Récupère l'incrément minimum de prix pour un symbole.
        
        Args:
            symbol: Symbole de l'actif.
            
        Returns:
            Incrément minimum de prix.
        """
        filters = self._get_symbol_filters(symbol)
        
        if "tickSize" in filters:
            return filters["tickSize"]
        
        return super().get_min_price_increment(symbol)
    
    def get_min_amount_increment(self, symbol: str) -> float:
        """
        Récupère l'incrément minimum de quantité pour un symbole.
        
        Args:
            symbol: Symbole de l'actif.
            
        Returns:
            Incrément minimum de quantité.
        """
        filters = self._get_symbol_filters(symbol)
        
        if "stepSize" in filters:
            return filters["stepSize"]
        
        return super().get_min_amount_increment(symbol)
