import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import plotly.express as px
from io import BytesIO

# Configuration de la page - DOIT ÊTRE EN PREMIER
st.set_page_config(
    page_title="Système de Pointage",
    page_icon="⏰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Style CSS personnalisé
st.markdown("""
    <style>
    .main {
        padding-top: 2rem;
    }
    .stAlert {
        margin-top: 1rem;
        margin-bottom: 1rem;
    }
    .stMetric {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
    }
    </style>
""", unsafe_allow_html=True)

class PointageSystem:
    def __init__(self):
        # Création des dossiers et fichiers nécessaires
        self.data_dir = Path("data")
        self.data_dir.mkdir(exist_ok=True)
        self.employees_file = self.data_dir / "employees.json"
        self.scans_file = self.data_dir / "scans.csv"
        self.load_data()

    def load_data(self):
        """Chargement des données depuis les fichiers"""
        # Chargement des employés depuis le JSON
        if self.employees_file.exists():
            try:
                with open(self.employees_file, 'r', encoding='utf-8') as f:
                    self.employees = json.load(f)
            except Exception as e:
                st.error(f"Erreur lors du chargement des employés: {str(e)}")
                self.employees = {}
        else:
            self.employees = {}
            self.save_employees()

        # Chargement des pointages depuis le CSV
        if self.scans_file.exists():
            try:
                self.scans_df = pd.read_csv(self.scans_file)
                # Conversion explicite des colonnes de date et heure
                if not self.scans_df.empty:
                    self.scans_df['DateTime'] = pd.to_datetime(
                        self.scans_df['Date'] + ' ' + self.scans_df['Heure']
                    )
            except Exception as e:
                st.error(f"Erreur lors du chargement des pointages: {str(e)}")
                self.scans_df = pd.DataFrame(columns=[
                    'ID_Employé', 'Nom', 'Prénom', 'Code_Barres', 
                    'Date', 'Heure', 'Type_Scan', 'DateTime'
                ])
        else:
            self.scans_df = pd.DataFrame(columns=[
                'ID_Employé', 'Nom', 'Prénom', 'Code_Barres', 
                'Date', 'Heure', 'Type_Scan', 'DateTime'
            ])
            self.save_scans()

    def save_employees(self):
        """Sauvegarde des employés dans le fichier JSON"""
        try:
            with open(self.employees_file, 'w', encoding='utf-8') as f:
                json.dump(self.employees, f, indent=4, ensure_ascii=False)
        except Exception as e:
            st.error(f"Erreur lors de la sauvegarde des employés: {str(e)}")

    def save_scans(self):
        """Sauvegarde des pointages dans le fichier CSV"""
        try:
            save_df = self.scans_df.copy()
            if 'DateTime' in save_df.columns:
                save_df = save_df.drop('DateTime', axis=1)
            save_df.to_csv(self.scans_file, index=False, encoding='utf-8')
        except Exception as e:
            st.error(f"Erreur lors de la sauvegarde des pointages: {str(e)}")

    def add_employee(self, id_emp, nom, prenom, code_barre):
        """Ajout d'un nouvel employé"""
        if code_barre not in self.employees:
            self.employees[code_barre] = {
                'id': id_emp,
                'nom': nom,
                'prenom': prenom,
                'code_barre': code_barre,
                'actif': True
            }
            self.save_employees()
            return True
        return False

    def record_scan(self, code_barre):
        """Enregistrement d'un pointage"""
        if code_barre in self.employees:
            emp = self.employees[code_barre]
            if not emp['actif']:
                return False, "Employé inactif"
                
            current_time = datetime.now()
            date_str = current_time.strftime('%Y-%m-%d')
            heure_str = current_time.strftime('%H:%M:%S')
            
            # Déterminer le type de scan
            aujourd_hui = self.scans_df[
                (self.scans_df['Code_Barres'] == code_barre) & 
                (self.scans_df['Date'] == date_str)
            ]
            
            type_scan = 'Entrée' if len(aujourd_hui) % 2 == 0 else 'Sortie'
            
            # Créer le nouveau scan
            nouveau_scan = pd.DataFrame([{
                'ID_Employé': emp['id'],
                'Nom': emp['nom'],
                'Prénom': emp['prenom'],
                'Code_Barres': code_barre,
                'Date': date_str,
                'Heure': heure_str,
                'Type_Scan': type_scan
            }])
            
            # Ajouter le DateTime pour les calculs
            nouveau_scan['DateTime'] = pd.to_datetime(
                nouveau_scan['Date'] + ' ' + nouveau_scan['Heure']
            )
            
            # Concaténer avec les données existantes
            self.scans_df = pd.concat([self.scans_df, nouveau_scan], ignore_index=True)
            
            # Sauvegarder immédiatement
            self.save_scans()
            
            return True, f"{type_scan} enregistrée pour {emp['prenom']} {emp['nom']}"
        return False, "Code-barres non reconnu"

    def calculate_daily_hours(self, employee_id, date):
        """Calcule les heures travaillées pour un employé sur une journée donnée"""
        day_scans = self.scans_df[
            (self.scans_df['ID_Employé'] == employee_id) & 
            (self.scans_df['Date'] == date)
        ].sort_values('DateTime')

        total_hours = timedelta()
        entry_time = None

        for _, scan in day_scans.iterrows():
            if scan['Type_Scan'] == 'Entrée':
                entry_time = pd.to_datetime(scan['Date'] + ' ' + scan['Heure'])
            elif scan['Type_Scan'] == 'Sortie' and entry_time is not None:
                exit_time = pd.to_datetime(scan['Date'] + ' ' + scan['Heure'])
                total_hours += exit_time - entry_time
                entry_time = None

        return total_hours.total_seconds() / 3600

    def backup_data(self):
        """Création d'une sauvegarde des données"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_dir = self.data_dir / 'backups'
            backup_dir.mkdir(exist_ok=True)
            
            # Sauvegarde des employés
            employee_backup = backup_dir / f'employees_{timestamp}.json'
            with open(employee_backup, 'w', encoding='utf-8') as f:
                json.dump(self.employees, f, indent=4, ensure_ascii=False)
            
            # Sauvegarde des pointages
            scans_backup = backup_dir / f'scans_{timestamp}.csv'
            save_df = self.scans_df.copy()
            if 'DateTime' in save_df.columns:
                save_df = save_df.drop('DateTime', axis=1)
            save_df.to_csv(scans_backup, index=False, encoding='utf-8')
            
            # Nettoyage des anciennes sauvegardes (garder les 5 dernières)
            backup_files = sorted(list(backup_dir.glob('*.json')) + list(backup_dir.glob('*.csv')))
            if len(backup_files) > 10:  # 5 sauvegardes * 2 fichiers
                for old_file in backup_files[:-10]:
                    old_file.unlink()
                    
            return True, "Sauvegarde créée avec succès"
        except Exception as e:
            return False, f"Erreur lors de la sauvegarde: {str(e)}"

def handle_authentication():
    """Gestion basique de l'authentification"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.admin = False

    if not st.session_state.authenticated:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.title("Connexion")
            username = st.text_input("Utilisateur")
            password = st.text_input("Mot de passe", type="password")
            
            if st.button("Se connecter"):
                if username == "admin" and password == "admin":
                    st.session_state.authenticated = True
                    st.session_state.admin = True
                    st.rerun()
                elif username == "user" and password == "user":
                    st.session_state.authenticated = True
                    st.session_state.admin = False
                    st.rerun()
                else:
                    st.error("Identifiants incorrects")
            return False
    return True

def show_sidebar():
    """Affichage et gestion de la barre latérale"""
    with st.sidebar:
        st.title("Navigation")
        
        # Menu de navigation
        pages = ["Pointage"]
        if st.session_state.admin:
            pages.extend(["Administration", "Rapports"])
        
        page = st.radio("", pages)
        
        # Informations supplémentaires
        st.divider()
        st.caption(f"Date: {datetime.now().strftime('%d/%m/%Y')}")
        st.caption(f"Heure: {datetime.now().strftime('%H:%M:%S')}")
        
        # Bouton de déconnexion
        if st.button("Déconnexion"):
            st.session_state.authenticated = False
            st.session_state.admin = False
            st.rerun()
        
        return page
        def show_pointage_page():
    st.title("Pointage")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Scanner votre badge")
        scan_input = st.text_input("", key="scan_input", help="Scannez votre badge")

        if scan_input:
            success, message = st.session_state.system.record_scan(scan_input)
            if success:
                st.success(message)
            else:
                st.error(message)

    with col2:
        st.subheader("Derniers pointages")
        if not st.session_state.system.scans_df.empty:
            recent_scans = st.session_state.system.scans_df.tail(5)
            for _, scan in recent_scans.iloc[::-1].iterrows():
                st.write(f"{scan['Prénom']} {scan['Nom']} - {scan['Type_Scan']} à {scan['Heure']}")

def show_admin_page():
    st.title("Administration")

    tab1, tab2 = st.tabs(["Gestion des Employés", "Liste des Employés"])

    with tab1:
        st.subheader("Ajouter un nouvel employé")
        col1, col2 = st.columns(2)

        with col1:
            id_emp = st.text_input("ID Employé")
            nom = st.text_input("Nom")

        with col2:
            prenom = st.text_input("Prénom")
            code_barre = st.text_input("Code Barres")

        if st.button("Ajouter l'employé"):
            if all([id_emp, nom, prenom, code_barre]):
                if st.session_state.system.add_employee(id_emp, nom, prenom, code_barre):
                    st.success("Employé ajouté avec succès!")
                else:
                    st.error("Ce code-barres existe déjà!")
            else:
                st.error("Veuillez remplir tous les champs")

    with tab2:
        st.subheader("Liste des employés")
        if st.session_state.system.employees:
            df_employees = pd.DataFrame(st.session_state.system.employees.values())
            st.dataframe(df_employees)

def export_dataframe_to_excel(df):
    """Fonction utilitaire pour exporter un DataFrame en Excel"""
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    return buffer.getvalue()

def show_reports_page():
    st.title("Rapports et Analyses")

    tabs = st.tabs(["Journalier", "Hebdomadaire", "Mensuel", "Personnalisé"])
    
    with tabs[0]:  # Rapport Journalier
        st.subheader("Rapport Journalier")
        selected_date = st.date_input(
            "Sélectionnez une date",
            value=datetime.now()
        )

        if st.button("Générer rapport journalier"):
            date_str = selected_date.strftime('%Y-%m-%d')
            daily_data = []

            for code_barre, emp in st.session_state.system.employees.items():
                hours = st.session_state.system.calculate_daily_hours(emp['id'], date_str)
                if hours > 0:
                    daily_data.append({
                        'Employé': f"{emp['prenom']} {emp['nom']}",
                        'Heures': round(hours, 2)
                    })

            if daily_data:
                df_daily = pd.DataFrame(daily_data)
                
                # Affichage graphique
                fig = px.bar(df_daily, x='Employé', y='Heures',
                           title=f"Heures travaillées le {date_str}")
                st.plotly_chart(fig)
                
                # Affichage tableau
                st.dataframe(df_daily)
                
                # Export Excel
                excel_data = export_dataframe_to_excel(df_daily)
                st.download_button(
                    label="📥 Télécharger le rapport",
                    data=excel_data,
                    file_name=f"rapport_journalier_{date_str}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.info("Aucune donnée pour cette date")
                with tabs[1]:  # Rapport Hebdomadaire
        st.subheader("Rapport Hebdomadaire")
        week_date = st.date_input("Sélectionnez une date dans la semaine", value=datetime.now(), key="week_select")
        
        if st.button("Générer rapport hebdomadaire"):
            start_week = week_date - timedelta(days=week_date.weekday())
            end_week = start_week + timedelta(days=6)
            
            weekly_data = []
            for code_barre, emp in st.session_state.system.employees.items():
                weekly_hours = 0
                daily_hours = []
                current_date = start_week
                
                while current_date <= end_week:
                    hours = st.session_state.system.calculate_daily_hours(
                        emp['id'], 
                        current_date.strftime('%Y-%m-%d')
                    )
                    daily_hours.append(round(hours, 2))
                    weekly_hours += hours
                    current_date += timedelta(days=1)
                
                if weekly_hours > 0:
                    weekly_data.append({
                        'Employé': f"{emp['prenom']} {emp['nom']}",
                        'Lundi': daily_hours[0],
                        'Mardi': daily_hours[1],
                        'Mercredi': daily_hours[2],
                        'Jeudi': daily_hours[3],
                        'Vendredi': daily_hours[4],
                        'Samedi': daily_hours[5],
                        'Dimanche': daily_hours[6],
                        'Total': round(weekly_hours, 2)
                    })
            
            if weekly_data:
                df_weekly = pd.DataFrame(weekly_data)
                
                # Graphique
                fig = px.bar(df_weekly, x='Employé', y='Total',
                           title=f"Total des heures semaine du {start_week.strftime('%d/%m/%Y')}")
                st.plotly_chart(fig)
                
                # Tableau
                st.dataframe(df_weekly)
                
                # Export Excel
                excel_data = export_dataframe_to_excel(df_weekly)
                st.download_button(
                    label="📥 Télécharger le rapport",
                    data=excel_data,
                    file_name=f"rapport_hebdomadaire_{start_week.strftime('%Y-%m-%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.info("Aucune donnée pour cette semaine")

    with tabs[2]:  # Rapport Mensuel
        st.subheader("Rapport Mensuel")
        col1, col2 = st.columns(2)
        with col1:
            selected_year = st.selectbox(
                "Année",
                options=list(range(datetime.now().year-2, datetime.now().year+1)),
                index=2
            )
        with col2:
            selected_month = st.selectbox(
                "Mois",
                options=list(range(1, 13)),
                format_func=lambda x: datetime(2000, x, 1).strftime('%B'),
                index=datetime.now().month-1
            )
        
        if st.button("Générer rapport mensuel"):
            monthly_data = []
            first_day = datetime(selected_year, selected_month, 1)
            if selected_month == 12:
                last_day = datetime(selected_year + 1, 1, 1) - timedelta(days=1)
            else:
                last_day = datetime(selected_year, selected_month + 1, 1) - timedelta(days=1)
            
            for code_barre, emp in st.session_state.system.employees.items():
                total_hours = 0
                days_worked = 0
                current_date = first_day
                
                while current_date <= last_day:
                    hours = st.session_state.system.calculate_daily_hours(
                        emp['id'],
                        current_date.strftime('%Y-%m-%d')
                    )
                    if hours > 0:
                        total_hours += hours
                        days_worked += 1
                    current_date += timedelta(days=1)
                
                if total_hours > 0:
                    monthly_data.append({
                        'Employé': f"{emp['prenom']} {emp['nom']}",
                        'Jours Travaillés': days_worked,
                        'Total Heures': round(total_hours, 2),
                        'Moyenne Heures/Jour': round(total_hours/days_worked, 2)
                    })
            
            if monthly_data:
                df_monthly = pd.DataFrame(monthly_data)
                
                # Statistiques
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Heures", f"{df_monthly['Total Heures'].sum():.2f}h")
                with col2:
                    st.metric("Moyenne Employés", f"{df_monthly['Total Heures'].mean():.2f}h")
                with col3:
                    st.metric("Jours Moyens", f"{df_monthly['Jours Travaillés'].mean():.1f}j")
                
                # Graphique
                fig = px.bar(df_monthly, x='Employé', y='Total Heures',
                           title=f"Heures travaillées - {datetime(selected_year, selected_month, 1).strftime('%B %Y')}")
                st.plotly_chart(fig)
                
                # Tableau
                st.dataframe(df_monthly)
                
                # Export Excel
                excel_data = export_dataframe_to_excel(df_monthly)
                st.download_button(
                    label="📥 Télécharger le rapport",
                    data=excel_data,
                    file_name=f"rapport_mensuel_{selected_year}_{selected_month:02d}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.info("Aucune donnée pour ce mois")

def main():
    # Vérification de l'authentification
    if not handle_authentication():
        return
    
    # Initialisation du système
    if 'system' not in st.session_state:
        st.session_state.system = PointageSystem()
    
    # Backup automatique quotidien
    if 'last_backup' not in st.session_state:
        st.session_state.last_backup = datetime.now().date()
    elif st.session_state.last_backup < datetime.now().date():
        success, message = st.session_state.system.backup_data()
        if not success and st.session_state.admin:
            st.warning(f"Erreur de sauvegarde automatique: {message}")
        st.session_state.last_backup = datetime.now().date()
    
    # Affichage du menu et récupération de la page sélectionnée
    page = show_sidebar()
    
    try:
        # Navigation entre les pages
        if page == "Pointage":
            show_pointage_page()
        elif page == "Administration" and st.session_state.admin:
            show_admin_page()
        elif page == "Rapports" and st.session_state.admin:
            show_reports_page()
    except Exception as e:
        st.error(f"Une erreur est survenue : {str(e)}")
        if st.session_state.admin:
            st.exception(e)

if __name__ == "__main__":
    main()
  
