import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import plotly.express as px
from io import BytesIO

class PointageSystem:
    def __init__(self):
        self.data_dir = Path("data")
        self.data_dir.mkdir(exist_ok=True)
        self.employees_file = self.data_dir / "employees.json"
        self.scans_file = self.data_dir / "scans.csv"
        self.load_data()

    def load_data(self):
        # Chargement des employés
        if self.employees_file.exists():
            with open(self.employees_file, 'r') as f:
                self.employees = json.load(f)
        else:
            self.employees = {}
            self.save_employees()

        # Chargement des pointages
        if self.scans_file.exists():
            self.scans_df = pd.read_csv(self.scans_file)
            # Conversion des colonnes de date et heure
            self.scans_df['DateTime'] = pd.to_datetime(
                self.scans_df['Date'] + ' ' + self.scans_df['Heure']
            )
        else:
            self.scans_df = pd.DataFrame(columns=[
                'ID_Employé', 'Nom', 'Prénom', 'Code_Barres', 
                'Date', 'Heure', 'Type_Scan', 'DateTime'
            ])
            self.save_scans()

    def save_employees(self):
        with open(self.employees_file, 'w') as f:
            json.dump(self.employees, f, indent=4)

    def save_scans(self):
        save_df = self.scans_df.copy()
        if 'DateTime' in save_df.columns:
            save_df = save_df.drop('DateTime', axis=1)
        save_df.to_csv(self.scans_file, index=False)

    def add_employee(self, id_emp, nom, prenom, code_barre):
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
        if code_barre in self.employees:
            emp = self.employees[code_barre]
            current_time = datetime.now()
            date = current_time.strftime('%Y-%m-%d')
            heure = current_time.strftime('%H:%M:%S')
            
            aujourd_hui = self.scans_df[
                (self.scans_df['Code_Barres'] == code_barre) & 
                (self.scans_df['Date'] == date)
            ]
            
            type_scan = 'Entrée' if len(aujourd_hui) % 2 == 0 else 'Sortie'
            
            nouveau_scan = pd.DataFrame([{
                'ID_Employé': emp['id'],
                'Nom': emp['nom'],
                'Prénom': emp['prenom'],
                'Code_Barres': code_barre,
                'Date': date,
                'Heure': heure,
                'Type_Scan': type_scan
            }])
            
            self.scans_df = pd.concat([self.scans_df, nouveau_scan], ignore_index=True)
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
                # Récupérer tous les scans de la journée
                day_scans = st.session_state.system.scans_df[
                    (st.session_state.system.scans_df['ID_Employé'] == emp['id']) & 
                    (st.session_state.system.scans_df['Date'] == date_str)
                ].sort_values('DateTime')
                
                if not day_scans.empty:
                    # Calculer les heures travaillées
                    total_hours = st.session_state.system.calculate_daily_hours(emp['id'], date_str)
                    
                    # Calculer le temps de pause
                    pause_time = 0
                    entry_time = None
                    for _, scan in day_scans.iterrows():
                        if scan['Type_Scan'] == 'Sortie':
                            entry_time = pd.to_datetime(scan['Date'] + ' ' + scan['Heure'])
                        elif scan['Type_Scan'] == 'Entrée' and entry_time is not None:
                            exit_time = pd.to_datetime(scan['Date'] + ' ' + scan['Heure'])
                            pause_time += (exit_time - entry_time).total_seconds() / 3600
                    
                    # Première et dernière entrée
                    first_scan = day_scans.iloc[0]
                    last_scan = day_scans.iloc[-1]
                    
                    daily_data.append({
                        'Employé': f"{emp['prenom']} {emp['nom']}",
                        'Heure Arrivée': first_scan['Heure'],
                        'Heure Départ': last_scan['Heure'],
                        'Heures Travaillées': round(total_hours, 2),
                        'Temps de Pause': round(pause_time, 2),
                        'Heures Effectives': round(total_hours - pause_time, 2)
                    })
            
            if daily_data:
                df_daily = pd.DataFrame(daily_data)
                
                # Affichage des statistiques
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Heures Travaillées", 
                             f"{df_daily['Heures Travaillées'].sum():.2f}h")
                with col2:
                    st.metric("Moyenne Heures/Employé", 
                             f"{df_daily['Heures Travaillées'].mean():.2f}h")
                with col3:
                    st.metric("Employés Présents", 
                             len(df_daily))
                
                # Graphique des heures par employé
                fig = px.bar(
                    df_daily,
                    x='Employé',
                    y=['Heures Effectives', 'Temps de Pause'],
                    title=f"Répartition du temps de travail - {date_str}",
                    barmode='stack'
                )
                st.plotly_chart(fig)
                
                # Tableau détaillé
                st.dataframe(df_daily)
                
                # Export Excel
                if st.download_button(
                    label="📥 Télécharger le rapport",
                    data=df_daily.to_excel(index=False, engine='openpyxl'),
                    file_name=f'rapport_journalier_{date_str}.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                ):
                    st.success("Rapport exporté avec succès!")
            else:
                st.info("Aucune donnée pour cette date")
    
    with tabs[1]:  # Rapport Hebdomadaire
        st.subheader("Rapport Hebdomadaire")
        
        # Sélection de la semaine
        selected_week = st.date_input(
            "Sélectionnez une date dans la semaine désirée",
            value=datetime.now()
        )
        
        if st.button("Générer rapport hebdomadaire"):
            # Calculer début et fin de semaine
            start_of_week = selected_week - timedelta(days=selected_week.weekday())
            end_of_week = start_of_week + timedelta(days=6)
            
            weekly_data = []
            
            for code_barre, emp in st.session_state.system.employees.items():
                daily_hours = []
                total_hours = 0
                total_pause = 0
                
                # Calculer les heures pour chaque jour
                current_date = start_of_week
                while current_date <= end_of_week:
                    date_str = current_date.strftime('%Y-%m-%d')
                    hours = st.session_state.system.calculate_daily_hours(emp['id'], date_str)
                    daily_hours.append(hours)
                    total_hours += hours
                    current_date += timedelta(days=1)
                
                if sum(daily_hours) > 0:
                    weekly_data.append({
                        'Employé': f"{emp['prenom']} {emp['nom']}",
                        'Lundi': round(daily_hours[0], 2),
                        'Mardi': round(daily_hours[1], 2),
                        'Mercredi': round(daily_hours[2], 2),
                        'Jeudi': round(daily_hours[3], 2),
                        'Vendredi': round(daily_hours[4], 2),
                        'Samedi': round(daily_hours[5], 2),
                        'Dimanche': round(daily_hours[6], 2),
                        'Total Heures': round(total_hours, 2)
                    })
            
            if weekly_data:
                df_weekly = pd.DataFrame(weekly_data)
                
                # Graphique hebdomadaire
                df_plot = df_weekly.melt(
                    id_vars=['Employé'],
                    value_vars=['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche'],
                    var_name='Jour',
                    value_name='Heures'
                )
                
                fig = px.bar(
                    df_plot,
                    x='Jour',
                    y='Heures',
                    color='Employé',
                    title=f"Heures travaillées par jour - Semaine du {start_of_week.strftime('%d/%m/%Y')}"
                )
                st.plotly_chart(fig)
                
                # Tableau récapitulatif
                st.dataframe(df_weekly)
                
                # Alertes temps de travail
                for _, row in df_weekly.iterrows():
                    if row['Total Heures'] > 48:  # Seuil légal en France
                        st.warning(f"⚠️ {row['Employé']} a dépassé les 48h hebdomadaires: {row['Total Heures']}h")
                
                # Export Excel
                if st.download_button(
                    label="📥 Télécharger le rapport hebdomadaire",
                    data=df_weekly.to_excel(index=False, engine='openpyxl'),
                    file_name=f'rapport_hebdo_{start_of_week.strftime("%Y-%m-%d")}.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                ):
                    st.success("Rapport exporté avec succès!")
            else:
                st.info("Aucune donnée pour cette semaine")
    
    with tabs[2]:  # Rapport Mensuel
        st.subheader("Rapport Mensuel")
        
        col1, col2 = st.columns(2)
        with col1:
            selected_year = st.selectbox(
                "Année",
                options=list(range(datetime.now().year - 5, datetime.now().year + 1)),
                index=5
            )
        with col2:
            selected_month = st.selectbox(
                "Mois",
                options=list(range(1, 13)),
                format_func=lambda x: datetime(2000, x, 1).strftime('%B'),
                index=datetime.now().month - 1
            )
        
        if st.button("Générer rapport mensuel"):
            monthly_data = []
            
            # Premier et dernier jour du mois
            first_day = datetime(selected_year, selected_month, 1)
            if selected_month == 12:
                last_day = datetime(selected_year + 1, 1, 1) - timedelta(days=1)
            else:
                last_day = datetime(selected_year, selected_month + 1, 1) - timedelta(days=1)
            
            for code_barre, emp in st.session_state.system.employees.items():
                total_hours = 0
                worked_days = 0
                current_date = first_day
                
                while current_date <= last_day:
                    date_str = current_date.strftime('%Y-%m-%d')
                    hours = st.session_state.system.calculate_daily_hours(emp['id'], date_str)
                    if hours > 0:
                        total_hours += hours
                        worked_days += 1
                    current_date += timedelta(days=1)
                
                if total_hours > 0:
                    monthly_data.append({
                        'Employé': f"{emp['prenom']} {emp['nom']}",
                        'Jours Travaillés': worked_days,
                        'Total Heures': round(total_hours, 2),
                        'Moyenne Heures/Jour': round(total_hours / worked_days if worked_days > 0 else 0, 2)
                    })
            
            if monthly_data:
                df_monthly = pd.DataFrame(monthly_data)
                
                # Statistiques mensuelles
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Heures Travaillées",
                             f"{df_monthly['Total Heures'].sum():.2f}h")
                with col2:
                    st.metric("Moyenne Heures/Employé",
                             f"{df_monthly['Total Heures'].mean():.2f}h")
                with col3:
                    st.metric("Jours Travaillés Moyen",
                             f"{df_monthly['Jours Travaillés'].mean():.1f}")
                
                # Graphiques
                fig1 = px.bar(
                    df_monthly,
                    x='Employé',
                    y='Total Heures',
                    title=f"Heures totales par employé - {datetime(selected_year, selected_month, 1).strftime('%B %Y')}"
                )
                st.plotly_chart(fig1)
                
                fig2 = px.scatter(
                    df_monthly,
                    x='Jours Travaillés',
                    y='Total Heures',
                    text='Employé',
                    title="Corrélation Jours travaillés / Heures totales"
                )
                st.plotly_chart(fig2)
                
                # Tableau détaillé
                st.dataframe(df_monthly)
                
                # Export Excel
                if st.download_button(
                    label="📥 Télécharger le rapport mensuel",
                    data=df_monthly.to_excel(index=False, engine='openpyxl'),
                    file_name=f'rapport_mensuel_{selected_year}_{selected_month}.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                ):
                    st.success("Rapport exporté avec succès!")
            else:
                st.info("Aucune donnée pour ce mois")
    
    with tabs[3]:  # Rapport Personnalisé
        st.subheader("Rapport Personnalisé")
        
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Date de début", value=datetime.now() - timedelta(days=30))
        with col2:
            end_date = st.date_input("Date de fin", value=datetime.now())
            
        # Sélection des métriques
        st.write("Sélectionnez les métriques à inclure :")
        col1, col2, col3 = st.columns(3)
        with col1:
            show_hours = st.checkbox("Heures travaillées", value=True)
            show_breaks = st.checkbox("Temps de pause", value=True)
        with col2:
            show_daily_avg = st.checkbox("Moyenne quotidienne", value=True)
            show_overtime = st.checkbox("Heures supplémentaires", value=True)
        with col3:
            show_presence = st.checkbox("Taux de présence", value=True)
            show_late = st.checkbox("Retards", value=True)
        
        if st.button("Générer rapport personnalisé"):
            custom_data = []
            total_days = (end_date - start_date).days + 1
            
            for code_barre, emp in st.session_state.system.employees.items():
                emp_data = {
                    'Employé': f"{emp['prenom']} {emp['nom']}",
                    'Jours Période': total_days
                }
                
                total_hours = 0
                total_breaks = 0
                worked_days = 0
                late_days = 0
                current_date = start_date
                
                while current_date <= end_date:
                    date_str = current_date.strftime('%Y-%m-%d')
                    hours = st.session_state.system.calculate_daily_hours(emp['id'], date_str)
                    
                    if hours > 0:
                        total_hours += hours
                        worked_days += 1
                        
                        # Vérifier les retards (exemple: arrivée après 9h)
                        day_scans = st.session_state.system.scans_df[
                            (
                        (st.session_state.system.scans_df['ID_Employé'] == emp['id']) &
                            (st.session_state.system.scans_df['Date'] == date_str) &
                            (st.session_state.system.scans_df['Type_Scan'] == 'Entrée')
                        ]
                        if not day_scans.empty:
                            first_entry = pd.to_datetime(day_scans.iloc[0]['Heure'])
                            if first_entry.hour >= 9 and first_entry.minute > 0:
                                late_days += 1
                        
                        # Calculer les pauses
                        day_scans = st.session_state.system.scans_df[
                            (st.session_state.system.scans_df['ID_Employé'] == emp['id']) &
                            (st.session_state.system.scans_df['Date'] == date_str)
                        ].sort_values('DateTime')
                        
                        entry_time = None
                        for _, scan in day_scans.iterrows():
                            if scan['Type_Scan'] == 'Sortie':
                                entry_time = pd.to_datetime(scan['Date'] + ' ' + scan['Heure'])
                            elif scan['Type_Scan'] == 'Entrée' and entry_time is not None:
                                exit_time = pd.to_datetime(scan['Date'] + ' ' + scan['Heure'])
                                total_breaks += (exit_time - entry_time).total_seconds() / 3600
                    
                    current_date += timedelta(days=1)
                
                # Calculer toutes les métriques
                if worked_days > 0:
                    if show_hours:
                        emp_data['Total Heures'] = round(total_hours, 2)
                    if show_breaks:
                        emp_data['Total Pauses'] = round(total_breaks, 2)
                    if show_daily_avg:
                        emp_data['Moyenne Heures/Jour'] = round(total_hours / worked_days, 2)
                    if show_overtime:
                        # Considérer les heures sup au-delà de 7h par jour
                        emp_data['Heures Supplémentaires'] = round(max(0, total_hours - (worked_days * 7)), 2)
                    if show_presence:
                        emp_data['Taux Présence'] = f"{(worked_days / total_days * 100):.1f}%"
                    if show_late:
                        emp_data['Nombre Retards'] = late_days
                    
                    custom_data.append(emp_data)
            
            if custom_data:
                df_custom = pd.DataFrame(custom_data)
                
                # Graphiques personnalisés
                for metric in df_custom.columns[2:]:  # Ignorer 'Employé' et 'Jours Période'
                    if metric != 'Taux Présence':  # Ne pas faire de graphique pour les pourcentages
                        fig = px.bar(
                            df_custom,
                            x='Employé',
                            y=metric,
                            title=f"{metric} par employé"
                        )
                        st.plotly_chart(fig)
                
                # Tableau récapitulatif
                st.dataframe(df_custom)
                
                # Alertes et analyses
                st.subheader("Analyses et Alertes")
                
                # Alertes sur les heures supplémentaires
                if show_overtime and 'Heures Supplémentaires' in df_custom.columns:
                    for _, row in df_custom.iterrows():
                        if row['Heures Supplémentaires'] > 10:
                            st.warning(f"⚠️ {row['Employé']} a accumulé {row['Heures Supplémentaires']}h supplémentaires")
                
                # Alertes sur les retards
                if show_late and 'Nombre Retards' in df_custom.columns:
                    for _, row in df_custom.iterrows():
                        if row['Nombre Retards'] > 3:
                            st.warning(f"⚠️ {row['Employé']} a {row['Nombre Retards']} retards sur la période")
                
                # Analyses statistiques
                st.subheader("Statistiques globales")
                metrics_cols = st.columns(3)
                col_idx = 0
                
                if show_hours:
                    with metrics_cols[col_idx % 3]:
                        st.metric(
                            "Moyenne d'heures totales",
                            f"{df_custom['Total Heures'].mean():.1f}h"
                        )
                        col_idx += 1
                
                if show_daily_avg:
                    with metrics_cols[col_idx % 3]:
                        st.metric(
                            "Moyenne quotidienne globale",
                            f"{df_custom['Moyenne Heures/Jour'].mean():.1f}h/jour"
                        )
                        col_idx += 1
                
                if show_presence:
                    with metrics_cols[col_idx % 3]:
                        avg_presence = df_custom['Taux Présence'].str.rstrip('%').astype(float).mean()
                        st.metric(
                            "Taux de présence moyen",
                            f"{avg_presence:.1f}%"
                        )
                        col_idx += 1
                
                # Export Excel
                if st.download_button(
                    label="📥 Télécharger le rapport personnalisé",
                    data=df_custom.to_excel(index=False, engine='openpyxl'),
                    file_name=f'rapport_personnalise_{start_date.strftime("%Y%m%d")}_{end_date.strftime("%Y%m%d")}.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                ):
                    st.success("Rapport exporté avec succès!")
            else:
                st.info("Aucune donnée pour la période sélectionnée")
                def setup_page_config():
    """Configuration initiale de la page Streamlit"""
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
                # Exemple simplifié - À remplacer par une vraie authentification
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
        
        # Logo ou image d'entreprise
        st.image("https://via.placeholder.com/150", caption="Logo Entreprise")
        
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

def main():
    """Fonction principale de l'application"""
    # Configuration initiale
    setup_page_config()
    
    # Vérification de l'authentification
    if not handle_authentication():
        return
    
    # Initialisation du système
    if 'system' not in st.session_state:
        st.session_state.system = PointageSystem()
    
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
