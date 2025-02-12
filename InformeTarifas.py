import streamlit as st
import pandas as pd

def extraer_datos_excel(archivo_entrada, hoja_origen):
    df = pd.read_excel(archivo_entrada, sheet_name=hoja_origen, header=3)
    df = df[~df.iloc[:, 0].astype(str).str.contains("Total general", na=False)]
    return df

st.title("Carga de archivos para procesamiento")

# Subida de TC1.csv
tc1_file = st.file_uploader("Subir TC1.csv", type=["csv"])
if tc1_file is not None:
    tc1 = pd.read_csv(tc1_file)
    st.write("Vista previa de TC1:")
    st.dataframe(tc1.head())

# Subida de TC2.xlsx
tc2_file = st.file_uploader("Subir TC2.xlsx", type=["xlsx"])
if tc2_file is not None:
    tc2 = pd.read_excel(tc2_file)
    st.write("Vista previa de TC2:")
    st.dataframe(tc2.head())

# Subida de AP.xlsx
ap_file = st.file_uploader("Subir AP.xlsx", type=["xlsx"])
if ap_file is not None:
    archivo_ap = extraer_datos_excel(ap_file, "TABLA TARIFAS")
    st.write("Vista previa de AP:")
    st.dataframe(archivo_ap.head())

# Subida de Dane_Divipola_08_2012.xlsx
divipola_file = st.file_uploader("Subir Dane_Divipola_08_2012.xlsx", type=["xlsx"])
if divipola_file is not None:
    divipola = pd.read_excel(divipola_file)
    st.write("Vista previa de Divipola:")
    st.dataframe(divipola.head())

# Subida de Bitacora.xlsx
bitacora_file = st.file_uploader("Subir Bitacora.xlsx", type=["xlsx"])
if bitacora_file is not None:
    bitacora = pd.read_excel(bitacora_file)
    st.write("Vista previa de Bitácora:")
    st.dataframe(bitacora.head())
