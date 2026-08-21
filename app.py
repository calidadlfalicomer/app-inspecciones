import streamlit as st
import datetime
import pandas as pd
from sqlalchemy import create_engine
import uuid
import time

# --- 1. CONEXIÓN A LA BASE DE DATOS ---
db_url = "postgresql://postgres.gejkgyqrnmetjdguekvt:Alicomer2027%23@aws-0-us-west-2.pooler.supabase.com:5432/postgres"

# --- 2. MENÚ LATERAL (BARRA DE NAVEGACIÓN) ---
st.sidebar.title("Sistema de Gestión")
menu = st.sidebar.radio("Navegación:", ["📝 Ingreso de Inspección", "⚙️ Mantenedor de Personal"], key="menu_principal")

# ==========================================
# PANTALLA 1: MANTENEDOR DE PERSONAL HÍBRIDO
# ==========================================
if menu == "⚙️ Mantenedor de Personal":
    st.title("⚙️ Mantenedor Oficial de Personal")

    st.subheader("Opción 1: Carga Masiva (Excel)")
    st.write("Reemplaza toda la base de datos con una nómina oficial nueva.")
    archivo_subido = st.file_uploader("Cargar archivo Excel (columnas: Rol, Nombre)", type=["xlsx"])

    if archivo_subido is not None:
        try:
            df_personal = pd.read_excel(archivo_subido)
            st.dataframe(df_personal)

            if st.button("Reemplazar Base de Datos"):
                engine = create_engine(db_url)
                df_personal.to_sql('maestro_personal', engine, if_exists='replace', index=False)
                st.cache_data.clear()
                st.success("¡Base de datos de personal reemplazada con éxito!")
        except Exception as e:
            st.error(f"Error al procesar el archivo: {e}")

    st.divider()

    st.subheader("Opción 2: Ingreso Rápido Manual")
    st.write("Agrega a un trabajador o monitor individual.")

    col_r, col_n = st.columns(2)
    with col_r:
        nuevo_rol = st.selectbox("Seleccione el Rol", ["Monitor", "Trabajador"])
    with col_n:
        nuevo_nombre = st.text_input("Nombre Completo")

    if st.button("Agregar Persona"):
        if nuevo_nombre.strip() != "":
            nombre_limpio = nuevo_nombre.strip().title() 
            nuevo_registro_personal = pd.DataFrame([{'Rol': nuevo_rol, 'Nombre': nombre_limpio}])

            try:
                engine = create_engine(db_url)
                nuevo_registro_personal.to_sql('maestro_personal', engine, if_exists='append', index=False)
                st.cache_data.clear()
                st.success(f"✅ {nombre_limpio} agregado exitosamente como {nuevo_rol}.")
            except Exception as e:
                st.error(f"❌ Error al agregar: {e}")
        else:
            st.warning("Debe ingresar un nombre válido.")

# ==========================================
# PANTALLA 2: INGRESO DE INSPECCIÓN
# ==========================================
elif menu == "📝 Ingreso de Inspección":

    @st.cache_data(ttl=60) 
    def cargar_nombres_oficiales():
        try:
            engine = create_engine(db_url)
            df = pd.read_sql("SELECT * FROM maestro_personal", engine)

            lista_m = df[df['Rol'] == 'Monitor']['Nombre'].str.strip().drop_duplicates().sort_values().tolist()
            lista_t = df[df['Rol'] == 'Trabajador']['Nombre'].str.strip().drop_duplicates().sort_values().tolist()

            return lista_m, lista_t
        except Exception as e:
            st.error(f"🔍 Error interno de conexión BBDD: {e}")
            return ["Revisar Error Arriba"], ["Revisar Error Arriba"]

    lista_monitores, lista_trabajadores = cargar_nombres_oficiales()
    
    # --- MEMORIA DE SESIÓN ---
    if 'id_actual' not in st.session_state:
        st.session_state['id_actual'] = str(uuid.uuid4())
        
    # EL TRUCO MAESTRO: Un contador para forzar el reinicio visual
    if 'llave_reinicio' not in st.session_state:
        st.session_state['llave_reinicio'] = 0
        
    st.title("Checklist de Higiene R.P-15.02")
    st.subheader("Datos Generales")

    col1, col2 = st.columns(2)
    with col1:
        fecha = st.date_input("Fecha", datetime.date.today(), disabled=True)
    with col2:
        hora = st.time_input("Hora", datetime.datetime.now().time(), disabled=True)

    col3, col4 = st.columns(2)
    with col3:
        monitor = st.selectbox("Monitor*", lista_monitores, index=None, placeholder="--- Seleccione Monitor ---", key=f"sel_m_{st.session_state['llave_reinicio']}")
    with col4:
        trabajador = st.selectbox("Trabajador Evaluado*", lista_trabajadores, index=None, placeholder="--- Seleccione Trabajador ---", key=f"sel_t_{st.session_state['llave_reinicio']}")        
    
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

        if monitor is None or trabajador is None:
            st.error("⚠️ ERROR: Debe seleccionar un Monitor y un Trabajador Evaluado antes de guardar.")
        elif None in acciones_seleccionadas.values():
            st.error("⚠️ ERROR: Ha marcado 'NO CUMPLE' pero le falta seleccionar la acción correctiva. Revise el formulario antes de guardar.")
        else:
            turno_final = f"{turno_letra}{turno_numero}"
            fecha_hora_str = f"{fecha} {hora}" 
            nuevo_id = st.session_state['id_actual'] 

            nuevo_registro_cabecera = pd.DataFrame([{
                'id_registro': nuevo_id,
                'fecha_hora': fecha_hora_str, 
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
                with st.spinner("Guardando registro en la nube, por favor espere..."):
                    engine = create_engine(db_url)
                    nuevo_registro_cabecera.to_sql('inspecciones_cabecera', engine, if_exists='append', index=False)
                    df_detalles.to_sql('inspecciones_detalle', engine, if_exists='append', index=False)

                st.success(f"✅ ¡Registro completo guardado exitosamente! | Turno: {turno_final}")
                
                # 1. Renovar ID en la memoria
                st.session_state['id_actual'] = str(uuid.uuid4())
                
                # 2. EL TRUCO: Aumentamos el contador en 1. Al recargar, todas las llaves cambiarán
                # y Streamlit se verá obligado a redibujar todo el formulario completamente en blanco.
                st.session_state['llave_reinicio'] += 1
                
                time.sleep(1)
                st.rerun() 

            except Exception as e:
                if "UniqueViolation" in str(e):
                    st.warning("⚠️ El registro ya fue guardado correctamente. Evite hacer doble clic.")
                else:
                    st.error(f"❌ Error al guardar en la base de datos: {e}")