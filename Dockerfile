FROM python:3.10-slim

# Définir les variables d'environnement
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TZ=UTC

# Définir le répertoire de travail
WORKDIR /app

# Installer les dépendances système
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copier les fichiers de dépendances
COPY requirements.txt .

# Installer les dépendances Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copier le code source
COPY . .

# Installer le package en mode développement
RUN pip install -e .

# Ajouter le répertoire parent au PYTHONPATH
ENV PYTHONPATH=/app/src

# Créer un utilisateur non-root
RUN useradd -m appuser
RUN chown -R appuser:appuser /app
USER appuser

# Créer les répertoires nécessaires
RUN mkdir -p logs data

# Exposer le port pour le tableau de bord
EXPOSE 8050

# Commande par défaut
CMD ["python", "/app/src/main.py", "--config", "/app/src/config/default.yaml"]
