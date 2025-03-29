#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ULTRA-ROBOT MARKET MAKER IA
---------------------------
Point d'entrée principal pour le bot de market making ultra-puissant avec IA.

Ce script initialise et lance le bot avec les configurations spécifiées.
"""

import argparse
import os
import sys
import logging
import yaml
from pathlib import Path
from loguru import logger

# Importer les composants principaux du bot
from src.core.engine import MarketMakingEngine
from src.config.config_loader import ConfigLoader
from src.utils.logger_setup import setup_logger


def parse_arguments():
    """Parse les arguments de ligne de commande."""
    parser = argparse.ArgumentParser(description="ULTRA-ROBOT MARKET MAKER IA")
    parser.add_argument(
        "--config",
        type=str,
        default="config/default.yaml",
        help="Chemin vers le fichier de configuration"
    )
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Niveau de journalisation"
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["live", "backtest", "paper", "simulation"],
        default="simulation",
        help="Mode d'exécution du bot"
    )
    return parser.parse_args()


def main():
    """Fonction principale pour initialiser et exécuter le bot."""
    # Analyser les arguments
    args = parse_arguments()
    
    # Configurer la journalisation
    setup_logger(args.log_level)
    logger.info(f"Démarrage du bot en mode {args.mode}")
    
    try:
        # Charger la configuration
        config_path = Path(args.config)
        if not config_path.exists():
            logger.error(f"Fichier de configuration non trouvé: {config_path}")
            sys.exit(1)
            
        config_loader = ConfigLoader(config_path)
        config = config_loader.load()
        
        logger.info(f"Configuration chargée depuis {config_path}")
        
        # Initialiser le moteur de market making
        engine = MarketMakingEngine(
            config=config,
            mode=args.mode
        )
        
        # Démarrer le bot
        logger.info("Initialisation du moteur de market making...")
        engine.initialize()
        
        logger.info("Démarrage du bot de market making...")
        engine.start()
        
    except KeyboardInterrupt:
        logger.info("Arrêt du bot par l'utilisateur")
        if 'engine' in locals():
            engine.stop()
        sys.exit(0)
    except Exception as e:
        logger.exception(f"Erreur critique: {str(e)}")
        if 'engine' in locals():
            engine.stop()
        sys.exit(1)


if __name__ == "__main__":
    main()
