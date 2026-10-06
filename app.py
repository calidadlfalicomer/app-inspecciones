import streamlit as st
import datetime
import pandas as pd
from sqlalchemy import create_engine, text
import uuid
import time

# --- 1. CONEXIÓN A LA BASE DE DATOS ---
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
                    engine = create_engine(db_url)
                    df_personal.to_sql('maestro_personal', engine, if_exists='replace', index=False)
                    st.cache_data.clear()
                    st.success("✅ ¡Base de datos reemplazada con éxito! Ahora es Multi-Planta y en MAYÚSCULAS.")
            except Exception as e:
                st.error(f"Error al procesar el archivo: {e}")

        st.divider()

        st.subheader("Opción 2: Migración de Historial (Desde AppSheet)")
        st.warning("⚠️ Asegúrate de haber agregado la columna 'Planta' a tu Excel antiguo antes de subirlo.")
        archivo_historico = st.file_uploader("Cargar Historial Excel (AppSheet)", type=["xlsx", "xls"], key="hist")

        if archivo_historico is not None:
            if st.button("Procesar y Migrar Datos", type="primary"):
                try:
                    df_hist = pd.read_excel(archivo_historico)
                    
                    if 'Planta' not in df_hist.columns:
                        st.error("❌ El Excel no tiene la columna 'Planta'. Agrégala e inténtalo de nuevo.")
                    else:
                        with st.spinner("Traduciendo formato AppSheet a BD Relacional..."):
                            df_hist['nuevo_id_uuid'] = [str(uuid.uuid4()) for _ in range(len(df_hist))]
                            
                            df_cab = pd.DataFrame()
                            df_cab['id_registro'] = df_hist['nuevo_id_uuid']
                            df_cab['planta'] = df_hist['Planta']
                            df_cab['fecha_hora'] = pd.to_datetime(df_hist['Fecha_y_Hora']).astype(str)
                            df_cab['monitor'] = df_hist['Monitor'].astype(str).str.strip().str.upper() 
                            df_cab['trabajador_evaluado'] = df_hist['Trabajador_Evaluado'].astype(str).str.strip().str.upper() 
                            df_cab['turno_final'] = df_hist['Turno_Final'].astype(str)
                            
                            # MODIFICACIÓN: Forzar el área a mayúsculas y quitar espacios extra
                            df_cab['area'] = df_hist['Area'].astype(str).str.strip().str.upper()
                            
                            # MODIFICACIÓN: Diccionario ampliado para aceptar formatos con guiones o con puntos
                            mapa_preguntas = {
                                # Formato AppSheet original (Guiones bajos)
                                "1_Manos_Limpias": "1_Manos_Limpias",
                                "2_Pelo_Tomado_y_Cofia": "2_Pelo_Tomado_y_Cofia",
                                "3_Uñas_Cortas_y_Sin_Esmalte": "3_Uñas_Cortas_y_Sin_Esmalte",
                                "4_Sin_Heridas_Ni_Cortes": "4_Sin_Heridas_Ni_Cortes",
                                "5_Uniforme_Limpio_y_Buen_Estado": "5_Uniforme_Limpio_y_Buen_Estado",
                                "6_Lentes_Opticos_Buen_Estado": "6_Lentes_Opticos_Buen_Estado",
                                "7_Sin_Maquillaje_Barba_Pestañas": "7_Sin_Maquillaje_Barba_Pestañas",
                                "8_Celular_Parlante_y/o_Audifonos": "8_Celular_Parlante_y/o_Audifonos",
                                "8_Celular, Parlante y/o Audifonos": "8_Celular_Parlante_y/o_Audifonos",
                                "9_Joyas y Accesorios": "9_Joyas_y_Accesorios",
                                "10_Buen_Estado_Salud": "10_Buen_Estado_Salud",
                                "11_Consumo de Alimentos y bebidas": "11_Consumo_de_Alimentos_y_bebidas",
                                
                                # Formato Excel plano (Puntos y espacios)
                                "1. Manos Limpias": "1_Manos_Limpias",
                                "2. Pelo Tomado y Cofia": "2_Pelo_Tomado_y_Cofia",
                                "3. Uñas Cortas y Sin Esmalte": "3_Uñas_Cortas_y_Sin_Esmalte",
                                "4. Sin Heridas Ni Cortes": "4_Sin_Heridas_Ni_Cortes",
                                "5. Uniforme Limpio y Buen Estado": "5_Uniforme_Limpio_y_Buen_Estado",
                                "6. Lentes Opticos Buen Estado": "6_Lentes_Opticos_Buen_Estado",
                                "7. Sin Maquillaje, Barba, Pestañas": "7_Sin_Maquillaje_Barba_Pestañas",
                                "8. Celular, Parlante y/o Audifonos": "8_Celular_Parlante_y/o_Audifonos",
                                "9. Joyas y Accesorios": "9_Joyas_y_Accesorios",
                                "10. Buen Estado Salud": "10_Buen_Estado_Salud",
                                "11. Consumo de Alimentos y bebidas": "11_Consumo_de_Alimentos_y_bebidas"
                            }
                            
                            detalles = []
                            for idx, row in df_hist.iterrows():
                                id_reg = row['nuevo_id_uuid']
                                accion_gen = str(row.get('Accion_Correctiva', 'Ninguna'))
                                if accion_gen.strip().lower() in ['nan', 'none', '']: 
                                    accion_gen = 'Ninguna'
                                
                                for col_excel, param_db in mapa_preguntas.items():
                                    if col_excel in row:
                                        evaluacion = str(row[col_excel]).strip().upper()
                                        if evaluacion not in ['CUMPLE', 'NO CUMPLE', 'NO APLICA']:
