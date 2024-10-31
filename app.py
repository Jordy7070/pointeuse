import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go
import base64
from io import BytesIO
from collections import defaultdict

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
                entry_time = scan['DateTime']
            elif scan['Type_Scan'] == 'Sortie' and entry_time is not None:
                total_hours += scan['DateTime'] - entry_time
                entry_time = None

        return total_hours.total_seconds() / 3600  # Conversion en heures

    def calculate_monthly_hours(self, employee_id, year, month):
        """Calcule les heures travaillées pour un employé sur un mois donné"""
        monthly_scans = self.scans_df[
            (self.scans_df['ID_Employé'] == employee_id) & 
            (pd.to_datetime(self.scans_df['Date']).dt.year == year) &
            (pd.to_datetime(self.scans_df['Date']).dt.month == month)
        ]

        daily_hours = defaultdict(float)
        dates = sorted(monthly_scans['Date'].unique())
        
        for date in dates:
            hours = self.calculate_daily_hours(employee_id, date)
            daily_hours[date] = hours

        return daily_hours

    def generate_monthly_report(self, year, month):
        """Génère un rapport mensuel pour tous les employés"""
        report_data = []
        
        for code_barre, emp in self.employees.items():
            monthly_hours = self.calculate_monthly_hours(emp['id'], year, month)
            total_hours = sum(monthly_hours.values())
            working_days = len(monthly_hours)
            
            report_data.append({
                'ID_Employé': emp['id'],
                'Nom': emp['nom'],
                'Prénom': emp['prenom'],
                'Jours_Travaillés': working_days,
                'Total_Heures': round(total_hours, 2),
                'Moyenne_Heures/Jour': round(total_hours / working_days if working_days > 0 else 0, 2)
            })
            
        return pd.DataFrame(report_data)

def show_pointage_page():
    st.title("Pointage")
    
    # Affichage de l'heure actuelle
    st.write(f"Date et heure : {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    
    # Zone de scan
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
        recent_scans = st.session_state.system.scans_df.tail(5)
        if not recent_scans.empty:
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
            
            if st.button("Exporter la liste"):
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_employees.to_excel(writer, index=False)
                excel_data = output.getvalue()
                st.download_button(
                    label="Télécharger Excel",
                    data=excel_data,
                    file_name="employees.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        else:
            st.info("Aucun employé enregistré")

def show_reports_page():
    st.title("Rapports et Analyses")
    
    tab1, tab2 = st.tabs(["Rapport Journalier", "Rapport Mensuel"])
    
    with tab1:
        st.subheader("Heures travaillées par jour")
        selected_date = st.date_input("Sélectionnez la date")
        
        if selected_date:
            date_str = selected_date.strftime('%Y-%m-%d')
            daily_report = []
            
            for code_barre, emp in st.session_state.system.employees.items():
                hours = st.session_state.system.calculate_daily_hours(emp['id'], date_str)
                if hours > 0:
                    daily_report.append({
                        'Nom': f"{emp['prenom']} {emp['nom']}",
                        'Heures': round(hours, 2)
                    })
            
            if daily_report:
                df_daily = pd.DataFrame(daily_report)
                
                # Affichage graphique
                fig = px.bar(df_daily, x='Nom', y='Heures',
                           title=f"Heures travaillées le {date_str}")
                st.plotly_chart(fig)
                
                # Affichage tableau
                st.dataframe(df_daily)
                
                # Export Excel
                if st.button("Exporter le rapport journalier"):
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        df_daily.to_excel(writer, sheet_name='Rapport Journalier', index=False)
                    excel_data = output.getvalue()
                    st.download_button(
                        label="Télécharger Excel",
                        data=excel_data,
                        file_name=f'rapport_journalier_{date_str}.xlsx',
                        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                    )
            else:
                st.info("Aucune donnée pour cette date")
    
    with tab2:
        st.subheader("Rapport Mensuel")
        
        col1, col2 = st.columns(2)
        with col1:
            selected_year = st.selectbox("Année", 
                                       options=range(2020, datetime.now().year + 1),
                                       default=datetime.now().year)
        with col2:
            selected_month = st.selectbox("Mois", 
                                        options=range(1, 13),
                                        default=datetime.now().month)
        
        if st.button("Générer le rapport mensuel"):
            monthly_report = st.session_state.system.generate_monthly_report(
                selected_year, selected_month
            )
            
            if not monthly_report.empty:
                # Affichage graphique
                fig = px.bar(monthly_report, 
                           x='Nom',
                           y='Total_Heures',
                           title=f"Heures totales - {selected_month}/{selected_year}")
                st.plotly_chart(fig)
                
                # Affichage tableau détaillé
                st.dataframe(monthly_report)
                
                # Export Excel
                if st.button("Exporter le rapport mensuel"):
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        monthly_report.to_excel(writer, 
                                             sheet_name='Rapport Mensuel',
                                             index=False)
                    excel_data = output.getvalue()
                    st.download_button(
                        label="Télécharger Excel",
                        data=excel_data,
                        file_name=f'rapport_mensuel_{selected_month}_{selected_year}.xlsx',
                        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                    )
            else:
                st.info("Aucune donnée pour cette période")

def main():
    st.set_page_config(
        page_title="Système de Pointage",
        page_icon="⏰",
        layout="wide"
    )
    
    # Initialisation du système
    if 'system' not in st.session_state:
        st.session_state.system = PointageSystem()

    # Menu latéral
    with st.sidebar:
        st.title("Navigation")
        page = st.radio("", ["Pointage", "Administration", "Rapports"])

    # Navigation entre les pages
    if page == "Pointage":
        show_pointage_page()
    elif page == "Administration":
        show_admin_page()
    elif page == "Rapports":
        show_reports_page()

if __name__ == "__main__":
    main()
