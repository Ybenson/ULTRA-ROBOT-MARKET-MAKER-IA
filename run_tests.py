#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour exécuter les tests unitaires et d'intégration d'ULTRA-ROBOT MARKET MAKER IA.

Ce script permet de lancer facilement les tests unitaires et d'intégration
pour vérifier le bon fonctionnement du bot de market making.
"""

import os
import sys
import unittest
import argparse
import time
from loguru import logger


def run_unit_tests(test_pattern=None):
    """
    Exécute les tests unitaires.
    
    Args:
        test_pattern: Motif pour filtrer les tests à exécuter.
    
    Returns:
        True si tous les tests ont réussi, False sinon.
    """
    logger.info("Exécution des tests unitaires...")
    
    # Créer le chargeur de tests
    loader = unittest.TestLoader()
    
    # Charger les tests
    if test_pattern:
        suite = loader.discover("tests", pattern=test_pattern)
    else:
        suite = loader.discover("tests", pattern="test_*.py")
    
    # Exécuter les tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Afficher le résultat
    logger.info(f"Tests unitaires terminés: {result.testsRun} tests exécutés")
    logger.info(f"Succès: {result.testsRun - len(result.failures) - len(result.errors)}")
    logger.info(f"Échecs: {len(result.failures)}")
    logger.info(f"Erreurs: {len(result.errors)}")
    
    # Retourner True si tous les tests ont réussi
    return len(result.failures) == 0 and len(result.errors) == 0


def run_integration_tests():
    """
    Exécute les tests d'intégration.
    
    Returns:
        True si tous les tests ont réussi, False sinon.
    """
    logger.info("Exécution des tests d'intégration...")
    
    # Créer le chargeur de tests
    loader = unittest.TestLoader()
    
    # Charger les tests d'intégration
    suite = loader.discover("tests", pattern="test_integration.py")
    
    # Exécuter les tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Afficher le résultat
    logger.info(f"Tests d'intégration terminés: {result.testsRun} tests exécutés")
    logger.info(f"Succès: {result.testsRun - len(result.failures) - len(result.errors)}")
    logger.info(f"Échecs: {len(result.failures)}")
    logger.info(f"Erreurs: {len(result.errors)}")
    
    # Retourner True si tous les tests ont réussi
    return len(result.failures) == 0 and len(result.errors) == 0


def run_specific_test(test_name):
    """
    Exécute un test spécifique.
    
    Args:
        test_name: Nom du test à exécuter.
    
    Returns:
        True si le test a réussi, False sinon.
    """
    logger.info(f"Exécution du test spécifique: {test_name}")
    
    # Créer le chargeur de tests
    loader = unittest.TestLoader()
    
    # Charger le test spécifique
    try:
        if "." in test_name:
            # Format: module.classe.méthode
            parts = test_name.split(".")
            
            if len(parts) == 2:
                # Format: module.classe
                module_name, class_name = parts
                suite = loader.loadTestsFromName(f"tests.{module_name}.{class_name}")
            elif len(parts) == 3:
                # Format: module.classe.méthode
                module_name, class_name, method_name = parts
                suite = loader.loadTestsFromName(f"tests.{module_name}.{class_name}.{method_name}")
            else:
                logger.error(f"Format de nom de test invalide: {test_name}")
                return False
        else:
            # Format: nom de fichier
            suite = loader.discover("tests", pattern=f"{test_name}.py")
    
    except Exception as e:
        logger.error(f"Erreur lors du chargement du test {test_name}: {str(e)}")
        return False
    
    # Exécuter le test
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Afficher le résultat
    logger.info(f"Test spécifique terminé: {result.testsRun} tests exécutés")
    logger.info(f"Succès: {result.testsRun - len(result.failures) - len(result.errors)}")
    logger.info(f"Échecs: {len(result.failures)}")
    logger.info(f"Erreurs: {len(result.errors)}")
    
    # Retourner True si tous les tests ont réussi
    return len(result.failures) == 0 and len(result.errors) == 0


def main():
    """
    Fonction principale.
    """
    # Analyser les arguments de la ligne de commande
    parser = argparse.ArgumentParser(description="Exécuter les tests d'ULTRA-ROBOT MARKET MAKER IA")
    parser.add_argument("--unit", action="store_true", help="Exécuter les tests unitaires")
    parser.add_argument("--integration", action="store_true", help="Exécuter les tests d'intégration")
    parser.add_argument("--all", action="store_true", help="Exécuter tous les tests")
    parser.add_argument("--test", type=str, help="Exécuter un test spécifique")
    parser.add_argument("--pattern", type=str, help="Motif pour filtrer les tests à exécuter")
    args = parser.parse_args()
    
    # Configurer la journalisation
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    
    # Mesurer le temps d'exécution
    start_time = time.time()
    
    # Exécuter les tests
    success = True
    
    if args.test:
        # Exécuter un test spécifique
        success = run_specific_test(args.test)
    elif args.all:
        # Exécuter tous les tests
        unit_success = run_unit_tests(args.pattern)
        integration_success = run_integration_tests()
        success = unit_success and integration_success
    elif args.unit:
        # Exécuter les tests unitaires
        success = run_unit_tests(args.pattern)
    elif args.integration:
        # Exécuter les tests d'intégration
        success = run_integration_tests()
    else:
        # Par défaut, exécuter les tests unitaires
        success = run_unit_tests(args.pattern)
    
    # Afficher le temps d'exécution
    execution_time = time.time() - start_time
    logger.info(f"Temps d'exécution total: {execution_time:.2f} secondes")
    
    # Retourner le code de sortie
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
