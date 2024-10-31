# Système de Pointage Entreprise

Une application de gestion des pointages développée avec Streamlit. Cette application permet de gérer les entrées/sorties des employés, d'administrer les badges et de générer des rapports.

## Fonctionnalités

- 📱 Interface de pointage simple avec lecteur de codes-barres USB
- 👥 Gestion complète des employés
- 📊 Rapports et statistiques de présence
- 📤 Export des données au format Excel
- 📈 Visualisation des données de présence
- 🔒 Stockage local sécurisé des données

## Installation

1. Clonez le repository :
```bash
git clone https://github.com/votre-username/systeme-pointage.git
cd systeme-pointage
```

2. Créez un environnement virtuel et installez les dépendances :
```bash
python -m venv venv
source venv/bin/activate  # Pour Linux/Mac
# OU
venv\Scripts\activate  # Pour Windows
pip install -r requirements.txt
```

3. Lancez l'application :
```bash
streamlit run app.py
```

## Structure du projet
```
systeme-pointage/
│
├── app.py                 # Application principale
├── requirements.txt       # Dépendances Python
├── README.md             # Documentation
├── .gitignore            # Fichiers à ignorer par Git
├── LICENSE               # Licence du projet
├── scripts/              # Scripts utilitaires
│   ├── install.bat       # Script d'installation Windows
│   └── install.sh        # Script d'installation Linux/Mac
│
└── data/                 # Dossier des données (ignoré par git)
    ├── employees.json    # Base de données des employés
    └── scans.csv         # Historique des pointages
```

## Configuration requise

- Python 3.8+
- Lecteur de codes-barres USB (en mode clavier)
- Windows, Linux ou MacOS

## Dépendances principales

- streamlit
- pandas
- plotly
- xlsxwriter
- python-dotenv

## Utilisation

1. Lancez l'application via le script d'installation ou directement avec Streamlit
2. Accédez à l'interface via votre navigateur (généralement http://localhost:8501)
3. Utilisez la barre latérale pour naviguer entre les différentes sections :
   - Pointage : Scanner les badges
   - Administration : Gérer les employés
   - Rapports : Visualiser et exporter les données

## Contribution

Les contributions sont bienvenues ! N'hésitez pas à :
- Ouvrir une issue pour signaler un bug
- Proposer de nouvelles fonctionnalités
- Soumettre une pull request

## Licence

MIT License - voir le fichier LICENSE pour plus de détails.
