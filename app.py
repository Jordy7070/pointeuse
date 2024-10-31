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

def show_reports_page():
    st.title("Rapports et Analyses")
    
    tab1, tab2 = st.tabs(["Rapport Journalier", "Rapport Mensuel"])
    
    with tab1:
        st.subheader("Heures travaillées par jour")
        
        # Sélection de la date
        selected_date = st.date_input("Sélectionnez la date")
        
        if selected_date:
            date_str = selected_date.strftime('%Y-%m-%d')
            daily_report = []
            
            for code_barre, emp in st.session_state.system.employees.items():
                hours = st.session_state.system.calculate_daily_hours(emp['id'], date_str)
                if hours > 0:
                    daily_report.append({
                        'Nom': f"{emp['prénom']} {emp['nom']}",
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
                
                # Statistiques globales
                st.subheader("Statistiques globales")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Moyenne d'heures par employé", 
                             f"{monthly_report['Total_Heures'].mean():.2f}")
                with col2:
                    st.metric("Total des heures travaillées", 
                             f"{monthly_report['Total_Heures'].sum():.2f}")
                with col3:
                    st.metric("Nombre d'employés actifs", 
                             len(monthly_report))
                
                # Export Excel
                if st.button("Exporter le rapport mensuel"):
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        monthly_report.to_excel(writer, 
                                             sheet_name='Rapport Mensuel',
                                             index=False)
                        
                        # Ajout d'une feuille pour les détails quotidiens
                        daily_details = []
                        for _, emp in monthly_report.iterrows():
                            hours = st.session_state.system.calculate_monthly_hours(
                                emp['ID_Employé'], selected_year, selected_month
                            )
                            for date, hrs in hours.items():
                                daily_details.append({
                                    'ID_Employé': emp['ID_Employé'],
                                    'Nom': f"{emp['Prénom']} {emp['Nom']}",
                                    'Date': date,
                                    'Heures': round(hrs, 2)
                                })
                        
                        pd.DataFrame(daily_details).to_excel(
                            writer,
                            sheet_name='Détails Quotidiens',
                            index=False
                        )
                    
                    excel_data = output.getvalue()
                    st.download_button(
                        label="Télécharger Excel",
                        data=excel_data,
                        file_name=f'rapport_mensuel_{selected_month}_{selected_year}.xlsx',
                        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                    )
            else:
                st.info("Aucune donnée pour cette période")

# Mettre à jour la fonction main() pour inclure la nouvelle page de rapports
def main():
    # ... (reste du code inchangé)
    if page == "Rapports":
        show_reports_page()

if __name__ == "__main__":
    main()
