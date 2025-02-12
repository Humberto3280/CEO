import pandas as pd
import streamlit as st

st.title("Carga y procesamiento de archivos")

# Subir archivos
uploaded_tc1 = st.file_uploader("Subir TC1.csv", type=["csv"])
uploaded_tc2 = st.file_uploader("Subir TC2.xlsx", type=["xlsx"])
uploaded_ap = st.file_uploader("Subir AP.xlsx", type=["xlsx"])
uploaded_divipola = st.file_uploader("Subir Dane_Divipola_08_2012.xlsx", type=["xlsx"])
uploaded_bitacora = st.file_uploader("Subir Bitacora.xlsx", type=["xlsx"])

# Verificar si ya hemos cargado los archivos antes
if "tc1" not in st.session_state and uploaded_tc1:
    st.session_state.tc1 = pd.read_csv(uploaded_tc1)

if "tc2" not in st.session_state and uploaded_tc2:
    st.session_state.tc2 = pd.read_excel(uploaded_tc2)

if "archivo_ap" not in st.session_state and uploaded_ap:
    def extraer_datos_excel(archivo_entrada, hoja_origen):
        df = pd.read_excel(archivo_entrada, sheet_name=hoja_origen, header=3)
        df = df[~df.iloc[:, 0].astype(str).str.contains("Total general", na=False)]
        return df
    st.session_state.archivo_ap = extraer_datos_excel(uploaded_ap, "TABLA TARIFAS")

if "davipola" not in st.session_state and uploaded_divipola:
    st.session_state.davipola = pd.read_excel(uploaded_divipola)

if "bitacora" not in st.session_state and uploaded_bitacora:
    st.session_state.bitacora = pd.read_excel(uploaded_bitacora)

# Si todos los archivos están cargados, procedemos con el análisis
if all(key in st.session_state for key in ["tc1", "tc2", "archivo_ap", "davipola", "bitacora"]):
    st.write("### Columnas en AP:", st.session_state.archivo_ap.columns.tolist())

    # Aplicar filtro por ID_COMERCIALIZADOR = 23442
    id_comercializador_col = 'ID COMERCIALIZADOR'
    niu_col = 'NIU'

    if id_comercializador_col in st.session_state.tc1.columns and niu_col in st.session_state.tc1.columns:
        tc1_filtrado = st.session_state.tc1[st.session_state.tc1[id_comercializador_col] == 23442]
        count_nius_tc1 = tc1_filtrado[niu_col].nunique()
        st.write(f"Número de NIUs en TC1 después de filtrar: {count_nius_tc1}")
    else:
        st.error("Las columnas esperadas no están en TC1.")

    # Validación de TC2
    if niu_col in st.session_state.tc2.columns:
        tc2_sin_duplicados = st.session_state.tc2.drop_duplicates(subset=niu_col)
        count_nius_tc2 = tc2_sin_duplicados[niu_col].nunique()
        st.write(f"Número de NIUs en TC2 después de eliminar duplicados: {count_nius_tc2}")

        # Preguntar al usuario cuánto restar
        ajuste_nius = st.number_input("Ingrese el valor a restar en la validación de TC2:", min_value=0, value=1, step=1)

        # Botón para confirmar y validar
        if st.button("Validar número de NIUs en TC2"):
            if count_nius_tc1 == count_nius_tc2 - ajuste_nius:
                st.success("El número de NIUs en TC2 coincide con el valor esperado.")
            else:
                st.error("El número de NIUs en TC2 no coincide con el valor esperado.")
    else:
        st.error("Las columnas esperadas no están en TC2.")
