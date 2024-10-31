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

class PointageSystem:
    def __init__(self):
        # Création des dossiers et fichiers nécessaires
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
        else:
            self.scans_df = pd.DataFrame(columns=[
                'ID_Employé', 'Nom', 'Prénom', 'Code_Barres', 
                'Date', 'Heure', 'Type_Scan'
            ])
            self.save_scans()

    def save_employees(self):
        with open(self.employees_file, 'w') as f:
            json.dump(self.employees, f, indent=4)

    def save_scans(self):
        self.scans_df.to_csv(self.scans_file, index=False)

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
            date = current_time.strftime('%Y-%m-%d')
            heure = current_time.strftime('%H:%M:%S')
            
            # Déterminer le type de scan
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

def main():
    st.set_page_config(page_title="Système de Pointage", layout="wide")
    
    # Initialisation du système
    if 'system' not in st.session_state:
        st.session_state.system = PointageSystem()

    # Menu latéral
    with st.sidebar:
        st.title("Navigation")
        page = st.radio("", ["Pointage", "Administration", "Rapports"])

    if page == "Pointage":
        show_pointage_page()
    elif page == "Administration":
        show_admin_page()
    else:
        show_reports_page()

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
            
            # Export Excel
            if st.button("Exporter la liste"):
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_employees.to_excel(writer, index=False)
                excel_data = output.getvalue()
                b64 = base64.b64encode(excel_data).decode()
                href = f'<a href="data:application/octet-stream;base64,{b64}" download="employees.xlsx">Télécharger Excel</a>'
                st.markdown(href, unsafe_allow_html=True)
        else:
            st.info("Aucun employé enregistré")

def show_reports_page():
    st.title("Rapports et Analyses")
    
    # Sélection de la période
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Date de début")
    with col2:
        end_date = st.date_input("Date de fin")
    
    if start_date and end_date:
        # Filtrer les données
        mask = (pd.to_datetime(st.session_state.system.scans_df['Date']).dt.date >= start_date) & \
               (pd.to_datetime(st.session_state.system.scans_df['Date']).dt.date <= end_date)
        filtered_df = st.session_state.system.scans_df[mask]
        
        if not filtered_df.empty:
            # Statistiques
            st.subheader("Statistiques de présence")
            
            # Graphique des présences par jour
            daily_presence = filtered_df[filtered_df['Type_Scan'] == 'Entrée'].groupby('Date').size()
            fig = px.line(daily_presence, title="Nombre de présences par jour")
            st.plotly_chart(fig)
            
            # Export des données
            if st.button("Exporter les données"):
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    filtered_df.to_excel(writer, index=False)
                excel_data = output.getvalue()
                b64 = base64.b64encode(excel_data).decode()
                href = f'<a href="data:application/octet-stream;base64,{b64}" download="pointages.xlsx">Télécharger Excel</a>'
                st.markdown(href, unsafe_allow_html=True)
        else:
            st.info("Aucune donnée pour la période sélectionnée")

if __name__ == "__main__":
    main()
