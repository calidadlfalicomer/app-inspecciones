import streamlit as st
import datetime
import pandas as pd
from sqlalchemy import create_engine
import uuid
import time
import plotly.express as px

# --- 1. CONEXIÓN A LA BASE DE DATOS ---
db_url = "postgresql://postgres.gejkgyqrnmetjdguekvt:Alicomer2027%23@aws-0-us-west-2.pooler.supabase.com:5432/postgres"

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
menu = st.sidebar.radio("Navegación:", ["📝 Ingreso de Inspección", "⚙️ Mantenedor de Personal", "📊 Panel de Métricas"], key="menu_principal")

# ==========================================
# PANTALLA 1: MANTENEDOR DE PERSONAL (MODO ADMIN)
# ==========================================
if menu == "⚙️ Mantenedor de Personal":
    st.title("⚙️ Mantenedor de Personal")
    
    st.info("⚠️ Acceso restringido a Jefatura de Calidad.")
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
                st.dataframe(df_personal)

                if st.button("Reemplazar Base de Datos"):
                    engine = create_engine(db_url)
                    df_personal.to_sql('maestro_personal', engine, if_exists='replace', index=False)
                    st.cache_data.clear()
                    st.success("✅ ¡Base de datos reemplazada con éxito! Ahora es Multi-Planta.")
            except Exception as e:
                st.error(f"Error al procesar el archivo: {e}")

        st.divider()

        st.subheader("Opción 2: Ingreso Rápido Manual")
        
        # ESTRUCTURA DIVIDIDA PARA EL NOMBRE
        col_pl, col_r = st.columns(2)
        with col_pl:
            nueva_planta = st.text_input("Planta (Ej: Alicomer o AMBAS)")
        with col_r:
            nuevo_rol = st.selectbox("Rol", ["Monitor", "Trabajador"])
            
        col_n1, col_n2, col_p = st.columns([1.5, 1.5, 1])
        with col_n1:
            nuevo_nombre = st.text_input("Nombre(s)")
        with col_n2:
            nuevo_apellido = st.text_input("Apellido(s)")
        with col_p:
            nuevo_pin = st.text_input("PIN (Solo monitores)", max_chars=4, type="password")

        if st.button("Agregar Persona"):
            if nuevo_nombre.strip() != "" and nuevo_apellido.strip() != "" and nueva_planta.strip() != "":
                
                # UNIÓN Y FORMATO AUTOMÁTICO (Ej: Juan Perez)
                nombre_completo = f"{nuevo_nombre.strip()} {nuevo_apellido.strip()}".title()
                planta_limpia = nueva_planta.strip().upper() if nueva_planta.strip().upper() == "AMBAS" else nueva_planta.strip().title()
                pin_final = nuevo_pin if nuevo_rol == "Monitor" else None
                
                nuevo_registro_personal = pd.DataFrame([{'Planta': planta_limpia, 'Rol': nuevo_rol, 'Nombre': nombre_completo, 'PIN': pin_final}])

                try:
                    engine = create_engine(db_url)
                    nuevo_registro_personal.to_sql('maestro_personal', engine, if_exists='append', index=False)
                    st.cache_data.clear()
                    st.success(f"✅ {nombre_completo} agregado exitosamente a {planta_limpia}.")
                except Exception as e:
                    st.error(f"❌ Error al agregar. Detalle: {e}")
            else:
                st.warning("⚠️ Debe ingresar Planta, Nombre y Apellido obligatoriamente.")

