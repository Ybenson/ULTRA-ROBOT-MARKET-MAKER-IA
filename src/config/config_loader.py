#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module de chargement de configuration pour ULTRA-ROBOT MARKET MAKER IA.

Ce module gère le chargement et la validation des configurations à partir de fichiers YAML.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from loguru import logger


class ConfigLoader:
    """
    Classe pour charger et valider les configurations du bot.
    
    Cette classe gère le chargement des fichiers de configuration YAML,
    la validation des paramètres requis et la fusion avec les valeurs par défaut.
    """
    
    def __init__(self, config_path: Path, env_prefix: str = "ULTRA_BOT_"):
        """
        Initialise le chargeur de configuration.
        
        Args:
            config_path: Chemin vers le fichier de configuration YAML.
            env_prefix: Préfixe pour les variables d'environnement qui peuvent remplacer
                       les paramètres de configuration.
        """
        self.config_path = config_path
        self.env_prefix = env_prefix
        self.required_fields = {
            "general": ["bot_name", "mode"],
            "markets": ["enabled_markets"],
            "risk_management": ["max_position_size", "max_drawdown_percent"],
            "execution": ["order_type", "max_slippage_percent"],
        }
        
    def load(self) -> Dict[str, Any]:
        """
        Charge la configuration à partir du fichier YAML et des variables d'environnement.
        
        Returns:
            Dict contenant la configuration complète.
        
        Raises:
            FileNotFoundError: Si le fichier de configuration n'existe pas.
            ValueError: Si la configuration est invalide ou incomplète.
        """
        if not self.config_path.exists():
            raise FileNotFoundError(f"Fichier de configuration non trouvé: {self.config_path}")
        
        # Charger la configuration depuis le fichier YAML
        with open(self.config_path, 'r', encoding='utf-8') as file:
            config = yaml.safe_load(file)
        
        # Fusionner avec les valeurs par défaut
        config = self._merge_with_defaults(config)
        
        # Remplacer les valeurs par des variables d'environnement si elles existent
        config = self._override_from_env(config)
        
        # Valider la configuration
        self._validate_config(config)
        
        return config
    
    def _merge_with_defaults(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fusionne la configuration chargée avec les valeurs par défaut.
        
        Args:
            config: Configuration chargée depuis le fichier YAML.
            
        Returns:
            Configuration fusionnée avec les valeurs par défaut.
        """
        # Définir les valeurs par défaut
        defaults = {
            "general": {
                "bot_name": "ULTRA-ROBOT-MARKET-MAKER",
                "mode": "simulation",
                "log_level": "INFO",
            },
            "markets": {
                "enabled_markets": ["crypto"],
                "default_market": "crypto",
            },
            "risk_management": {
                "max_position_size": 1000,
                "max_drawdown_percent": 5.0,
                "stop_loss_percent": 2.0,
                "take_profit_percent": 5.0,
                "max_open_orders": 10,
            },
            "execution": {
                "order_type": "limit",
                "max_slippage_percent": 0.1,
                "retry_attempts": 3,
                "retry_delay_seconds": 1,
            },
            "ai": {
                "enabled": True,
                "model_type": "reinforcement_learning",
                "update_frequency_seconds": 300,
            },
        }
        
        # Fusionner récursivement les dictionnaires
        merged_config = defaults.copy()
        for key, value in config.items():
            if key in merged_config and isinstance(merged_config[key], dict) and isinstance(value, dict):
                merged_config[key].update(value)
            else:
                merged_config[key] = value
                
        return merged_config
    
    def _override_from_env(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remplace les valeurs de configuration par des variables d'environnement si elles existent.
        
        Args:
            config: Configuration à mettre à jour.
            
        Returns:
            Configuration mise à jour avec les valeurs des variables d'environnement.
        """
        for section_key, section_value in config.items():
            if isinstance(section_value, dict):
                for key in section_value:
                    env_var_name = f"{self.env_prefix}{section_key.upper()}_{key.upper()}"
                    if env_var_name in os.environ:
                        # Convertir la valeur au type approprié
                        original_value = section_value[key]
                        env_value = os.environ[env_var_name]
                        
                        if isinstance(original_value, bool):
                            section_value[key] = env_value.lower() in ('true', 'yes', '1')
                        elif isinstance(original_value, int):
                            section_value[key] = int(env_value)
                        elif isinstance(original_value, float):
                            section_value[key] = float(env_value)
                        elif isinstance(original_value, list):
                            section_value[key] = env_value.split(',')
                        else:
                            section_value[key] = env_value
                            
                        logger.debug(f"Remplacement de la configuration {section_key}.{key} par la variable d'environnement {env_var_name}")
        
        return config
    
    def _validate_config(self, config: Dict[str, Any]) -> None:
        """
        Valide que la configuration contient tous les champs requis.
        
        Args:
            config: Configuration à valider.
            
        Raises:
            ValueError: Si des champs requis sont manquants.
        """
        missing_fields = []
        
        for section, fields in self.required_fields.items():
            if section not in config:
                missing_fields.append(f"Section '{section}'")
                continue
                
            for field in fields:
                if field not in config[section]:
                    missing_fields.append(f"Champ '{section}.{field}'")
        
        if missing_fields:
            raise ValueError(f"Configuration invalide. Champs manquants: {', '.join(missing_fields)}")
