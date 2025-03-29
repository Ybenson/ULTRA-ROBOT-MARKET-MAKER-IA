# ULTRA-ROBOT MARKET MAKER IA

## Aperçu
Un bot de market making ultra-puissant, piloté par IA, conçu pour opérer sur plusieurs marchés financiers (cryptomonnaies, actions, forex, matières premières) avec haute performance, gestion avancée des risques et rentabilité optimale.

## Caractéristiques Principales
- **Support Multi-Marchés**: Fonctionne de manière transparente sur les cryptos, actions, forex et matières premières
- **Stratégies Optimisées par IA**: Utilise l'apprentissage machine avancé pour ajuster dynamiquement les spreads et positions
- **Exécution Ultra-Rapide**: Architecture à faible latence avec WebSockets et code optimisé
- **Gestion Avancée des Risques**: Stop-loss dynamique, protection anti-manipulation et couverture intelligente
- **Stratégies Combinées**: Intègre plusieurs approches de trading pour une rentabilité maximale, incluant l'arbitrage statistique
- **Surveillance en Temps Réel**: Tableaux de bord interactifs avec Dash/Plotly et système d'alertes configurable
- **Architecture Évolutive**: Conçue pour gérer plusieurs marchés et opérations à haute fréquence
- **Modularité**: Architecture modulaire permettant d'ajouter facilement de nouvelles stratégies et connecteurs d'échange

## Structure du Projet
```
ULTRA-ROBOT-MARKET-MAKER-IA/
├── src/
│   ├── core/           # Moteur principal de market making
│   ├── strategies/     # Implémentation des stratégies de trading
│   │   ├── base_strategy.py                  # Classe de base pour toutes les stratégies
│   │   ├── statistical_arbitrage_strategy.py # Stratégie d'arbitrage statistique
│   │   ├── market_making_strategy.py         # Stratégie de market making de base
│   │   ├── adaptive_market_making_strategy.py # Stratégie de market making adaptative
│   │   └── combined_strategy.py              # Stratégie combinée multi-approches
│   ├── risk_management/# Contrôle des risques et gestion des positions
│   ├── execution/      # Exécution des ordres et optimisation de la latence
│   ├── data/           # Gestion et stockage des données de marché
│   │   └── market_data_manager.py      # Gestionnaire de données de marché en temps réel
│   ├── ai/             # Modèles d'IA pour l'optimisation des spreads
│   ├── exchanges/      # Connecteurs aux API des exchanges
│   │   ├── base_exchange.py            # Interface commune pour tous les exchanges
│   │   └── binance_exchange.py         # Implémentation spécifique pour Binance
│   ├── monitoring/     # Surveillance et alertes
│   │   └── monitor.py                  # Module de surveillance avec tableau de bord
│   └── main.py         # Point d'entrée principal de l'application
├── tests/              # Tests unitaires et d'intégration
│   ├── test_market_data_manager.py     # Tests pour le gestionnaire de données
│   ├── test_statistical_arbitrage_strategy.py  # Tests pour la stratégie d'arbitrage
│   └── test_integration.py             # Tests d'intégration du système complet
├── config/             # Fichiers de configuration
│   └── default.yaml    # Configuration par défaut
├── logs/               # Journaux d'exécution
├── data/               # Données persistantes
├── Dockerfile          # Configuration Docker pour le déploiement
├── requirements.txt    # Dépendances Python
├── run_tests.py        # Script pour exécuter les tests unitaires et d'intégration
└── README.md           # Documentation du projet
```

## Fonctionnalités Détaillées

### Gestionnaire de Données de Marché
- Collecte de données en temps réel via WebSockets
- Calcul d'indicateurs avancés (volatilité, volume, tendances)
- Gestion efficace du cache avec verrous thread-safe
- Analyse de la profondeur du carnet d'ordres et des spreads

### Connecteurs d'Échanges
- Interface commune pour tous les exchanges
- Implémentation spécifique pour Binance avec gestion des limites d'API
- Support pour les ordres limites, au marché et iceberg
- Gestion robuste des erreurs et reconnexions

### Stratégies de Trading
- **Arbitrage Statistique**: Exploite les déviations temporaires entre paires d'actifs corrélés
- **Market Making de Base**: Place des ordres d'achat et de vente autour du prix du marché avec un spread défini
- **Market Making Adaptatif**: Ajuste dynamiquement les spreads en fonction des conditions du marché
- **Stratégie Combinée**: Agrège intelligemment les signaux de plusieurs stratégies avec pondération dynamique
  - Rééquilibrage automatique des poids basé sur les performances historiques
  - Calcul de confiance et de force des signaux pour une prise de décision optimale
  - Architecture thread-safe avec verrous pour les opérations concurrentes
- Calcul dynamique des ratios de couverture et des Z-scores
- Gestion automatique des positions et rééquilibrage périodique
- Suivi des performances avec métriques clés (P&L, ratio de Sharpe, drawdown)

### Module de Surveillance
- Tableau de bord interactif en temps réel avec Dash/Plotly
- Système d'alertes configurable (email, Telegram, webhook)
- Métriques de performance complètes
- Architecture thread-safe pour les opérations concurrentes

## Installation

### Prérequis
- Python 3.8+
- Pip (gestionnaire de paquets Python)
- Accès API aux exchanges souhaités

### Installation Standard
1. Cloner le dépôt:
```bash
git clone https://github.com/votre-username/ULTRA-ROBOT-MARKET-MAKER-IA.git
cd ULTRA-ROBOT-MARKET-MAKER-IA
```

2. Installer les dépendances:
```bash
pip install -r requirements.txt
```

3. Configurer les variables d'environnement:
```bash
cp .env.example .env
# Éditer .env avec vos clés API
```

4. Personnaliser la configuration:
```bash
cp config/default.yaml config/custom.yaml
# Éditer custom.yaml selon vos besoins
```

### Installation avec Docker
1. Construire l'image Docker:
```bash
docker build -t ultra-robot-market-maker .
```

2. Exécuter le conteneur:
```bash
docker run -d --name market-maker \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/data:/app/data \
  -p 8050:8050 \
  --env-file .env \
  ultra-robot-market-maker
```

## Utilisation

### Démarrage du Bot
```bash
python -m src.main --config config/custom.yaml
```

### Accès au Tableau de Bord
Ouvrez votre navigateur et accédez à:
```
http://localhost:8050
```

### Exécution des Tests
```bash
# Exécuter tous les tests (unitaires et d'intégration)
python run_tests.py --all

# Exécuter uniquement les tests unitaires
python run_tests.py --unit

# Exécuter uniquement les tests d'intégration
python run_tests.py --integration

# Exécuter un test spécifique
python run_tests.py --test test_market_data_manager
```

## Configuration
Le fichier de configuration YAML permet de personnaliser tous les aspects du bot:

- Exchanges et paires de trading
- Paramètres des stratégies
- Gestion des risques
- Options de surveillance
- Journalisation

Consultez `config/default.yaml` pour un exemple complet avec commentaires.

## Sécurité

- Les clés API sont stockées dans des variables d'environnement, jamais en dur dans le code
- Implémentation de limites de position et de perte maximale
- Protection contre les erreurs d'exécution et les conditions de marché anormales

## Licence
Ce projet est sous licence MIT. Voir le fichier LICENSE pour plus de détails.

## Avertissement
Le trading automatisé comporte des risques financiers significatifs. Ce logiciel est fourni à des fins éducatives et expérimentales uniquement. Utilisez-le à vos propres risques.
