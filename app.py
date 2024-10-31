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
    
    # Correction : Création d'une liste d'années
    current_year = datetime.now().year
    years = list(range(current_year - 5, current_year + 1))
    months = list(range(1, 13))
    
    col1, col2 = st.columns(2)
    
    with col1:
        selected_year = st.selectbox("Année", options=years, index=len(years)-1)
    
    with col2:
        selected_month = st.selectbox(
            "Mois",
            options=months,
            format_func=lambda x: datetime.strptime(str(x), "%m").strftime("%B"),
            index=datetime.now().month-1
        )
    
    if st.button("Générer rapport"):
        # Filtrer les données pour le mois sélectionné
        report_data = []
        
        for code_barre, emp in st.session_state.system.employees.items():
            monthly_hours = 0
            current_date = datetime(selected_year, selected_month, 1)
            
            while current_date.month == selected_month:
                date_str = current_date.strftime('%Y-%m-%d')
                hours = st.session_state.system.calculate_daily_hours(emp['id'], date_str)
                monthly_hours += hours
                current_date += timedelta(days=1)
            
            if monthly_hours > 0:
                report_data.append({
                    'Employé': f"{emp['prenom']} {emp['nom']}",
                    'Heures': round(monthly_hours, 2)
                })
        
        if report_data:
            df_report = pd.DataFrame(report_data)
            
            # Graphique
            fig = px.bar(
                df_report,
                x='Employé',
                y='Heures',
                title=f"Heures travaillées - {datetime(selected_year, selected_month, 1).strftime('%B %Y')}"
            )
            st.plotly_chart(fig)
            
            # Tableau
            st.dataframe(df_report)
            
            # Export Excel
            if st.button("Exporter en Excel"):
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_report.to_excel(writer, index=False)
                excel_data = output.getvalue()
                
                st.download_button(
                    label="Télécharger le rapport",
                    data=excel_data,
                    file_name=f'rapport_{selected_year}_{selected_month}.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
        else:
            st.info("Aucune donnée pour la période sélectionnée")

def main():
    st.set_page_config(page_title="Système de Pointage", layout="wide")
    
    if 'system' not in st.session_state:
        st.session_state.system = PointageSystem()
    
    with st.sidebar:
        st.title("Navigation")
        page = st.radio("", ["Pointage", "Administration", "Rapports"])
    
    if page == "Pointage":
        show_pointage_page()
    elif page == "Administration":
        show_admin_page()
    else:
        show_reports_page()

if __name__ == "__main__":
    main()
