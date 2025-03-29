#!/bin/bash

# Script de démarrage pour ULTRA-ROBOT MARKET MAKER IA
# Ce script facilite le lancement du bot dans différents modes d'exécution

# Fonction d'aide
show_help() {
    echo "Usage: ./start.sh [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --help                Affiche cette aide"
    echo "  --mode MODE           Mode d'exécution (live, simulation, backtest, paper)"
    echo "  --config FILE         Fichier de configuration à utiliser"
    echo "  --log-level LEVEL     Niveau de journalisation (DEBUG, INFO, WARNING, ERROR)"
    echo "  --symbols SYM1,SYM2   Symboles à trader (séparés par des virgules)"
    echo "  --strategies STR1,STR2 Stratégies à utiliser (séparées par des virgules)"
    echo "  --no-dashboard        Désactive le tableau de bord"
    echo "  --no-ai               Désactive l'optimisation par IA"
    echo "  --docker              Utilise Docker pour exécuter le bot"
    echo "  --docker-build        Reconstruit l'image Docker avant de lancer le bot"
    echo "  --docker-logs         Affiche les logs du conteneur Docker"
    echo "  --docker-stop         Arrête les conteneurs Docker"
    echo ""
    echo "Exemples:"
    echo "  ./start.sh --mode simulation"
    echo "  ./start.sh --mode live --symbols BTC/USDT,ETH/USDT"
    echo "  ./start.sh --docker --mode backtest"
}

# Variables par défaut
MODE="simulation"
CONFIG="src/config/default.yaml"
LOG_LEVEL="INFO"
LOG_FILE="logs/ultra_robot.log"
DASHBOARD="--dashboard"
AI="--ai"
USE_DOCKER=false
BUILD_DOCKER=false
DOCKER_LOGS=false
DOCKER_STOP=false
SYMBOLS=""
STRATEGIES=""

# Analyser les arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --help)
            show_help
            exit 0
            ;;
        --mode)
            MODE="$2"
            shift 2
            ;;
        --config)
            CONFIG="$2"
            shift 2
            ;;
        --log-level)
            LOG_LEVEL="$2"
            shift 2
            ;;
        --symbols)
            SYMBOLS="$2"
            shift 2
            ;;
        --strategies)
            STRATEGIES="$2"
            shift 2
            ;;
        --no-dashboard)
            DASHBOARD=""
            shift
            ;;
        --no-ai)
            AI="--no-ai"
            shift
            ;;
        --docker)
            USE_DOCKER=true
            shift
            ;;
        --docker-build)
            BUILD_DOCKER=true
            USE_DOCKER=true
            shift
            ;;
        --docker-logs)
            DOCKER_LOGS=true
            shift
            ;;
        --docker-stop)
            DOCKER_STOP=true
            shift
            ;;
        *)
            echo "Option inconnue: $1"
            show_help
            exit 1
            ;;
    esac
done

# Créer les répertoires nécessaires
mkdir -p logs data models

# Préparer les arguments pour les symboles et stratégies
SYMBOLS_ARG=""
if [ ! -z "$SYMBOLS" ]; then
    # Convertir la liste séparée par des virgules en liste séparée par des espaces
    SYMBOLS_ARG="--symbols ${SYMBOLS//,/ }"
fi

STRATEGIES_ARG=""
if [ ! -z "$STRATEGIES" ]; then
    # Convertir la liste séparée par des virgules en liste séparée par des espaces
    STRATEGIES_ARG="--strategies ${STRATEGIES//,/ }"
fi

# Arrêter les conteneurs Docker si demandé
if $DOCKER_STOP; then
    echo "Arrêt des conteneurs Docker..."
    docker-compose down
    exit 0
fi

# Afficher les logs Docker si demandé
if $DOCKER_LOGS; then
    echo "Affichage des logs Docker..."
    docker-compose logs -f ultra-robot
    exit 0
fi

# Exécuter avec Docker
if $USE_DOCKER; then
    # Reconstruire l'image Docker si demandé
    if $BUILD_DOCKER; then
        echo "Construction de l'image Docker..."
        docker-compose build
    fi
    
    # Préparer la commande Docker
    DOCKER_CMD="python run_bot.py --config $CONFIG --mode $MODE --log-level $LOG_LEVEL --log-file $LOG_FILE $DASHBOARD $AI $SYMBOLS_ARG $STRATEGIES_ARG"
    
    # Mettre à jour la commande dans le fichier docker-compose.yml
    sed -i "s|command:.*|command: $DOCKER_CMD|" docker-compose.yml
    
    echo "Démarrage du bot avec Docker en mode $MODE..."
    docker-compose up -d
    
    echo "Bot démarré en arrière-plan. Pour voir les logs, utilisez:"
    echo "./start.sh --docker-logs"
    
# Exécuter directement
else
    # Vérifier si Python est installé
    if ! command -v python &> /dev/null; then
        echo "Python n'est pas installé. Veuillez installer Python 3.8+ pour exécuter le bot."
        exit 1
    fi
    
    # Vérifier si les dépendances sont installées
    if [ ! -f "requirements.txt" ]; then
        echo "Fichier requirements.txt non trouvé."
        exit 1
    fi
    
    # Installer les dépendances si nécessaire
    if [ ! -d "venv" ]; then
        echo "Création de l'environnement virtuel et installation des dépendances..."
        python -m venv venv
        source venv/bin/activate
        pip install -r requirements.txt
    else
        source venv/bin/activate
    fi
    
    echo "Démarrage du bot en mode $MODE..."
    python run_bot.py --config $CONFIG --mode $MODE --log-level $LOG_LEVEL --log-file $LOG_FILE $DASHBOARD $AI $SYMBOLS_ARG $STRATEGIES_ARG
fi
