import pandas as pd
import streamlit as st

st.title("Informe tarifas")

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

# Verificar si todos los archivos han sido cargados
if all(file_dict.values()):
    try:
        # Leer archivos
        tc1 = pd.read_csv(file_dict["TC1"])
        tc2 = pd.read_excel(file_dict["TC2"])
        ap = pd.read_excel(file_dict["AP"], sheet_name="TABLA TARIFAS", header=3)
        ap = ap[~ap.iloc[:, 0].astype(str).str.contains("Total general", na=False)]
        divipola = pd.read_excel(file_dict["DIVIPOLA"])
        bitacora = pd.read_excel(file_dict["BITACORA"])

        # Aplicar filtro en TC1
        id_comercializador_col = 'ID COMERCIALIZADOR'
        niu_col = 'NIU'

        if id_comercializador_col in tc1.columns and niu_col in tc1.columns:
            tc1_filtrado = tc1[tc1[id_comercializador_col] == 23442]
            count_nius_tc1 = tc1_filtrado[niu_col].nunique()
            st.write(f"Número de NIUs en TC1 después de filtrar: {count_nius_tc1}")
        else:
            st.error("Las columnas esperadas no están en TC1.")

        # **Validación de TC2 (NIUs y Tarifas)**
        if niu_col in tc2.columns:

            # Contar NIUs después de eliminar duplicados
            tc2_sin_duplicados = tc2.drop_duplicates(subset=niu_col)
            count_nius_tc2 = tc2_sin_duplicados[niu_col].nunique()
            st.write(f"Número de NIUs en TC2 después de eliminar duplicados: {count_nius_tc2}")

            # Comparación de NIUs TC1 vs TC2
            if count_nius_tc1 == count_nius_tc2 - 1:
                st.success("✅ El número de NIUs en TC2 coincide con el valor esperado.")
            else:
                st.error("❌ El número de NIUs en TC2 no coincide con el valor esperado. Verifica los archivos.")
            # Validar NIUs duplicados con diferentes tarifas
            if 'Tipo de Tarifa' in tc2.columns:
                duplicated_nius = tc2[tc2.duplicated(subset='NIU', keep=False)]
                different_tarifas = duplicated_nius.groupby('NIU')['Tipo de Tarifa'].nunique()
                nius_with_different_tarifas = different_tarifas[different_tarifas > 1]
                if not nius_with_different_tarifas.empty:
                    st.error("❌ Hay NIUs con diferentes tipos de tarifa. Revisa los datos.")
                    niu_different_tarifa_df = duplicated_nius[duplicated_nius['NIU'].isin(nius_with_different_tarifas.index)]
                    st.write("### NIUs con tipo de tarifa diferente:")
                    st.dataframe(niu_different_tarifa_df[['NIU', 'Tipo de Tarifa']])
                else:
                    st.success("✅ Todos los NIUs tienen el mismo tipo de tarifa.")

        else:
            st.error("❌ Las columnas esperadas no están en TC2.")

    except Exception as e:
        st.error(f"Ocurrió un error al procesar los archivos: {e}")

    # **Generación de Tabla de Tarifas**
    required_columns = ['NIU', 'ESTRATO', 'CODIGO DANE (NIU)', 'UBICACION', 
                        'NIVEL DE TENSION', 'PORCENTAJE PROPIEDAD DEL ACTIVO', 'CODIGO AREA ESPECIAL']

    if all(col in tc1_filtrado.columns for col in required_columns):
        Tarifas = tc1_filtrado[required_columns].copy()
        Tarifas.columns = ['NIU', 'ESTRATO', 'DIVIPOLA', 'UBICACION', 'NIVEL DE TENSION', 'CARGA DE INVERSION', 'ZE']

        # Modificar valores en columnas
        Tarifas['ESTRATO'] = Tarifas['ESTRATO'].replace({7: 'I', 8: 'C', 9: 'O', 11: 'AP'})
        Tarifas['UBICACION'] = Tarifas['UBICACION'].replace({1: 'R', 2: 'U'})
        Tarifas['CARGA DE INVERSION'] = Tarifas['CARGA DE INVERSION'].replace({101: 0})

        # Crear la tabla dinámica sumando los valores
        pivot_table = pd.pivot_table(tc2, index='NIU', values=['Consumo Usuario (kWh)', 'Valor Facturación por Consumo Usuario'], aggfunc='sum')
        pivot_table.reset_index(inplace=True)
        tblDinamicaTc2 = pivot_table[['NIU', 'Consumo Usuario (kWh)', 'Valor Facturación por Consumo Usuario']]

        # Convertir las columnas NIU a tipo string y eliminar espacios en blanco
        Tarifas['NIU'] = Tarifas['NIU'].astype(str).str.strip()
        tblDinamicaTc2['NIU'] = tblDinamicaTc2['NIU'].astype(str).str.strip()
        tc2_sin_duplicados['NIU'] = tc2_sin_duplicados['NIU'].astype(str).str.strip()

        # Añadir 'Tipo de Tarifa'
        tblDinamicaTc2 = tblDinamicaTc2.merge(tc2_sin_duplicados[['NIU', 'Tipo de Tarifa']], on='NIU', how='left')
        Tarifas = Tarifas.merge(tblDinamicaTc2, on='NIU', how='left')
        Tarifas['Tipo de Tarifa'] = Tarifas['Tipo de Tarifa'].replace({1: 'R', 2: 'NR'})
        # Reorganizar las columnas en el orden deseado
        Tarifas = Tarifas[['NIU', 'ESTRATO', 'Tipo de Tarifa', 'Consumo Usuario (kWh)',
                             'Valor Facturación por Consumo Usuario', 'UBICACION',
                             'DIVIPOLA', 'Municipio', 'NIVEL DE TENSION',
                             'CARGA DE INVERSION', 'ZE']]

        # Renombrar las columnas según los nuevos nombres proporcionados
        Tarifas = Tarifas.rename(columns={
            'Tipo de Tarifa': 'TIPO TARIFA',
            'Consumo Usuario (kWh)': 'CONSUMO',
            'Valor Facturación por Consumo Usuario': 'FACTURACION CONSUMO',
            'Municipio': 'MUNICIPIO',
            'DIVIPOLA': 'DAVIPOLA'
        })
        # **Añadir el Cliente de otro mercado**
        niu_filtrado = tc2[(tc2['NIU'] == 898352932) | (tc2['NIU'] == 18124198)]
        consumo_usuario = niu_filtrado['Consumo Usuario (kWh)'].values[0]
        valor_facturacion = niu_filtrado['Valor Facturación por Consumo Usuario'].values[0]
        nueva_fila = pd.DataFrame({
            'NIU': [898352932],
            'ESTRATO': ['I'],
            'TIPO TARIFA': ['NR'],
            'CONSUMO': [consumo_usuario],
            'FACTURACION CONSUMO': [valor_facturacion],
            'UBICACION': ['U'],
            'DAVIPOLA': [13001000],
            'MUNICIPIO': ['CARTAGENA'],
            'NIVEL DE TENSION': [2],
            'CARGA DE INVERSION': [0],
            'ZE': [0]
        })
        Tarifas = pd.concat([Tarifas, nueva_fila], ignore_index=True)
        # Mostrar tabla en Streamlit
        st.write("### Tabla de Tarifas Generada:")
        st.dataframe(Tarifas)
    else:
        st.error("❌ No se encontraron todas las columnas necesarias en TC1. Verifica el archivo.")

# **Botón para limpiar la app**
if st.button("Limpiar"):
    st.rerun()
