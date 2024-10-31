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
                (self.scans_df['Code_Barres'] == code_barre) & 
                (self.scans_df['Date'] == date_str)
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

def show_reports_page():
    st.title("Rapports et Analyses")
    
    selected_date = st.date_input("Sélectionnez une date", value=datetime.now())
    
    if st.button("Générer rapport journalier"):
        date_str = selected_date.strftime('%Y-%m-%d')
        daily_data = []

        for code_barre, emp in st.session_state.system.employees.items():
            day_scans = st.session_state.system.scans_df[
                (st.session_state.system.scans_df['ID_Employé'] == emp['id']) & 
                (st.session_state.system.scans_df['Date'] == date_str)
            ].sort_values('DateTime')

            if not day_scans.empty:
                total_hours = st.session_state.system.calculate_daily_hours(emp['id'], date_str)
                first_scan = day_scans.iloc[0]
                last_scan = day_scans.iloc[-1]

                daily_data.append({
                    'Employé': f"{emp['prenom']} {emp['nom']}",
                    'Heure Arrivée': first_scan['Heure'],
                    'Heure Départ': last_scan['Heure'],
                    'Heures Travaillées': round(total_hours, 2)
                })

        if daily_data:
            df_daily = pd.DataFrame(daily_data)

            # Graphique des heures par employé
            fig = px.bar(
                df_daily,
                x='Employé',
                y='Heures Travaillées',
                title=f"Répartition du temps de travail - {date_str}"
            )
            st.plotly_chart(fig)

            # Tableau détaillé
            st.dataframe(df_daily)

            # Export Excel
            excel_buffer = BytesIO()
            df_daily.to_excel(excel_buffer, index=False, engine='openpyxl')
            excel_buffer.seek(0)

            if st.download_button(
                label="📥 Télécharger le rapport",
                data=excel_buffer,
                file_name=f'rapport_journalier_{date_str}.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            ):
                st.success("Rapport exporté avec succès!")
        else:
            st.info("Aucune donnée pour cette date")

def main():
    st.set_page_config(page_title="Système de Pointage", layout="wide")
    
    if 'system' not in st.session_state:
        st.session_state.system = PointageSystem()
    
    page = st.sidebar.selectbox("Navigation", ["Pointage", "Rapports"])
    
    if page == "Pointage":
        show_pointage_page()
    elif page == "Rapports":
        show_reports_page()

if __name__ == "__main__":
    main()
