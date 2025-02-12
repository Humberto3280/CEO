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

        st.write("### Columnas en AP:", ap.columns.tolist())

        # Aplicar filtro en TC1
        id_comercializador_col = 'ID COMERCIALIZADOR'
        niu_col = 'NIU'

        if id_comercializador_col in tc1.columns and niu_col in tc1.columns:
            tc1_filtrado = tc1[tc1[id_comercializador_col] == 23442]
            count_nius_tc1 = tc1_filtrado[niu_col].nunique()
            st.write(f"Número de NIUs en TC1 después de filtrar: {count_nius_tc1}")
        else:
            st.error("Las columnas esperadas no están en TC1.")

        # Validación de TC2
        if niu_col in tc2.columns:
            tc2_sin_duplicados = tc2.drop_duplicates(subset=niu_col)
            count_nius_tc2 = tc2_sin_duplicados[niu_col].nunique()
            st.write(f"Número de NIUs en TC2 después de eliminar duplicados: {count_nius_tc2}")

            # Comparación directa
            if count_nius_tc1 == count_nius_tc2 - 1:
                st.success("El número de NIUs en TC2 coincide con el valor esperado.")
            else:
                st.error("El número de NIUs en TC2 no coincide con el valor esperado. Verifica los archivos.")
        else:
            st.error("Las columnas esperadas no están en TC2. Verifica los nombres de las columnas.")

    except Exception as e:
        st.error(f"Ocurrió un error al procesar los archivos: {e}")

    # Verificar que las columnas necesarias existen en TC1
    required_columns = ['NIU', 'ESTRATO', 'CODIGO DANE (NIU)', 'UBICACION', 
                        'NIVEL DE TENSION', 'PORCENTAJE PROPIEDAD DEL ACTIVO', 'CODIGO AREA ESPECIAL']

    if all(col in tc1_filtrado.columns for col in required_columns):
        # Crear la nueva tabla con las columnas requeridas
        Tarifas = tc1_filtrado[required_columns].copy()
        Tarifas.columns = ['NIU', 'ESTRATO', 'DIVIPOLA', 'UBICACION', 'NIVEL DE TENSION', 'CARGA DE INVERSION', 'ZE']

        # Modificar valores en 'ESTRATO'
        Tarifas['ESTRATO'] = Tarifas['ESTRATO'].replace({7: 'I', 8: 'C', 9: 'O', 11: 'AP'})
        
        # Modificar valores en 'UBICACION'
        Tarifas['UBICACION'] = Tarifas['UBICACION'].replace({1: 'R', 2: 'U'})
        
        # Modificar valores de "CARGA DE INVERSION"
        Tarifas['CARGA DE INVERSION'] = Tarifas['CARGA DE INVERSION'].replace({101: 0})

        # Mostrar la tabla en la app
        st.write("### Tabla de Tarifas Generada:")
        st.dataframe(Tarifas)
    else:
        st.error("❌ No se encontraron todas las columnas necesarias en TC1. Verifica el archivo.")

# Botón para limpiar la app
if st.button("Limpiar"):
    st.experimental_rerun()