# ==========================================
# PANTALLA 2: INGRESO DE INSPECCIÓN (LOGIN DE MONITORES)
# ==========================================
elif menu == "📝 Ingreso de Inspección":

    @st.cache_data(ttl=60) 
    def cargar_nombres_oficiales():
        try:
            engine = create_engine(db_url)
            df = pd.read_sql("SELECT * FROM maestro_personal", engine)
            return df
        except Exception as e:
            return pd.DataFrame() 

    df_personal = cargar_nombres_oficiales()

    if not st.session_state['autenticado']:
        st.title("🔒 Acceso de Monitores")
        st.write("Ingrese sus credenciales para iniciar una inspección.")
        
        if df_personal.empty or 'PIN' not in df_personal.columns or 'Planta' not in df_personal.columns:
            st.warning("⚠️ El sistema no está configurado aún. Vaya al Mantenedor y suba el Excel.")
        else:
            monitores_db = df_personal[df_personal['Rol'] == 'Monitor']
            lista_monitores = monitores_db['Nombre'].str.strip().drop_duplicates().sort_values().tolist()
            
            usuario_intento = st.selectbox("Seleccione su usuario:", lista_monitores, index=None, placeholder="--- Elija su nombre ---")
            pin_intento = st.text_input("Ingrese su PIN numérico:", type="password")
            
            if st.button("Ingresar", type="primary"):
                if usuario_intento is None:
                    st.error("Seleccione un usuario.")
                else:
                    fila_monitor = monitores_db[monitores_db['Nombre'] == usuario_intento].iloc[0]
                    pin_real = fila_monitor['PIN']
                    planta_real = fila_monitor['Planta']
                    
                    pin_real_str = str(pin_real).strip()
                    if pin_real_str.endswith('.0'):
                        pin_real_str = pin_real_str[:-2]
                    
                    if str(pin_intento).strip() == pin_real_str:
                        st.session_state['autenticado'] = True
                        st.session_state['monitor_activo'] = usuario_intento
                        st.session_state['planta_activa'] = str(planta_real).strip()
                        st.rerun()
                    else:
                        st.error("❌ PIN incorrecto.")

    else:
        st.sidebar.divider()
        st.sidebar.success(f"👤 Conectado: {st.session_state['monitor_activo']}")
        if st.sidebar.button("Cerrar Sesión"):
            st.session_state['autenticado'] = False
            st.session_state['monitor_activo'] = None
            st.session_state['planta_activa'] = None
            st.rerun()

        st.title("Checklist de Higiene R.P-15.02")
        st.subheader("Datos Generales")

        # --- HORA CHILENA FORZADA PARA MOSTRAR ---
        ahora_chile = pd.Timestamp.now(tz='America/Santiago')

        col1, col2 = st.columns(2)
        with col1:
            st.text_input("Fecha", ahora_chile.strftime("%d-%m-%Y"), disabled=True, key=f"f_{st.session_state['llave_reinicio']}")
        with col2:
            st.text_input("Hora de apertura", ahora_chile.strftime("%H:%M"), disabled=True, key=f"h_{st.session_state['llave_reinicio']}")

        col_p, col_m, col_t = st.columns([1, 1.5, 1.5])
        
        es_multiplanta = st.session_state['planta_activa'].upper() == "AMBAS"
        
        with col_p:
            if es_multiplanta:
                plantas_reales = df_personal[df_personal['Planta'].str.upper() != 'AMBAS']['Planta'].dropna().unique().tolist()
                planta_final = st.selectbox("Planta*", plantas_reales, index=None, placeholder="-- Elija --", key=f"sel_p_{st.session_state['llave_reinicio']}")
            else:
                planta_final = st.session_state['planta_activa']
                st.text_input("Planta*", planta_final, disabled=True)

        if planta_final:
            trabajadores_planta = df_personal[(df_personal['Rol'] == 'Trabajador') & (df_personal['Planta'].str.upper() == str(planta_final).upper())]
            lista_trabajadores = trabajadores_planta['Nombre'].str.strip().drop_duplicates().sort_values().tolist()
        else:
            lista_trabajadores = []

        with col_m:
            monitor = st.text_input("Monitor*", st.session_state['monitor_activo'], disabled=True)
        
        with col_t:
            trabajador = st.selectbox("Trabajador Evaluado*", lista_trabajadores, index=None, placeholder="--- Seleccione Trabajador ---", key=f"sel_t_{st.session_state['llave_reinicio']}")        
        
        # --- MINI-MANTENEDOR DIVIDIDO EN NOMBRE Y APELLIDO ---
        if planta_final:
            with st.expander("➕ ¿Falta personal? Agregar nuevo trabajador a la lista"):
                col_n1, col_n2 = st.columns(2)
                with col_n1:
                    nuevo_nombre_rapido = st.text_input("Nombre:")
                with col_n2:
                    nuevo_apellido_rapido = st.text_input("Apellido:")
                
                if st.button("Guardar y Actualizar Lista", type="secondary"):
                    if nuevo_nombre_rapido.strip() != "" and nuevo_apellido_rapido.strip() != "":
                        
                        # UNE Y FORMATEA (Pone las mayúsculas correctas automáticamente)
                        nombre_completo_rapido = f"{nuevo_nombre_rapido.strip()} {nuevo_apellido_rapido.strip()}".title()
                        
                        nuevo_registro = pd.DataFrame([{
                            'Planta': str(planta_final).title(), 
                            'Rol': 'Trabajador', 
                            'Nombre': nombre_completo_rapido, 
                            'PIN': None
                        }])
                        
                        try:
                            engine = create_engine(db_url)
                            nuevo_registro.to_sql('maestro_personal', engine, if_exists='append', index=False)
                            st.cache_data.clear() 
                            st.success(f"✅ {nombre_completo_rapido} agregado. Actualizando...")
                            time.sleep(1)
                            st.rerun() 
                        except Exception as e:
                            st.error(f"❌ Error al agregar: {e}")
                    else:
                        st.warning("⚠️ Debe ingresar el Nombre y el Apellido en ambas casillas para poder guardar.")
        # -----------------------------------------------------

        st.write("Turno*")
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            turno_letra = st.radio("Turno Letra*", ["A", "B", "C"], horizontal=True, label_visibility="collapsed")
        with col_t2:
            turno_numero = st.radio("Turno Numero*", ["1", "2", "3"], horizontal=True, label_visibility="collapsed")

        area = st.radio("Área*", ["Bodega MMPP", "Masas", "Corte", "Horno", "Envasado", "Aseo", "Jefatura"], horizontal=True)

        st.divider()
        st.subheader("Evaluación de Parámetros")

        lista_acciones = [
            "1- Completar uniforme, cambiar", "2- Cortar, limpiar uñas, eliminar barniz",
            "3- Retirar, guardar joyas y/o accesorios", "4- Repetir lavado de manos y/o hábitos de higiene",
            "5- No ingresa a planta", "6- Se entrega mascarilla, enfermo",
            "7- Se entrega parche y guante para cubrir herida", "8- Afeitarse",
            "9- Quitar maquillaje", "10- Retirar alimento", "11- Capacitar"
        ]

        respuestas = {}
        acciones_seleccionadas = {}

        preguntas = [
            "1_Manos_Limpias", "2_Pelo_Tomado_y_Cofia", "3_Uñas_Cortas_y_Sin_Esmalte",
            "4_Sin_Heridas_Ni_Cortes", "5_Uniforme_Limpio_y_Buen_Estado", 
            "6_Lentes_Opticos_Buen_Estado", "7_Sin_Maquillaje_Barba_Pestañas", 
            "8_Celular_Parlante_y/o_Audifonos", "9_Joyas_y_Accesorios", 
            "10_Buen_Estado_Salud", "11_Consumo_de_Alimentos_y_bebidas"
        ]

        for i, pregunta in enumerate(preguntas, 1):
            if i == 6:
                resp = st.radio(f"{pregunta}*", ["CUMPLE", "NO CUMPLE", "NO APLICA"], horizontal=True, index=2, key=f"q{i}_{st.session_state['llave_reinicio']}")
            else:
                resp = st.radio(f"{pregunta}*", ["CUMPLE", "NO CUMPLE"], horizontal=True, key=f"q{i}_{st.session_state['llave_reinicio']}")

            respuestas[f"q{i}"] = resp

            if resp == "NO CUMPLE":
                acc = st.selectbox(
                    f"⚠️ Justifique la acción correctiva para el punto {i}:", 
                    lista_acciones, 
                    index=None, 
                    placeholder="--- Elija una acción obligatoria ---",
                    key=f"acc_{i}_{st.session_state['llave_reinicio']}"
                )
                acciones_seleccionadas[f"q{i}"] = acc

            st.write("---")

        st.write("")

        if st.button("Guardar Inspección", type="primary", key="btn_guardar"):

            if planta_final is None:
                st.error("⚠️ ERROR: Debe seleccionar la Planta antes de guardar.")
            elif trabajador is None:
                st.error("⚠️ ERROR: Debe seleccionar un Trabajador Evaluado antes de guardar.")
            elif None in acciones_seleccionadas.values():
                st.error("⚠️ ERROR: Ha marcado 'NO CUMPLE' pero le falta seleccionar la acción correctiva. Revise el formulario antes de guardar.")
            else:
                turno_final = f"{turno_letra}{turno_numero}"
                
                # --- HORA CHILENA EXACTA DE GUARDADO ---
                momento_exacto_guardado = pd.Timestamp.now(tz='America/Santiago').strftime("%Y-%m-%d %H:%M:%S")
                
                nuevo_id = st.session_state['id_actual'] 

                nuevo_registro_cabecera = pd.DataFrame([{
                    'id_registro': nuevo_id,
                    'planta': planta_final,
                    'fecha_hora': momento_exacto_guardado, 
                    'monitor': monitor,
                    'trabajador_evaluado': trabajador, 
                    'turno_final': turno_final, 
                    'area': area
                }])

                detalles_lista = []
                for i, pregunta in enumerate(preguntas, 1):
                    llave_pregunta = f"q{i}"
                    evaluacion_actual = respuestas[llave_pregunta]
                    accion = acciones_seleccionadas.get(llave_pregunta, "Ninguna")

                    detalles_lista.append({
                        'id_registro': nuevo_id,
                        'parametro': pregunta,
                        'evaluacion': evaluacion_actual,
                        'accion_correctiva': accion
                    })

                df_detalles = pd.DataFrame(detalles_lista)

                try:
                    with st.spinner("Guardando registro en la nube..."):
                        engine = create_engine(db_url)
                        nuevo_registro_cabecera.to_sql('inspecciones_cabecera_v2', engine, if_exists='append', index=False)
                        df_detalles.to_sql('inspecciones_detalle_v2', engine, if_exists='append', index=False)

                    st.success(f"✅ ¡Registro guardado exitosamente! | Planta: {planta_final} | Turno: {turno_final}")
                    
                    st.session_state['id_actual'] = str(uuid.uuid4())
                    st.session_state['llave_reinicio'] += 1
                    
                    time.sleep(1.5)
                    st.rerun() 

                except Exception as e:
                    if "UniqueViolation" in str(e):
                        st.warning("⚠️ El registro ya fue guardado correctamente. Evite hacer doble clic.")
                    else:
                        st.error(f"❌ Error al guardar en la base de datos: {e}")

