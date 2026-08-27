import streamlit as st
import datetime
import pandas as pd
from sqlalchemy import create_engine, text
import uuid
import time

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
menu = st.sidebar.radio("Navegación:", ["📝 Formularios Operativos", "✅ Verificación Jefatura", "⚙️ Mantenedor de Personal"], key="menu_principal")


# ==========================================
# PANTALLA 1: MANTENEDOR DE PERSONAL Y MIGRACIÓN
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
                            df_cab['monitor'] = df_hist['Monitor'].str.title()
                            df_cab['trabajador_evaluado'] = df_hist['Trabajador_Evaluado'].str.title()
                            df_cab['turno_final'] = df_hist['Turno_Final'].astype(str)
                            df_cab['area'] = df_hist['Area']
                            
                            mapa_preguntas = {
                                "1_Manos_Limpias": "1_Manos_Limpias",
                                "2_Pelo_Tomado_y_Cofia": "2_Pelo_Tomado_y_Cofia",
                                "3_Uñas_Cortas_y_Sin_Esmalte": "3_Uñas_Cortas_y_Sin_Esmalte",
                                "4_Sin_Heridas_Ni_Cortes": "4_Sin_Heridas_Ni_Cortes",
                                "5_Uniforme_Limpio_y_Buen_Estado": "5_Uniforme_Limpio_y_Buen_Estado",
                                "6_Lentes_Opticos_Buen_Estado": "6_Lentes_Opticos_Buen_Estado",
                                "7_Sin_Maquillaje_Barba_Pestañas": "7_Sin_Maquillaje_Barba_Pestañas",
                                "8_Celular, Parlante y/o Audifonos": "8_Celular_Parlante_y/o_Audifonos",
                                "9_Joyas y Accesorios": "9_Joyas_y_Accesorios",
                                "10_Buen_Estado_Salud": "10_Buen_Estado_Salud",
                                "11_Consumo de Alimentos y bebidas": "11_Consumo_de_Alimentos_y_bebidas"
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
                                            evaluacion = 'CUMPLE' 
                                            
                                        acc = accion_gen if evaluacion == 'NO CUMPLE' else 'Ninguna'
                                        
                                        detalles.append({
                                            'id_registro': id_reg,
                                            'parametro': param_db,
                                            'evaluacion': evaluacion,
                                            'accion_correctiva': acc
                                        })
                            
                            df_det = pd.DataFrame(detalles)
                            
                            engine = create_engine(db_url)
                            df_cab.to_sql('inspecciones_cabecera_v2', engine, if_exists='append', index=False)
                            df_det.to_sql('inspecciones_detalle_v2', engine, if_exists='append', index=False)
                            
                            st.cache_data.clear()
                            st.success(f"✅ ¡Magnífico! Se migró el historial de {len(df_cab)} inspecciones a la nube.")
                            
                except Exception as e:
                    st.error(f"❌ Ocurrió un error en la traducción: {e}")


# ==========================================
# PANTALLA 2: FORMULARIOS OPERATIVOS (CENTRAL DE REGISTROS)
# ==========================================
elif menu == "📝 Formularios Operativos":

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

        # --- SELECTOR DE FORMULARIOS MULTIPLES ---
        st.sidebar.divider()
        formulario_elegido = st.sidebar.radio(
            "📋 SELECCIONE CHECKLIST:", 
            ["1. Higiene Personal (R.P-15.02)", "2. Limpieza Planta (R.P-20.05)"]
        )

        # ----------------------------------------------------------------------
        # FORMULARIO 1: HIGIENE PERSONAL (R.P-15.02)
        # ----------------------------------------------------------------------
        if formulario_elegido == "1. Higiene Personal (R.P-15.02)":
            st.title("Checklist de Higiene R.P-15.02")
            st.subheader("Datos Generales")

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
            
            if planta_final:
                with st.expander("➕ ¿Falta personal? Agregar nuevo trabajador a la lista"):
                    col_n1, col_n2 = st.columns(2)
                    with col_n1:
                        nuevo_nombre_rapido = st.text_input("Nombre:")
                    with col_n2:
                        nuevo_apellido_rapido = st.text_input("Apellido:")
                    
                    if st.button("Guardar y Actualizar Lista", type="secondary"):
                        if nuevo_nombre_rapido.strip() != "" and nuevo_apellido_rapido.strip() != "":
                            
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

        # ----------------------------------------------------------------------
        # FORMULARIO 2: LIMPIEZA PLANTA (R.P-20.05)
        # ----------------------------------------------------------------------
        elif formulario_elegido == "2. Limpieza Planta (R.P-20.05)":
            st.title("Check Limpieza y Sanitización (R.P-20.05)")
            st.subheader("Datos de la Inspección")
            
            diccionario_limpieza = {
                "Masas": {
                    "Diario": ["Mesones", "Cuchillos y Raspas", "Balanzas"],
                    "Semanal": ["Pisos", "Muros", "Revolvedora", "Basurero"],
                    "Quincenal": ["Cámara"],
                    "Mensual": ["Cableado y Tubos PVC"],
                    "Semestral": ["Techos"]
                },
                "Corte": {
                    "Diario": ["Pisos", "Mesones", "Cuchillos y Raspas", "Balanzas"],
                    "Semanal": ["Muros", "Cableado y Tubos PVC", "Chabatera", "Ovilladora", "Basurero"],
                    "Semestral": ["Techos"]
                },
                "Horno": {
                    "Diario": ["Pisos", "Mesones", "Cuchillos"],
                    "Semanal": ["Muros", "Cableado y Tubos PVC", "Tunel / Abatidor", "Basurero"],
                    "Mensual": ["Hornos"],
                    "Semestral": ["Techo"]
                },
                "Envases": {
                    "Diario": ["Pisos", "Mesones", "Balanzas"],
                    "Semanal": ["Muros", "Cableado y Tubos PVC", "Basurero"],
                    "Semestral": ["Techos"]
                },
                "Dosificado": {
                    "Diario": ["Pisos", "Mesones", "Balanzas"],
                    "Semanal": ["Muros", "Cableado y Tubos PVC", "Basurero"],
                    "Semestral": ["Techos"]
                },
                "Bodega": {
                    "Diario": ["Pisos"],
                    "Semanal": ["Muros"]
                },
                "Cámara despacho": {
                    "Diario": ["Pisos"],
                    "Semanal": ["Muros", "Lamas", "Basurero"],
                    "Quincenal": ["Traspaleta"]
                },
                "Baños": {
                    "Diario": ["Mujer", "Hombre"]
                },
                "Comedor": {
                    "Diario": ["Comedor"]
                },
                "Area externa": {
                    "Diario": ["Pasillo Entrada", "Calle Exterior Planta", "Sector Merma"]
                }
            }

            ahora_chile = pd.Timestamp.now(tz='America/Santiago')
            
            col1, col2 = st.columns(2)
            with col1:
                st.text_input("Fecha", ahora_chile.strftime("%d-%m-%Y"), disabled=True, key=f"f_limp_{st.session_state['llave_reinicio']}")
                
                es_multiplanta = st.session_state['planta_activa'].upper() == "AMBAS"
                if es_multiplanta:
                    plantas_reales = df_personal[df_personal['Planta'].str.upper() != 'AMBAS']['Planta'].dropna().unique().tolist()
                    planta_final_limpieza = st.selectbox("Planta*", plantas_reales, index=None, placeholder="-- Elija --", key=f"p_limp_{st.session_state['llave_reinicio']}")
                else:
                    planta_final_limpieza = st.session_state['planta_activa']
                    st.text_input("Planta*", planta_final_limpieza, disabled=True, key=f"p_limp_fijo_{st.session_state['llave_reinicio']}")
                    
                sector_sel = st.selectbox("1. Sector a Inspeccionar*", list(diccionario_limpieza.keys()), index=None, placeholder="Elija el sector...", key=f"sec_{st.session_state['llave_reinicio']}")
            
            with col2:
                st.text_input("Hora de apertura", ahora_chile.strftime("%H:%M"), disabled=True, key=f"h_limp_{st.session_state['llave_reinicio']}")
                st.text_input("Monitor*", st.session_state['monitor_activo'], disabled=True, key=f"mon_limp_{st.session_state['llave_reinicio']}")
                
                if sector_sel:
                    frecuencias_disponibles = list(diccionario_limpieza[sector_sel].keys())
                    frecuencia_sel = st.selectbox("2. Frecuencia (Tipo de Limpieza)*", frecuencias_disponibles, index=None, placeholder="Elija frecuencia...", key=f"freq_{st.session_state['llave_reinicio']}")
                else:
                    frecuencia_sel = None

            if sector_sel and frecuencia_sel:
                st.divider()
                st.subheader(f"Equipos a auditar: {sector_sel} ({frecuencia_sel})")
                
                equipos_a_evaluar = diccionario_limpieza[sector_sel][frecuencia_sel]
                
                lista_acciones_limpieza = [
                    "1- Volver a limpiar y sanitizar", 
                    "2- Capacitar al personal asignado", 
                    "3- Revisión de procedimiento/metodología", 
                    "4- Reforzar procedimiento eventual"
                ]
                
                respuestas_limpieza = {}
                acciones_limpieza = {}
                
                for i, equipo in enumerate(equipos_a_evaluar, 1):
                    st.markdown(f"**{i}. {equipo}**")
                    resp = st.radio(f"Evaluación {equipo}", ["CUMPLE", "NO CUMPLE"], horizontal=True, key=f"eq_{equipo}_{st.session_state['llave_reinicio']}")
                    respuestas_limpieza[equipo] = resp
                    
                    if resp == "NO CUMPLE":
                        acc = st.selectbox(
                            f"⚠️ Acción correctiva para {equipo}:", 
                            lista_acciones_limpieza, 
                            index=None, 
                            placeholder="--- Elija una acción obligatoria ---",
                            key=f"acclimp_{equipo}_{st.session_state['llave_reinicio']}"
                        )
                        acciones_limpieza[equipo] = acc
                    st.write("---")

                if st.button("Guardar Inspección de Limpieza", type="primary", key="btn_guardar_limp"):
                    if planta_final_limpieza is None:
                        st.error("⚠️ ERROR: Debe seleccionar la Planta.")
                    elif "NO CUMPLE" in respuestas_limpieza.values() and None in acciones_limpieza.values():
                        st.error("⚠️ Faltan acciones correctivas por justificar.")
                    else:
                        momento_exacto_guardado = pd.Timestamp.now(tz='America/Santiago').strftime("%Y-%m-%d %H:%M:%S")
                        nuevo_id_limpieza = st.session_state['id_actual']
                        
                        # Al guardar, inyectamos el estado "Pendiente" para que Jefatura lo vea
                        nuevo_registro_cabecera = pd.DataFrame([{
                            'id_registro': nuevo_id_limpieza,
                            'planta': planta_final_limpieza,
                            'fecha_hora': momento_exacto_guardado,
                            'monitor': st.session_state['monitor_activo'],
                            'sector': sector_sel,
                            'frecuencia': frecuencia_sel,
                            'estado_verificacion': 'Pendiente',
                            'verificado_por': None,
                            'fecha_verificacion': None
                        }])
                        
                        detalles_lista = []
                        for equipo in equipos_a_evaluar:
                            evaluacion_actual = respuestas_limpieza[equipo]
                            accion = acciones_limpieza.get(equipo, "Ninguna")
                            
                            detalles_lista.append({
                                'id_registro': nuevo_id_limpieza,
                                'equipo': equipo,
                                'evaluacion': evaluacion_actual,
                                'accion_correctiva': accion
                            })
                            
                        df_detalles = pd.DataFrame(detalles_lista)
                        
                        try:
                            with st.spinner("Guardando registro en la nube..."):
                                engine = create_engine(db_url)
                                nuevo_registro_cabecera.to_sql('limpieza_cabecera', engine, if_exists='append', index=False)
                                df_detalles.to_sql('limpieza_detalle', engine, if_exists='append', index=False)

                            st.success(f"✅ ¡Registro guardado exitosamente! | Sector: {sector_sel}")
                            
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
# PANTALLA 3: VERIFICACIÓN JEFATURA (EL CEREBRO DE GESTIÓN)
# ==========================================
elif menu == "✅ Verificación Jefatura":
    st.title("✅ Panel de Jefatura (R.P-20.05)")
    st.info("⚠️ Acceso restringido a Jefatura de Calidad.")
    admin_pass = st.text_input("Ingrese contraseña de administrador:", type="password", key="pass_jefatura")
    
    if admin_pass == "Calidad2026":
        st.success("Acceso concedido.")
        st.divider()
        
        tab1, tab2 = st.tabs(["🚨 Alertas de Frecuencia", "✍️ Verificación de Registros"])
        
        # --- PESTAÑA 1: SEMÁFORO DE ALERTAS ---
        with tab1:
            st.subheader("Estado actual de limpieza por sector")
            try:
                engine = create_engine(db_url)
                # Buscamos cuándo fue la última vez que se hizo cada tarea
                df_cab = pd.read_sql("SELECT planta, sector, frecuencia, fecha_hora FROM limpieza_cabecera", engine)
                
                if df_cab.empty:
                    st.info("Aún no hay registros de limpieza en la base de datos.")
                else:
                    df_cab['fecha_hora_dt'] = pd.to_datetime(df_cab['fecha_hora'])
                    ultima_limpieza = df_cab.groupby(['planta', 'sector', 'frecuencia'])['fecha_hora_dt'].max().reset_index()
                    
                    ahora = pd.Timestamp.now(tz='America/Santiago').tz_localize(None)
                    ultima_limpieza['dias_transcurridos'] = (ahora - ultima_limpieza['fecha_hora_dt']).dt.days
                    
                    # Lógica del motor de alertas
                    limites = {"Diario": 1, "Semanal": 7, "Quincenal": 15, "Mensual": 30, "Semestral": 180}
                    
                    def estado_alerta(row):
                        limite = limites.get(row['frecuencia'], 999)
                        dias = row['dias_transcurridos']
                        if dias > limite:
                            return "🔴 Atrasado"
                        elif dias == limite or dias == (limite - 1):
                            return "🟡 Por vencer"
                        else:
                            return "🟢 Al día"
                            
                    ultima_limpieza['Estado'] = ultima_limpieza.apply(estado_alerta, axis=1)
                    ultima_limpieza['Última Limpieza'] = ultima_limpieza['fecha_hora_dt'].dt.strftime('%Y-%m-%d %H:%M')
                    
                    # Mostrar el cuadro de mando
                    st.dataframe(ultima_limpieza[['planta', 'sector', 'frecuencia', 'Última Limpieza', 'dias_transcurridos', 'Estado']].sort_values('Estado'), use_container_width=True)
                    
            except Exception as e:
                st.error(f"Error cargando alertas: {e}")
                
        # --- PESTAÑA 2: BANDEJA DE ENTRADA Y FIRMA ---
        with tab2:
            st.subheader("Registros Pendientes de Revisión")
            try:
                engine = create_engine(db_url)
                df_pendientes = pd.read_sql("SELECT * FROM limpieza_cabecera WHERE estado_verificacion = 'Pendiente' OR estado_verificacion IS NULL", engine)
                
                if df_pendientes.empty:
                    st.success("🎉 ¡Todo al día! No hay registros pendientes de verificación.")
                else:
                    df_pendientes = df_pendientes.sort_values('fecha_hora', ascending=False)
                    st.dataframe(df_pendientes[['fecha_hora', 'planta', 'monitor', 'sector', 'frecuencia']], use_container_width=True)
                    
                    st.write("---")
                    st.write("**Revisar y Aprobar Inspección**")
                    
                    opciones_revision = df_pendientes['id_registro'].tolist()
                    nombres_revision = df_pendientes['fecha_hora'] + " | " + df_pendientes['planta'] + " | " + df_pendientes['sector'] + " (" + df_pendientes['monitor'] + ")"
                    dict_revision = dict(zip(opciones_revision, nombres_revision))
                    
                    registro_sel = st.selectbox("Seleccione el registro a revisar:", opciones_revision, format_func=lambda x: dict_revision[x], index=None, placeholder="--- Elija inspección ---")
                    
                    if registro_sel:
                        df_det = pd.read_sql(f"SELECT equipo, evaluacion, accion_correctiva FROM limpieza_detalle WHERE id_registro = '{registro_sel}'", engine)
                        st.write("Detalle levantado por el monitor:")
                        
                        # Colorear rojo automático si hay incumplimiento
                        def highlight_no_cumple(val):
                            color = '#ff4b4b' if val == 'NO CUMPLE' else ''
                            return f'background-color: {color}'
                            
                        st.dataframe(df_det.style.map(highlight_no_cumple, subset=['evaluacion']), use_container_width=True)
                        
                        if st.button("Firma Digital: Aprobar Registro", type="primary"):
                            momento_aprobacion = pd.Timestamp.now(tz='America/Santiago').strftime("%Y-%m-%d %H:%M:%S")
                            with engine.begin() as conn:
                                # Estampamos la firma en la BD
                                query = text(f"""
                                    UPDATE limpieza_cabecera 
                                    SET estado_verificacion = 'Verificado', 
                                        verificado_por = 'Jefe Calidad', 
                                        fecha_verificacion = '{momento_aprobacion}' 
                                    WHERE id_registro = '{registro_sel}'
                                """)
                                conn.execute(query)
                            st.success("✅ Registro verificado y cerrado correctamente.")
                            time.sleep(1.5)
                            st.rerun()
            except Exception as e:
                st.error(f"Error cargando registros pendientes: {e}")
