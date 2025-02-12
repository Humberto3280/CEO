import pandas as pd
import streamlit as st

st.title("Informe tarifas")

# Subir archivos
uploaded_tc1 = st.file_uploader("Subir TC1.csv", type=["csv"])
uploaded_tc2 = st.file_uploader("Subir TC2.xlsx", type=["xlsx"])
uploaded_ap = st.file_uploader("Subir AP.xlsx", type=["xlsx"])
uploaded_divipola = st.file_uploader("Subir Dane_Divipola_08_2012.xlsx", type=["xlsx"])
uploaded_bitacora = st.file_uploader("Subir Bitacora.xlsx", type=["xlsx"])

if uploaded_tc1 and uploaded_tc2 and uploaded_ap and uploaded_divipola and uploaded_bitacora:
    # Leer archivos
    tc1 = pd.read_csv(uploaded_tc1)
    tc2 = pd.read_excel(uploaded_tc2)
    
    def extraer_datos_excel(archivo_entrada, hoja_origen):
        df = pd.read_excel(archivo_entrada, sheet_name=hoja_origen, header=3)
        df = df[~df.iloc[:, 0].astype(str).str.contains("Total general", na=False)]
        return df
    
    archivo_ap = extraer_datos_excel(uploaded_ap, "TABLA TARIFAS")
    davipola = pd.read_excel(uploaded_divipola)
    bitacora = pd.read_excel(uploaded_bitacora)

    # Validación de que el archivo AP se leyó correctamente
    st.write("### Columnas en AP:", archivo_ap.columns.tolist())
    
    # Aplicar filtro por ID_COMERCIALIZADOR = 23442
    id_comercializador_col = 'ID COMERCIALIZADOR'  # Ajustar si es necesario
    niu_col = 'NIU'  # Ajustar si es necesario
    
    if id_comercializador_col in tc1.columns and niu_col in tc1.columns:
        tc1_filtrado = tc1[tc1[id_comercializador_col] == 23442]
        count_nius_tc1 = tc1_filtrado[niu_col].nunique()
        st.write(f"Número de NIUs en TC1 después de filtrar: {count_nius_tc1}")
    else:
        st.error("Las columnas esperadas no están en TC1. Verifica los nombres de las columnas.")

    # Validación de TC2
    if niu_col in tc2.columns:
        tc2_sin_duplicados = tc2.drop_duplicates(subset=niu_col)
        count_nius_tc2 = tc2_sin_duplicados[niu_col].nunique()
        st.write(f"Número de NIUs en TC2 después de eliminar duplicados: {count_nius_tc2}")
        
        # Comparación entre TC1 y TC2
        if count_nius_tc1 == count_nius_tc2 - 1:
            st.success("El número de NIUs en TC2 coincide con el valor esperado.")
        else:
            st.error("El número de NIUs en TC2 no coincide con el valor esperado. Verifica los archivos.")
    else:
        st.error("Las columnas esperadas no están en TC2. Verifica los nombres de las columnas.")
