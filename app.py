# app.py
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import plotly.express as px
from io import BytesIO
import openpyxl
import shutil

class PointageSystem:
    def __init__(self):
        self.data_dir = Path("data")
        self.data_dir.mkdir(exist_ok=True)
        self.employees_file = self.data_dir / "employees.json"
        self.scans_file = self.data_dir / "scans.csv"
        self.archive_dir = self.data_dir / "archives"
        self.archive_dir.mkdir(exist_ok=True)
        self.load_data()
        self.cleanup_old_data()

    def cleanup_old_data(self):
        if not self.scans_df.empty:
            current_date = datetime.now()
            one_year_ago = current_date - timedelta(days=365)
            
            self.scans_df['DateTime'] = pd.to_datetime(self.scans_df['Date'] + ' ' + self.scans_df['Heure'])
            old_data = self.scans_df[self.scans_df['DateTime'] < one_year_ago]
            current_data = self.scans_df[self.scans_df['DateTime'] >= one_year_ago]
            
            if not old_data.empty:
                archive_filename = f"archive_{one_year_ago.strftime('%Y%m%d')}.xlsx"
                archive_path = self.archive_dir / archive_filename
                
                with pd.ExcelWriter(archive_path, engine='openpyxl') as writer:
                    old_data.to_excel(writer, index=False, sheet_name='Pointages')
                    pd.DataFrame(self.employees).to_excel(writer, index=False, sheet_name='Employés')
                
                self.scans_df = current_data
                self.save_scans()

    def load_data(self):
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

        if self.scans_file.exists():
            try:
                self.scans_df = pd.read_csv(self.scans_file)
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
        try:
            with open(self.employees_file, 'w', encoding='utf-8') as f:
                json.dump(self.employees, f, indent=4, ensure_ascii=False)
        except Exception as e:
            st.error(f"Erreur lors de la sauvegarde des employés: {str(e)}")

    def save_scans(self):
        try:
            save_df = self.scans_df.copy()
            if 'DateTime' in save_df.columns:
                save_df = save_df.drop('DateTime', axis=1)
            save_df.to_csv(self.scans_file, index=False, encoding='utf-8')
        except Exception as e:
            st.error(f"Erreur lors de la sauvegarde des pointages: {str(e)}")

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
            if not emp['actif']:
                return False, "Employé inactif"
                
            current_time = datetime.now()
            date_str = current_time.strftime('%Y-%m-%d')
            heure_str = current_time.strftime('%H:%M:%S')
            
            aujourd_hui = self.scans_df[
                (self.scans_df['Code_Barres'].astype(str) == str(code_barre)) & 
                (self.scans_df['Date'].astype(str) == date_str)
            ]
            
            type_scan = 'Entrée' if len(aujourd_hui) % 2 == 0 else 'Sortie'
            
            nouveau_scan = pd.DataFrame([{
                'ID_Employé': emp['id'],
                'Nom': emp['nom'],
                'Prénom': emp['prenom'],
                'Code_Barres': code_barre,
                'Date': date_str,
                'Heure': heure_str,
                'Type_Scan': type_scan
            }])
            
            nouveau_scan['DateTime'] = pd.to_datetime(
                nouveau_scan['Date'] + ' ' + nouveau_scan['Heure']
            )
            
            self.scans_df = pd.concat([self.scans_df, nouveau_scan], ignore_index=True)
            self.save_scans()
            
            return True, f"{type_scan} enregistrée pour {emp['prenom']} {emp['nom']}"
        return False, "Code-barres non reconnu"

    def calculate_daily_hours(self, employee_id, date):
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

    def export_data(self, start_date=None, end_date=None):
        if start_date is None:
            start_date = datetime.now() - timedelta(days=365)
        if end_date is None:
            end_date = datetime.now()

        filtered_data = self.scans_df[
            (self.scans_df['DateTime'] >= pd.Timestamp(start_date)) &
            (self.scans_df['DateTime'] <= pd.Timestamp(end_date))
        ]

        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            filtered_data.to_excel(writer, sheet_name='Pointages', index=False)
            pd.DataFrame(list(self.employees.values())).to_excel(
                writer, sheet_name='Employés', index=False
            )

        return output.getvalue()

def show_pointage_page():
    st.title("Pointage")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Scanner votre badge")
        
        # Gestion de la clé unique pour le champ de saisie
        if 'scan_count' not in st.session_state:
            st.session_state.scan_count = 0
            
        # Utilisation d'une clé dynamique pour forcer la réinitialisation
        scan_input = st.text_input(
            "", 
            key=f"scan_input_{st.session_state.scan_count}",
            help="Scannez votre badge"
        )

        if scan_input:
            success, message = st.session_state.system.record_scan(scan_input)
            if success:
                st.success(message)
                # Incrémenter le compteur pour forcer une nouvelle clé
                st.session_state.scan_count += 1
                st.rerun()
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

    tab1, tab2, tab3 = st.tabs(["Gestion des Employés", "Liste des Employés", "Export des Données"])

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

    with tab3:
        st.subheader("Export des données")
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Date de début", value=datetime.now() - timedelta(days=30))
        with col2:
            end_date = st.date_input("Date de fin", value=datetime.now())

        if st.button("Exporter les données"):
            data = st.session_state.system.export_data(start_date, end_date)
            st.download_button(
                label="📥 Télécharger les données",
                data=data,
                file_name=f'pointages_{start_date.strftime("%Y%m%d")}_{end_date.strftime("%Y%m%d")}.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )

def show_reports_page():
    st.title("Rapports et Analyses")

    tabs = st.tabs(["Journalier", "Hebdomadaire", "Mensuel"])

    with tabs[0]:
        st.subheader("Rapport Journalier")
        selected_date = st.date_input("Sélectionnez une date", value=datetime.now())
        
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
                st.write("Heures travaillées:")
                st.dataframe(df_daily)

                fig = px.bar(df_daily, x='Employé', y='Heures',
                           title=f"Heures travaillées le {date_str}")
                st.plotly_chart(fig)

                if st.download_button(
                    label="📥 Télécharger le rapport",
                    data=df_daily.to_excel(index=False, engine='openpyxl'),
                    file_name=f'rapport_journalier_{date_str}.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                ):
                    st.success("Rapport exporté avec succès!")
            else:
                st.info("Aucune donnée pour cette date")

def setup_page_config():
    st.set_page_config(
        page_title="Système de Pointage",
        page_icon="⏰",
        layout="wide",
        initial_sidebar_state="expanded"
    )

def handle_authentication():
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
    with st.sidebar:
        st.title("Navigation")
        pages = ["Pointage"]
        if st.session_state.admin:
            pages.extend(["Administration", "Rapports"])
        
        page = st.radio("", pages)
        
        st.divider()
        st.caption(f"Date: {datetime.now().strftime('%d/%m/%Y')}")
        st.caption(f"Heure: {datetime.now().strftime('%H:%M:%S')}")
        
        if st.button("Déconnexion"):
            st.session_state.authenticated = False
            st.session_state.admin = False
            st.rerun()
        
        return page

def main():
    setup_page_config()

    if not handle_authentication():
        return

    if 'system' not in st.session_state:
        st.session_state.system = PointageSystem()

    page = show_sidebar()

    try:
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
