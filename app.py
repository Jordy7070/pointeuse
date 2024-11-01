import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import plotly.express as px
from io import BytesIO
import openpyxl
import pytz

@st.cache_data(persist=True)
def load_employees(file_path):
    if file_path.exists():
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        return {}

@st.cache_data(persist=True)
def load_scans(file_path):
    if file_path.exists():
        df = pd.read_csv(file_path)
        df['DateTime'] = pd.to_datetime(df['Date'] + ' ' + df['Heure'])
        return df
    else:
        return pd.DataFrame(columns=[
            'ID_Employé', 'Nom', 'Prénom', 'Code_Barres', 
            'Date', 'Heure', 'Type_Scan', 'DateTime'
        ])

class PointageSystem:
    def __init__(self):
        self.data_dir = Path("data")
        self.data_dir.mkdir(exist_ok=True)
        self.employees_file = self.data_dir / "employees.json"
        self.scans_file = self.data_dir / "scans.csv"
        self.archive_dir = self.data_dir / "archives"
        self.archive_dir.mkdir(exist_ok=True)
        
        # Chargement des données en cache
        self.employees = load_employees(self.employees_file)
        self.scans_df = load_scans(self.scans_file)
        
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

    def calculate_daily_hours(self, employee_id, date):
        scans = self.scans_df[(self.scans_df['ID_Employé'] == employee_id) & (self.scans_df['Date'] == date)]
        total_hours = timedelta()
        entry_time = None
        for _, scan in scans.iterrows():
            if scan['Type_Scan'] == 'Entrée':
                entry_time = scan['DateTime']
            elif scan['Type_Scan'] == 'Sortie' and entry_time:
                total_hours += scan['DateTime'] - entry_time
                entry_time = None
        return total_hours.total_seconds() / 3600

    def export_data(self, start_date, end_date):
        filtered_data = self.scans_df[(self.scans_df['DateTime'] >= pd.Timestamp(start_date)) & (self.scans_df['DateTime'] <= pd.Timestamp(end_date))]
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            filtered_data.to_excel(writer, sheet_name='Pointages', index=False)
            pd.DataFrame(self.employees.values()).to_excel(writer, sheet_name='Employés', index=False)
        return output.getvalue()

def show_navigation():
    st.sidebar.title("Menu")
    pages = ["Pointage", "Administration", "Rapports"]
    page = st.sidebar.radio("Pages", pages)
    return page

def main():
    st.set_page_config(page_title="Système de Pointage", layout="wide")
    system = PointageSystem()
    page = show_navigation()

    if page == "Pointage":
        st.title("Enregistrement de Pointages")
        scan_input = st.text_input("Scanner votre badge", "")
        if scan_input:
            success, message = system.record_scan(scan_input)
            st.toast(message, success=success)
    elif page == "Administration":
        st.title("Gestion des Employés")
        st.text("Options d'administration...")
    elif page == "Rapports":
        st.title("Rapports et Analyses")
        st.text("Options de rapport...")
        
if __name__ == "__main__":
    main()
