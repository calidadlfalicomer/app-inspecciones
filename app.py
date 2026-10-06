import streamlit as st
import datetime
import pandas as pd
from sqlalchemy import create_engine, text
import uuid
import time

# --- 1. CONEXIÓN A LA BASE DE DATOS ---
# Incluye +psycopg2 para que Streamlit sepa qué driver usar
db_url = "postgresql+psycopg2://postgres.gejkgyqrnmetjdguekvt:Alicomer2027%23@aws-0-us-west-2.pooler.supabase.com:5432/postgres"

# --- 2. MEMORIA DE SESIÓN ---
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False
if 'monitor_activo' not in st.session_state:
    st.session_state['monitor_activo'] = None
if 'planta_activa' not in st.session_state:
    st.session_state['planta_activa'] = None
if 'id_actual' not in st.session_state:
    st.session_state['id_actual'] = str(uuid.uuid4())
if 'llave_reinicio' not in st.session_state:
    st.session_state['llave_reinicio'] = 0

# --- 3. MENÚ LATERAL ---
st.sidebar.title("Sistema de Gestión")
menu = st.sidebar.radio("Navegación:", ["📝 Formularios Operativos", "✅ Verificación Jefatura", "⚙️ Mantenedor de Personal"], key="menu_principal")


# ==========================================
# PANTALLA 1: MANTENEDOR DE PERSONAL Y MIGRACIÓN
# ==========================================
if menu == "⚙️ Mantenedor de Personal":
    st.title("⚙️ Mantenedor de Personal")
    
    st.info("⚠️ Acceso restringido a Jefatura de Calidad Corporativa.")
    admin_pass = st.text_input("Ingrese contraseña de administrador:", type="password")
    
    if admin_pass == "Calidad2026": 
        st.success("Acceso concedido.")
        st.divider()

        st.subheader("Opción 1: Carga Masiva (Excel)")
        st.write("Sube la nómina oficial. **Debe contener 4 columnas exactas: Planta, Rol, Nombre, PIN**")
        st.write("*(Tip: Si un monitor revisa más de una instalación, ponle la palabra **AMBAS** en su Planta)*")
        archivo_subido = st.file_uploader("Cargar archivo Excel", type=["xlsx"])

        if archivo_subido is not None:
            try:
                df_personal = pd.read_excel(archivo_subido)
                
                # FORZAR MAYÚSCULAS EN EL EXCEL
                if 'Nombre' in df_personal.columns:
                    df_personal['Nombre'] = df_personal['Nombre'].astype(str).str.upper().str.strip()
                    
                st.dataframe(df_personal)

                if st.button("Reemplazar Base de Datos"):
                    engine = create_engine(db
