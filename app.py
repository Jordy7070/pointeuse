import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
from pathlib import Path
import plotly.express as px
from io import BytesIO
import openpyxl
import pytz

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
        current_date = datetime.now()
        one_year_ago = current_date - timedelta(days=365)
        old_data = self.scans_df[self.scans_df['DateTime'] < one_year_ago]
        if not old_data.empty:
            archive_filename = f"archive_{one_year_ago.strftime('%Y%m%d')}.xlsx"
            archive_path = self.archive_dir / archive_filename
            with pd.ExcelWriter(archive_path, engine='openpyxl') as writer:
                old_data.to_excel(writer, index=False, sheet_name='Pointages')
                pd.DataFrame(self.employees).to_excel(writer, index=False, sheet_name='Employés')
            self.scans_df = self.scans_df[self.scans_df['DateTime'] >= one_year_ago]
            self.save_scans()

    def load_data(self):
        if self.employees_file.exists():
            with open(self.employees_file, 'r', encoding='utf-8') as f:
                self.employees = json.load(f)
        else:
            self.employees = {}
            self.save_employees()

        if self.scans_file.exists():
            self.scans_df = pd.read_csv(self.scans_file)
            self.scans_df['DateTime'] = pd.to_datetime(self.scans_df['Date'] + ' ' + self.scans_df['Heure'])
        else:
            self.scans_df = pd.DataFrame(columns=[
                'ID_Employé', 'Nom', 'Prénom', 'Code_Barres', 
                'Date', 'Heure', 'Type_Scan', 'DateTime'
            ])
            self.save_scans()

    def save_employees(self):
        with open(self.employees_file, 'w', encoding='utf-8') as f:
            json.dump(self.employees, f, indent=4, ensure_ascii=False)

    def save_scans(self):
        save_df = self.scans_df.drop(columns=['DateTime'])
        save_df.to_csv(self.scans_file, index=False, encoding='utf-8')

    def add_employee(self, id_emp, nom, prenom, code_barre):
        if code_barre not in self.employees:
            self.employees[code_barre] = {'id': id_emp, 'nom': nom, 'prenom': prenom, 'actif': True}
            self.save_employees()
            return True
        return False

    def record_scan(self, code_barre):
        if code_barre in self.employees:
            emp = self.employees[code_barre]
            current_time = datetime.now(pytz.timezone('Europe/Paris'))
            date_str = current_time.strftime('%Y-%m-%d')
            heure_str = current_time.strftime('%H:%M:%S')
            today_scans = self.scans_df[(self.scans_df['Code_Barres'] == code_barre) & (self.scans_df['Date'] == date_str)]
            type_scan = 'Entrée' if len(today_scans) % 2 == 0 else 'Sortie'
            nouveau_scan = pd.DataFrame([{
                'ID_Employé': emp['id'], 'Nom': emp['nom'], 'Prénom': emp['prenom'], 'Code_Barres': code_barre,
                'Date': date_str, 'Heure': heure_str, 'Type_Scan': type_scan
            }])
            self.scans_df = pd.concat([self.scans_df, nouveau_scan], ignore_index=True)
            self.save_scans()
            return True, f"{type_scan} enregistrée pour {emp['prenom']} {emp['nom']}"
        return False, "Code-barres non reconnu"

    def export_data(self, start_date, end_date):
        filtered_data = self.scans_df[(self.scans_df['DateTime'] >= pd.Timestamp(start_date)) & (self.scans_df['DateTime'] <= pd.Timestamp(end_date))]
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            filtered_data.to_excel(writer, sheet_name='Pointages', index=False)
            pd.DataFrame(self.employees.values()).to_excel(writer, sheet_name='Employés', index=False)
        return output.getvalue()

def show_pointage_page(system):
    st.title("Enregistrement de Pointages")
    scan_input = st.text_input("Scanner votre badge", "", key="scan_input")
    if scan_input:
        success, message = system.record_scan(scan_input)
        if success:
            st.success(message)
        else:
            st.error(message)
        st.session_state["scan_input"] = ""  # Réinitialise le champ après l'enregistrement

def show_admin_page(system):
    st.title("Administration")
    st.subheader("Ajouter un nouvel employé")
    id_emp = st.text_input("ID Employé")
    nom = st.text_input("Nom")
    prenom = st.text_input("Prénom")
    code_barre = st.text_input("Code Barres")
    if st.button("Ajouter l'employé"):
        if all([id_emp, nom, prenom, code_barre]):
            if system.add_employee(id_emp, nom, prenom, code_barre):
                st.success("Employé ajouté avec succès!")
            else:
                st.error("Ce code-barres existe déjà!")

    st.subheader("Liste des employés")
    if system.employees:
        df_employees = pd.DataFrame(system.employees.values())
        st.dataframe(df_employees)

def show_reports_page(system):
    st.title("Rapports et Analyses")
    tabs = st.tabs(["Journalier", "Export des données"])

    with tabs[0]:
        selected_date = st.date_input("Sélectionnez une date", value=datetime.now())
        if st.button("Générer rapport journalier"):
            date_str = selected_date.strftime('%Y-%m-%d')
            daily_data = []
            for code_barre, emp in system.employees.items():
                hours = system.calculate_daily_hours(emp['id'], date_str)
                if hours > 0:
                    daily_data.append({
                        'Employé': f"{emp['prenom']} {emp['nom']}",
                        'Heures': round(hours, 2)
                    })
            if daily_data:
                df_daily = pd.DataFrame(daily_data)
                st.dataframe(df_daily)

    with tabs[1]:
        start_date = st.date_input("Date de début", value=datetime.now() - timedelta(days=30))
        end_date = st.date_input("Date de fin", value=datetime.now())
        if st.button("Exporter les données"):
            data = system.export_data(start_date, end_date)
            st.download_button(
                label="📥 Télécharger les données",
                data=data,
                file_name=f'pointages_{start_date.strftime("%Y%m%d")}_{end_date.strftime("%Y%m%d")}.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )

def setup_page_config():
    st.set_page_config(page_title="Système de Pointage", layout="wide")

def main():
    setup_page_config()
    system = PointageSystem()
    
    page = st.sidebar.radio("Pages", ["Pointage", "Administration", "Rapports"])
    if page == "Pointage":
        show_pointage_page(system)
    elif page == "Administration":
        show_admin_page(system)
    elif page == "Rapports":
        show_reports_page(system)

if __name__ == "__main__":
    main()
