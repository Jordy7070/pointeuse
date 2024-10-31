#!/bin/bash

echo "Installation du Système de Pointage"
echo "================================="

# Vérifier si Python est installé
if ! command -v python3 &> /dev/null; then
    echo "Python n'est pas installé. Veuillez l'installer via votre gestionnaire de paquets."
    exit 1
fi

# Vérifier si pip est installé
if ! command -v pip3 &> /dev/null; then
    echo "pip n'est pas installé. Installation..."
    python3 -m ensurepip --default-pip
fi

# Créer l'environnement virtuel
if [ ! -d "venv" ]; then
    echo "Création de l'environnement virtuel..."
    python3 -m venv venv
fi

# Activer l'environnement virtuel et installer les dépendances
source venv/bin/activate
echo "Installation des dépendances..."
pip install -r requirements.txt

# Créer les dossiers nécessaires
mkdir -p data

# Créer le script de lancement
echo '#!/bin/bash' > launch.sh
echo 'source venv/bin/activate' >> launch.sh
echo 'streamlit run app.py' >> launch.sh
chmod +x launch.sh

echo "Installation terminée !"
echo "Pour lancer l'application, exécutez : ./launch.sh"
