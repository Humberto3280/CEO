import pandas as pd
import streamlit as st

st.title("Informe tarifas")

# Subir archivos
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

if all(file_dict.values()):
    try:
        # Leer archivos
        tc1 = pd.read_csv(file_dict["TC1"])
        tc2 = pd.read_excel(file_dict["TC2"])
        ap = pd.read_excel(file_dict["AP"], sheet_name="TABLA TARIFAS", header=3)
        ap = ap[~ap.iloc[:, 0].astype(str).str.contains("Total general", na=False)]
        divipola = pd.read_excel(file_dict["DIVIPOLA"])
        bitacora = pd.read_excel(file_dict["BITACORA"])

        # Filtro en TC1
        if 'ID COMERCIALIZADOR' in tc1.columns and 'NIU' in tc1.columns:
            tc1_filtrado = tc1[tc1['ID COMERCIALIZADOR'] == 23442]
            count_nius_tc1 = tc1_filtrado['NIU'].nunique()
            st.write(f"Número de NIUs en TC1 después de filtrar: {count_nius_tc1}")
        else:
            st.error("Las columnas esperadas no están en TC1.")

        # Validación en TC2
        if 'NIU' in tc2.columns:
            tc2_sin_duplicados = tc2.drop_duplicates(subset='NIU')
            count_nius_tc2 = tc2_sin_duplicados['NIU'].nunique()
            st.write(f"Número de NIUs en TC2 después de eliminar duplicados: {count_nius_tc2}")

            if count_nius_tc1 == count_nius_tc2 - 1:
                st.success("✅ El número de NIUs en TC2 coincide con el valor esperado.")
            else:
                st.error("❌ El número de NIUs en TC2 no coincide con el valor esperado. Verifica los archivos.")

            if 'Tipo de Tarifa' in tc2.columns:
                duplicated_nius = tc2[tc2.duplicated(subset='NIU', keep=False)]
                different_tarifas = duplicated_nius.groupby('NIU')['Tipo de Tarifa'].nunique()
                nius_with_different_tarifas = different_tarifas[different_tarifas > 1]
                if not nius_with_different_tarifas.empty:
                    st.error("❌ Hay NIUs con diferentes tipos de tarifa. Revisa los datos.")
                    st.dataframe(duplicated_nius[duplicated_nius['NIU'].isin(nius_with_different_tarifas.index)])
                else:
                    st.success("✅ Todos los NIUs tienen el mismo tipo de tarifa.")
        else:
            st.error("❌ Las columnas esperadas no están en TC2.")

        # Generación de Tabla de Tarifas
        required_columns = ['NIU', 'ESTRATO', 'CODIGO DANE (NIU)', 'UBICACION', 'NIVEL DE TENSION', 'PORCENTAJE PROPIEDAD DEL ACTIVO', 'CODIGO AREA ESPECIAL']

        if all(col in tc1_filtrado.columns for col in required_columns):
            Tarifas = tc1_filtrado[required_columns].copy()
            Tarifas.columns = ['NIU', 'ESTRATO', 'DIVIPOLA', 'UBICACION', 'NIVEL DE TENSION', 'CARGA DE INVERSION', 'ZE']
            Tarifas.replace({'ESTRATO': {7: 'I', 8: 'C', 9: 'O', 11: 'AP'}, 'UBICACION': {1: 'R', 2: 'U'}, 'CARGA DE INVERSION': {101: 0}}, inplace=True)

            # Crear tabla dinámica
            pivot_table = pd.pivot_table(tc2, index='NIU', values=['Consumo Usuario (kWh)', 'Valor Facturación por Consumo Usuario'], aggfunc='sum')
            pivot_table.reset_index(inplace=True)
            tblDinamicaTc2 = pivot_table[['NIU', 'Consumo Usuario (kWh)', 'Valor Facturación por Consumo Usuario']]

            # Convertir a string y eliminar espacios
            for df in [Tarifas, tblDinamicaTc2, tc2_sin_duplicados]:
                df['NIU'] = df['NIU'].astype(str).str.strip()

            # Añadir 'Tipo de Tarifa'
            tblDinamicaTc2 = tblDinamicaTc2.merge(tc2_sin_duplicados[['NIU', 'Tipo de Tarifa']], on='NIU', how='left')
            Tarifas = Tarifas.merge(tblDinamicaTc2, on='NIU', how='left')
            Tarifas['Tipo de Tarifa'] = Tarifas['Tipo de Tarifa'].replace({1: 'R', 2: 'NR'})

            # Reorganizar y renombrar columnas
            Tarifas = Tarifas[['NIU', 'ESTRATO', 'Tipo de Tarifa', 'Consumo Usuario (kWh)',
                               'Valor Facturación por Consumo Usuario', 'UBICACION',
                               'DIVIPOLA', 'NIVEL DE TENSION', 'CARGA DE INVERSION', 'ZE']]
            Tarifas.rename(columns={'Tipo de Tarifa': 'TIPO TARIFA', 'Consumo Usuario (kWh)': 'CONSUMO',
                                    'Valor Facturación por Consumo Usuario': 'FACTURACION CONSUMO',
                                    'DIVIPOLA': 'DAVIPOLA'}, inplace=True)

            st.write("### Tabla de Tarifas Generada:")
            st.dataframe(Tarifas)
        else:
            st.error("❌ No se encontraron todas las columnas necesarias en TC1. Verifica el archivo.")

    except Exception as e:
        st.error(f"Ocurrió un error al procesar los archivos: {e}")

if st.button("Limpiar"):
    st.experimental_rerun()
