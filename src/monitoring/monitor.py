#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module de surveillance pour ULTRA-ROBOT MARKET MAKER IA.

Ce module fournit des fonctionnalités pour surveiller les performances du bot,
générer des alertes et afficher un tableau de bord en temps réel.
"""

import time
import threading
import json
import os
import datetime
from typing import Dict, Any, List, Optional, Tuple, Union, Callable
from loguru import logger
import pandas as pd
import numpy as np
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objs as go
import plotly.express as px


class Monitor:
    """
    Classe de surveillance pour le bot de market making.
    
    Cette classe fournit des fonctionnalités pour surveiller les performances
    du bot, générer des alertes et afficher un tableau de bord en temps réel.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialise le moniteur.
        
        Args:
            config: Configuration du moniteur.
        """
        self.config = config
        
        # Paramètres de configuration
        self.dashboard_enabled = config.get("dashboard_enabled", True)
        self.dashboard_port = config.get("dashboard_port", 8050)
        self.metrics_interval_seconds = config.get("metrics_interval_seconds", 60)
        self.alert_enabled = config.get("alert_enabled", True)
        self.alert_channels = config.get("alert_channels", [])
        self.performance_metrics = config.get("performance_metrics", ["pnl", "sharpe_ratio", "drawdown", "win_rate", "volume"])
        
        # Données de surveillance
        self.metrics = {
            "pnl": [],
            "sharpe_ratio": [],
            "drawdown": [],
            "win_rate": [],
            "volume": [],
            "order_count": [],
            "trade_count": [],
            "latency": [],
            "spread": [],
            "volatility": [],
            "market_impact": []
        }
        
        # Horodatages des métriques
        self.timestamps = []
        
        # Alertes
        self.alerts = []
        self.alert_callbacks = {}
        
        # État interne
        self.running = False
        self.update_thread = None
        self.dashboard_thread = None
        self.dashboard_app = None
        
        # Callbacks pour récupérer les données
        self.data_callbacks = {}
        
        # Verrou pour les opérations thread-safe
        self.lock = threading.RLock()
        
        logger.info("Moniteur initialisé")
    
    def start(self):
        """
        Démarre le moniteur.
        """
        if self.running:
            logger.warning("Le moniteur est déjà en cours d'exécution")
            return
        
        logger.info("Démarrage du moniteur...")
        
        # Démarrer le thread de mise à jour des métriques
        self.running = True
        self.update_thread = threading.Thread(target=self._update_loop)
        self.update_thread.daemon = True
        self.update_thread.start()
        
        # Démarrer le tableau de bord si activé
        if self.dashboard_enabled:
            self._start_dashboard()
        
        logger.info("Moniteur démarré")
    
    def stop(self):
        """
        Arrête le moniteur.
        """
        if not self.running:
            logger.warning("Le moniteur n'est pas en cours d'exécution")
            return
        
        logger.info("Arrêt du moniteur...")
        
        # Arrêter le thread de mise à jour
        self.running = False
        
        # Attendre que le thread de mise à jour se termine
        if self.update_thread and self.update_thread.is_alive():
            self.update_thread.join(timeout=10)
        
        logger.info("Moniteur arrêté")
    
    def register_data_callback(self, metric_name: str, callback: Callable[[], Any]):
        """
        Enregistre un callback pour récupérer les données d'une métrique.
        
        Args:
            metric_name: Nom de la métrique.
            callback: Fonction de callback qui renvoie la valeur de la métrique.
        """
        with self.lock:
            self.data_callbacks[metric_name] = callback
            logger.info(f"Callback enregistré pour la métrique {metric_name}")
    
    def register_alert_callback(self, alert_type: str, callback: Callable[[Dict[str, Any]], None]):
        """
        Enregistre un callback pour traiter les alertes.
        
        Args:
            alert_type: Type d'alerte.
            callback: Fonction de callback qui traite l'alerte.
        """
        with self.lock:
            self.alert_callbacks[alert_type] = callback
            logger.info(f"Callback enregistré pour les alertes de type {alert_type}")
    
    def add_metric(self, metric_name: str, value: float):
        """
        Ajoute une valeur à une métrique.
        
        Args:
            metric_name: Nom de la métrique.
            value: Valeur de la métrique.
        """
        with self.lock:
            if metric_name in self.metrics:
                self.metrics[metric_name].append(value)
                
                # Ajouter un horodatage si c'est la première métrique ajoutée à ce cycle
                if len(self.timestamps) < len(self.metrics[metric_name]):
                    self.timestamps.append(datetime.datetime.now())
                
                logger.debug(f"Métrique {metric_name} mise à jour: {value}")
            else:
                logger.warning(f"Métrique inconnue: {metric_name}")
    
    def get_metrics(self, metric_name: Optional[str] = None, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Récupère les métriques.
        
        Args:
            metric_name: Nom de la métrique à récupérer (si None, récupère toutes les métriques).
            limit: Nombre maximum de valeurs à récupérer (si None, récupère toutes les valeurs).
            
        Returns:
            Dictionnaire des métriques.
        """
        with self.lock:
            if metric_name:
                if metric_name in self.metrics:
                    values = self.metrics[metric_name]
                    if limit:
                        values = values[-limit:]
                    
                    timestamps = self.timestamps
                    if limit:
                        timestamps = timestamps[-limit:]
                    
                    return {
                        "name": metric_name,
                        "values": values,
                        "timestamps": timestamps
                    }
                else:
                    logger.warning(f"Métrique inconnue: {metric_name}")
                    return {"name": metric_name, "values": [], "timestamps": []}
            else:
                result = {}
                for name, values in self.metrics.items():
                    if limit:
                        result[name] = values[-limit:]
                    else:
                        result[name] = values
                
                timestamps = self.timestamps
                if limit:
                    timestamps = timestamps[-limit:]
                
                return {
                    "metrics": result,
                    "timestamps": timestamps
                }
    
    def add_alert(self, alert_type: str, message: str, level: str = "info", data: Optional[Dict[str, Any]] = None):
        """
        Ajoute une alerte.
        
        Args:
            alert_type: Type d'alerte.
            message: Message de l'alerte.
            level: Niveau de l'alerte (info, warning, error, critical).
            data: Données supplémentaires de l'alerte.
        """
        with self.lock:
            # Créer l'alerte
            alert = {
                "type": alert_type,
                "message": message,
                "level": level,
                "timestamp": datetime.datetime.now(),
                "data": data or {}
            }
            
            # Ajouter l'alerte à la liste
            self.alerts.append(alert)
            
            # Journaliser l'alerte
            log_message = f"Alerte {alert_type} ({level}): {message}"
            if level == "info":
                logger.info(log_message)
            elif level == "warning":
                logger.warning(log_message)
            elif level == "error":
                logger.error(log_message)
            elif level == "critical":
                logger.critical(log_message)
            
            # Traiter l'alerte si un callback est enregistré
            if alert_type in self.alert_callbacks:
                try:
                    self.alert_callbacks[alert_type](alert)
                except Exception as e:
                    logger.error(f"Erreur lors du traitement de l'alerte {alert_type}: {str(e)}")
            
            # Envoyer l'alerte via les canaux configurés
            if self.alert_enabled:
                self._send_alert(alert)
    
    def get_alerts(self, alert_type: Optional[str] = None, level: Optional[str] = None, 
                  limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Récupère les alertes.
        
        Args:
            alert_type: Type d'alerte à récupérer (si None, récupère toutes les alertes).
            level: Niveau d'alerte à récupérer (si None, récupère tous les niveaux).
            limit: Nombre maximum d'alertes à récupérer (si None, récupère toutes les alertes).
            
        Returns:
            Liste des alertes.
        """
        with self.lock:
            # Filtrer les alertes
            filtered_alerts = self.alerts
            
            if alert_type:
                filtered_alerts = [alert for alert in filtered_alerts if alert["type"] == alert_type]
            
            if level:
                filtered_alerts = [alert for alert in filtered_alerts if alert["level"] == level]
            
            # Limiter le nombre d'alertes
            if limit:
                filtered_alerts = filtered_alerts[-limit:]
            
            return filtered_alerts
    
    def clear_alerts(self, alert_type: Optional[str] = None, level: Optional[str] = None):
        """
        Efface les alertes.
        
        Args:
            alert_type: Type d'alerte à effacer (si None, efface toutes les alertes).
            level: Niveau d'alerte à effacer (si None, efface tous les niveaux).
        """
        with self.lock:
            if alert_type or level:
                # Filtrer les alertes à conserver
                if alert_type and level:
                    self.alerts = [alert for alert in self.alerts if alert["type"] != alert_type or alert["level"] != level]
                elif alert_type:
                    self.alerts = [alert for alert in self.alerts if alert["type"] != alert_type]
                elif level:
                    self.alerts = [alert for alert in self.alerts if alert["level"] != level]
            else:
                # Effacer toutes les alertes
                self.alerts = []
            
            logger.info("Alertes effacées")
    
    def _update_loop(self):
        """
        Boucle de mise à jour des métriques.
        """
        logger.info("Démarrage de la boucle de mise à jour des métriques")
        
        while self.running:
            try:
                # Mettre à jour les métriques
                self._update_metrics()
                
                # Vérifier les conditions d'alerte
                self._check_alert_conditions()
                
                # Attendre avant la prochaine mise à jour
                time.sleep(self.metrics_interval_seconds)
                
            except Exception as e:
                logger.error(f"Erreur dans la boucle de mise à jour des métriques: {str(e)}")
                time.sleep(1)  # Attendre un peu avant de réessayer
    
    def _update_metrics(self):
        """
        Met à jour les métriques en appelant les callbacks enregistrés.
        """
        with self.lock:
            for metric_name, callback in self.data_callbacks.items():
                try:
                    # Appeler le callback pour récupérer la valeur de la métrique
                    value = callback()
                    
                    # Ajouter la valeur à la métrique
                    self.add_metric(metric_name, value)
                    
                except Exception as e:
                    logger.error(f"Erreur lors de la mise à jour de la métrique {metric_name}: {str(e)}")
    
    def _check_alert_conditions(self):
        """
        Vérifie les conditions d'alerte.
        """
        # Cette méthode peut être étendue pour vérifier des conditions d'alerte spécifiques
        # Par exemple, alerter si le P&L descend en dessous d'un certain seuil
        pass
    
    def _send_alert(self, alert: Dict[str, Any]):
        """
        Envoie une alerte via les canaux configurés.
        
        Args:
            alert: Alerte à envoyer.
        """
        for channel in self.alert_channels:
            try:
                channel_type = channel.get("type", "")
                
                if channel_type == "email":
                    self._send_email_alert(alert, channel)
                elif channel_type == "telegram":
                    self._send_telegram_alert(alert, channel)
                elif channel_type == "webhook":
                    self._send_webhook_alert(alert, channel)
                else:
                    logger.warning(f"Type de canal d'alerte inconnu: {channel_type}")
                
            except Exception as e:
                logger.error(f"Erreur lors de l'envoi de l'alerte via le canal {channel.get('type', '')}: {str(e)}")
    
    def _send_email_alert(self, alert: Dict[str, Any], channel: Dict[str, Any]):
        """
        Envoie une alerte par email.
        
        Args:
            alert: Alerte à envoyer.
            channel: Configuration du canal d'alerte.
        """
        # Cette méthode devrait être implémentée pour envoyer un email
        # Utiliser une bibliothèque comme smtplib
        recipients = channel.get("recipients", [])
        logger.info(f"Envoi d'une alerte par email à {recipients}: {alert['message']}")
    
    def _send_telegram_alert(self, alert: Dict[str, Any], channel: Dict[str, Any]):
        """
        Envoie une alerte via Telegram.
        
        Args:
            alert: Alerte à envoyer.
            channel: Configuration du canal d'alerte.
        """
        # Cette méthode devrait être implémentée pour envoyer un message Telegram
        # Utiliser une bibliothèque comme python-telegram-bot
        chat_id_env = channel.get("chat_id_env", "")
        logger.info(f"Envoi d'une alerte via Telegram au chat {chat_id_env}: {alert['message']}")
    
    def _send_webhook_alert(self, alert: Dict[str, Any], channel: Dict[str, Any]):
        """
        Envoie une alerte via webhook.
        
        Args:
            alert: Alerte à envoyer.
            channel: Configuration du canal d'alerte.
        """
        # Cette méthode devrait être implémentée pour envoyer une requête HTTP
        # Utiliser une bibliothèque comme requests
        url = channel.get("url", "")
        logger.info(f"Envoi d'une alerte via webhook à {url}: {alert['message']}")
    
    def _start_dashboard(self):
        """
        Démarre le tableau de bord.
        """
        logger.info("Démarrage du tableau de bord...")
        
        # Créer l'application Dash
        self.dashboard_app = dash.Dash(__name__)
        
        # Définir la mise en page du tableau de bord
        self.dashboard_app.layout = html.Div([
            html.H1("ULTRA-ROBOT MARKET MAKER IA - Tableau de Bord"),
            
            html.Div([
                html.H2("Performance"),
                dcc.Graph(id="performance-graph"),
                dcc.Interval(
                    id="performance-interval",
                    interval=self.metrics_interval_seconds * 1000,  # en millisecondes
                    n_intervals=0
                )
            ]),
            
            html.Div([
                html.H2("Métriques"),
                dcc.Dropdown(
                    id="metric-dropdown",
                    options=[{"label": metric, "value": metric} for metric in self.metrics.keys()],
                    value=self.performance_metrics[0] if self.performance_metrics else None,
                    multi=False
                ),
                dcc.Graph(id="metric-graph"),
                dcc.Interval(
                    id="metric-interval",
                    interval=self.metrics_interval_seconds * 1000,  # en millisecondes
                    n_intervals=0
                )
            ]),
            
            html.Div([
                html.H2("Alertes"),
                html.Div(id="alerts-table"),
                dcc.Interval(
                    id="alerts-interval",
                    interval=self.metrics_interval_seconds * 1000,  # en millisecondes
                    n_intervals=0
                )
            ])
        ])
        
        # Définir les callbacks
        @self.dashboard_app.callback(
            Output("performance-graph", "figure"),
            [Input("performance-interval", "n_intervals")]
        )
        def update_performance_graph(n):
            return self._create_performance_figure()
        
        @self.dashboard_app.callback(
            Output("metric-graph", "figure"),
            [Input("metric-interval", "n_intervals"),
             Input("metric-dropdown", "value")]
        )
        def update_metric_graph(n, metric_name):
            return self._create_metric_figure(metric_name)
        
        @self.dashboard_app.callback(
            Output("alerts-table", "children"),
            [Input("alerts-interval", "n_intervals")]
        )
        def update_alerts_table(n):
            return self._create_alerts_table()
        
        # Démarrer le serveur Dash dans un thread séparé
        self.dashboard_thread = threading.Thread(
            target=self.dashboard_app.run_server,
            kwargs={"debug": False, "port": self.dashboard_port}
        )
        self.dashboard_thread.daemon = True
        self.dashboard_thread.start()
        
        logger.info(f"Tableau de bord démarré sur le port {self.dashboard_port}")
    
    def _create_performance_figure(self):
        """
        Crée la figure pour le graphique de performance.
        
        Returns:
            Figure Plotly.
        """
        # Récupérer les métriques de performance
        metrics_data = {}
        timestamps = []
        
        with self.lock:
            for metric_name in self.performance_metrics:
                if metric_name in self.metrics and self.metrics[metric_name]:
                    metrics_data[metric_name] = self.metrics[metric_name]
            
            if self.timestamps:
                timestamps = self.timestamps
        
        # Créer la figure
        fig = go.Figure()
        
        for metric_name, values in metrics_data.items():
            if values and len(values) == len(timestamps):
                fig.add_trace(go.Scatter(
                    x=timestamps,
                    y=values,
                    mode="lines",
                    name=metric_name
                ))
        
        # Mettre à jour la mise en page
        fig.update_layout(
            title="Performance du Bot",
            xaxis_title="Temps",
            yaxis_title="Valeur",
            legend_title="Métriques",
            hovermode="x unified"
        )
        
        return fig
    
    def _create_metric_figure(self, metric_name: str):
        """
        Crée la figure pour le graphique d'une métrique.
        
        Args:
            metric_name: Nom de la métrique.
            
        Returns:
            Figure Plotly.
        """
        # Récupérer les données de la métrique
        metric_data = self.get_metrics(metric_name)
        
        # Créer la figure
        fig = go.Figure()
        
        if metric_data["values"] and metric_data["timestamps"]:
            fig.add_trace(go.Scatter(
                x=metric_data["timestamps"],
                y=metric_data["values"],
                mode="lines",
                name=metric_name
            ))
        
        # Mettre à jour la mise en page
        fig.update_layout(
            title=f"Métrique: {metric_name}",
            xaxis_title="Temps",
            yaxis_title="Valeur",
            hovermode="x"
        )
        
        return fig
    
    def _create_alerts_table(self):
        """
        Crée le tableau des alertes.
        
        Returns:
            Composant HTML pour le tableau des alertes.
        """
        # Récupérer les alertes
        alerts = self.get_alerts(limit=10)  # Limiter aux 10 dernières alertes
        
        # Créer le tableau
        table_header = [
            html.Thead(html.Tr([
                html.Th("Horodatage"),
                html.Th("Type"),
                html.Th("Niveau"),
                html.Th("Message")
            ]))
        ]
        
        table_rows = []
        for alert in alerts:
            row = html.Tr([
                html.Td(alert["timestamp"].strftime("%Y-%m-%d %H:%M:%S")),
                html.Td(alert["type"]),
                html.Td(alert["level"]),
                html.Td(alert["message"])
            ])
            table_rows.append(row)
        
        table_body = [html.Tbody(table_rows)]
        
        return html.Table(table_header + table_body)
