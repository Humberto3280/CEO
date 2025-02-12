import pandas as pd
import streamlit as st

st.title("Carga y procesamiento de archivos")

# Subir archivos (un solo botón para todos)
uploaded_files = st.file_uploader(
    "Subir archivos (TC1.csv, TC2.xlsx, AP.xlsx, Divipola.xlsx, Bitacora.xlsx)", 
    type=["csv", "xlsx"], 
    accept_multiple_files=True
)

# Diccionario para almacenar los archivos subidos
file_dict = {"TC1": None, "TC2": None, "AP": None, "DIVIPOLA": None, "BITACORA": None}

# Asociar cada archivo subido a su clave correspondiente
for file in uploaded_files:
    if "TC1" in file.name.upper():
        file_dict["TC1"] = file
    elif "TC2" in file.name.upper():
        file_dict["TC2"] = file
    elif "AP" in file.name.upper():
        file_dict["AP"] = file
    elif "DIVIPOLA" in file.name.upper():
        file_dict["DIVIPOLA"] = file
    elif "BITACORA" in file.name.upper():
        file_dict["BITACORA"] = file

# Verificar si ya hemos cargado los archivos antes
if "tc1" not in st.session_state and file_dict["TC1"]:
    st.session_state.tc1 = pd.read_csv(file_dict["TC1"])

if "tc2" not in st.session_state and file_dict["TC2"]:
    st.session_state.tc2 = pd.read_excel(file_dict["TC2"])

if "archivo_ap" not in st.session_state and file_dict["AP"]:
    def extraer_datos_excel(archivo_entrada, hoja_origen):
        df = pd.read_excel(archivo_entrada, sheet_name=hoja_origen, header=3)
        df = df[~df.iloc[:, 0].astype(str).str.contains("Total general", na=False)]
        return df
    st.session_state.archivo_ap = extraer_datos_excel(file_dict["AP"], "TABLA TARIFAS")

if "davipola" not in st.session_state and file_dict["DIVIPOLA"]:
    st.session_state.davipola = pd.read_excel(file_dict["DIVIPOLA"])

if "bitacora" not in st.session_state and file_dict["BITACORA"]:
    st.session_state.bitacora = pd.read_excel(file_dict["BITACORA"])

# Si todos los archivos están cargados, proceder con el análisis
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

# Botón para reiniciar la app
if st.button("Hacer nuevo informe"):
    st.session_state.clear()
    st.experimental_rerun()