# ==========================================
# PANTALLA 3: PANEL DE MÉTRICAS (DATA STUDIO)
# ==========================================
elif menu == "📊 Panel de Métricas":
    st.title("📊 Panel de Métricas de Higiene")
    
    @st.cache_data(ttl=60)
    def cargar_datos_completos():
        try:
            engine = create_engine(db_url)
            query = """
                SELECT 
                    c.planta, c.fecha_hora, c.monitor, c.trabajador_evaluado, 
                    c.turno_final, c.area, d.parametro, d.evaluacion, d.accion_correctiva 
                FROM inspecciones_cabecera_v2 c
                JOIN inspecciones_detalle_v2 d ON c.id_registro = d.id_registro
            """
            df = pd.read_sql(query, engine)
            df['fecha_hora'] = pd.to_datetime(df['fecha_hora'])
            return df
        except Exception as e:
            st.error(f"Error al cargar datos: {e}")
            return pd.DataFrame()

    df_total = cargar_datos_completos()

    if df_total.empty:
        st.info("Aún no hay registros en la nueva base de datos Multi-Planta para mostrar.")
    else:
        st.subheader("Filtros de Análisis")
        col_f1, col_f2 = st.columns(2)
        
        with col_f1:
            lista_plantas = ["Todas las Plantas"] + list(df_total['planta'].dropna().unique())
            planta_filtro = st.selectbox("🏢 Seleccionar Planta", lista_plantas)
        
        with col_f2:
            meses_disponibles = df_total['fecha_hora'].dt.to_period('M').unique()
            mes_filtro = st.selectbox("📅 Mes de Análisis", ["Todos"] + list(meses_disponibles))

        df_filtrado = df_total.copy()
        if planta_filtro != "Todas las Plantas":
            df_filtrado = df_filtrado[df_filtrado['planta'] == planta_filtro]
        if mes_filtro != "Todos":
            df_filtrado = df_filtrado[df_filtrado['fecha_hora'].dt.to_period('M') == mes_filtro]

        st.divider()

        df_nc = df_filtrado[df_filtrado['evaluacion'] == 'NO CUMPLE']

        if df_nc.empty:
            st.success("🎉 ¡Excelente! No hay registros de 'NO CUMPLE' en este periodo para la selección.")
        else:
            st.subheader(f"Análisis de Desviaciones Absolutas (Total: {len(df_nc)} No Cumple)")
            
            # --- FILA 1: PARÁMETROS Y TURNOS ---
            col_graf1, col_graf2 = st.columns(2)

            with col_graf1:
                df_param = df_nc['parametro'].value_counts().reset_index().head(5)
                df_param.columns = ['Parámetro', 'Cantidad NC']
                df_param = df_param.sort_values('Cantidad NC', ascending=True) 
                
                fig_param = px.bar(df_param, x='Cantidad NC', y='Parámetro', orientation='h', 
                                   title='Top 5 Dimensiones Críticas', text_auto=True,
                                   color_discrete_sequence=['#4285F4'])
                fig_param.update_layout(yaxis_title=None, xaxis_title="N° de Desviaciones")
                fig_param.update_xaxes(tickformat="d") # Elimina decimales
                st.plotly_chart(fig_param, use_container_width=True)

            with col_graf2:
                df_turno = df_nc['turno_final'].value_counts().reset_index().head(5)
                df_turno.columns = ['Turno', 'Cantidad NC']
                
                fig_turno = px.bar(df_turno, x='Turno', y='Cantidad NC', 
                                   title='Desviaciones por Turno', text_auto=True,
                                   color_discrete_sequence=['#4285F4'])
                fig_turno.update_layout(xaxis_title="Turno", yaxis_title="N° de Desviaciones")
                fig_turno.update_yaxes(tickformat="d") # Elimina decimales
                st.plotly_chart(fig_turno, use_container_width=True)

            # --- FILA 2: TRABAJADORES Y ÁREAS ---
            col_graf3, col_graf4 = st.columns(2)

            with col_graf3:
                df_trab = df_nc['trabajador_evaluado'].value_counts().reset_index().head(5)
                df_trab.columns = ['Trabajador', 'Cantidad NC']
                df_trab = df_trab.sort_values('Cantidad NC', ascending=True)
                
                fig_trab = px.bar(df_trab, x='Cantidad NC', y='Trabajador', orientation='h', 
                                  title='Top 5 Trabajadores con Desviaciones', text_auto=True,
                                  color_discrete_sequence=['#4285F4'])
                fig_trab.update_layout(yaxis_title=None, xaxis_title="N° de Desviaciones")
                fig_trab.update_xaxes(tickformat="d") # Elimina decimales
                st.plotly_chart(fig_trab, use_container_width=True)

            with col_graf4:
                df_area = df_nc['area'].value_counts().reset_index()
                df_area.columns = ['Área', 'Cantidad NC']
                
                fig_area = px.pie(df_area, values='Cantidad NC', names='Área', 
                                  title='Distribución de Desviaciones por Área',
                                  hole=0.3) 
                fig_area.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig_area, use_container_width=True)
