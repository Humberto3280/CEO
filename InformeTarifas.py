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
        # Ahora se traen los nombre de los municipios según correspondan al código DAVIPOLA

        # Realiza la combinación de los DataFrames
        divipola.columns = divipola.columns.str.strip()
        Tarifas = Tarifas.merge(divipola[['Código DIVIPOLA', 'Nombre Municipio']],
                                left_on='DIVIPOLA', right_on='Código DIVIPOLA', how='left')

        # Renombra la nueva columna con el nombre del municipio
        Tarifas = Tarifas.rename(columns={'Nombre Municipio': 'Municipio'})

        # Elimina la columna 'Código DIVIPOLA' si no es necesaria
        Tarifas = Tarifas.drop(columns=['Código DIVIPOLA'])

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
        
        # **Eliminación de NIUs que contienen 'CAL'**
        Tarifas['NIU'] = Tarifas['NIU'].astype(str).fillna('') 
        Tarifas = Tarifas[~Tarifas['NIU'].str.contains('CAL')]

        # Convertir los elementos de la columna productos a str
        ap['producto'] = ap['producto'].astype(str).str.strip()

        # Validar que el archivo AP no contenga productos vacíos
        if ap['producto'].eq('').any():
            st.error("❌ El archivo AP contiene productos vacíos. Por favor, corrige los datos.")
            st.stop()  # Detiene la ejecución del script en Streamlit
        else:
            st.success("✅ Validación exitosa: No hay productos vacíos en el archivo AP.")

        # Modificar valores en 'Tipo_tarifa'
        ap['tipo de tarifa'] = ap['tipo de tarifa'].replace({1: 'R', 2: 'NR'})

        # Modificar valores en 'ESTRATO'
        ap['estrato'] = ap['estrato'].replace({11: 'AP'})

        # Filtrar archivo AP por estrato='AP'
        ap = ap[ap['estrato'] == 'AP']


        # Filtrar Tarifas sin CALP por estrato 'AP'
        tarifas_val = Tarifas[Tarifas['ESTRATO'] == 'AP']

        # Convertir las columnas NIU a conjuntos
        nius_archivo_ap = set(ap['producto'].astype(str).str.strip())
        nius_tarifas_ap = set(tarifas_val['NIU'].astype(str).str.strip())

        # Validar que todos los NIU de tarifas_ap_filtrado estén en archivo_ap_filtrado
        niu_faltantes_en_ap = nius_tarifas_ap - nius_archivo_ap

        # Validar que todos los NIU de archivo_ap_filtrado estén en tarifas_ap_filtrado
        niu_faltantes_en_tarifas = nius_archivo_ap - nius_tarifas_ap

        # Mostrar errores en Streamlit si hay diferencias
        if niu_faltantes_en_ap:
            st.error(f"❌ NIU en Tarifas (AP) que no están en archivo AP: {niu_faltantes_en_ap}")
            st.stop()  # Detiene la ejecución del script en Streamlit
        if niu_faltantes_en_tarifas:
            st.error(f"❌ NIU en archivo AP (AP) que no están en Tarifas: {niu_faltantes_en_tarifas}")
            st.stop()  # Detiene la ejecución del script en Streamlit

        # Si todo está bien, mostrar éxito
        if not niu_faltantes_en_ap and not niu_faltantes_en_tarifas:
            st.success("✅ Validación exitosa: se puede hacer cruce de AP con tarifas.")

        # Hacer un merge entre Tarifas sin cal y archivo ap basándose en NIU y producto
        Tarifas = Tarifas.merge(
            ap[['producto', 'Suma de consumo', 'Suma de facturacion consumo', 'tipo de tarifa']],
            left_on='NIU',    right_on='producto',
            how='left'
        )

        # Actualizar las columnas CONSUMO, FACTURACION CONSUMO y TIPO TARIFA solo si los valores son mayores a cero
        Tarifas.loc[Tarifas['Suma de consumo'] > 0, 'CONSUMO'] = Tarifas['Suma de consumo']
        Tarifas.loc[(Tarifas['Suma de facturacion consumo'].notna()) & (Tarifas['Suma de facturacion consumo'] != 0), 'FACTURACION CONSUMO'] = Tarifas['Suma de facturacion consumo']
        Tarifas.loc[Tarifas['tipo de tarifa'].notna(), 'TIPO TARIFA'] = Tarifas['tipo de tarifa']

        # Eliminar las columnas adicionales si no son necesarias
        Tarifas = Tarifas.drop(columns=['producto', 'Suma de consumo', 'Suma de facturacion consumo', 'tipo de tarifa'])

        import numpy as np

        # Redondeo de las columnas Consumo y fact consumo
        Tarifas['CONSUMO'] = np.floor(Tarifas['CONSUMO'] + 0.5).astype(int)
        Tarifas['FACTURACION CONSUMO'] = np.floor(Tarifas['FACTURACION CONSUMO'] + 0.5).astype(int)

        # Validación de valores vacíos en la columna NIU
        if Tarifas['NIU'].eq('').any():
            st.error("Error: La columna NIU tiene valores vacíos. Revisar los archivos TC1 y TC2.")
            st.stop()
        else:
            st.success("✅ Validación exitosa: La columna NIU no tiene valores vacíos.")

        # Validación de valores negativos en la columna CONSUMO
        if (Tarifas['CONSUMO'] < 0).any():
            st.error("Error: La columna CONSUMO tiene valores negativos. Verifica los datos.")
            st.stop()
        else:
            st.success("✅ Validación exitosa: La columna CONSUMO no tiene valores negativos.")

        # Validación de valores negativos en la columna FACTURACION CONSUMO
        if (Tarifas['FACTURACION CONSUMO'] < 0).any():
            st.error("Error: La columna FACTURACION CONSUMO tiene valores negativos. Verifica los datos.")
            st.stop()
        else:
            st.success("✅ Validación exitosa: La columna FACTURACION CONSUMO no tiene valores negativos.")

        # Validación de la regla: Si CONSUMO es 0, FACTURACION CONSUMO también debe ser 0
        if ((Tarifas['CONSUMO'] == 0) & (Tarifas['FACTURACION CONSUMO'] != 0)).any():
            st.error("Error: Si CONSUMO es 0, FACTURACION CONSUMO también debe ser 0. Hay inconsistencias en los datos.")
            st.stop()
        else:
            st.success("✅ Validación exitosa: No hay inconsistencias entre CONSUMO y FACTURACION CONSUMO.")

        # Validación de valores nulos en todo el DataFrame
        if Tarifas.isnull().any().any():
            st.error("Error: El DataFrame contiene valores nulos. Verifica las columnas y corrige los datos.")
            st.stop()
        else:
            st.success("✅ Validación exitosa: El DataFrame no tiene valores nulos.")

        # Validación Bitácora
        bitacora['Producto'] = bitacora['Producto'].astype(str)
        bitacora = bitacora[bitacora['Tipo Frontera'] == 'Tipo No Regulado']
        ultima_columna_bitacora = bitacora.columns[-1]

        resultado = pd.merge(
            bitacora[['Producto', ultima_columna_bitacora]],
            Tarifas[['NIU', 'CONSUMO']],
            left_on='Producto', right_on='NIU',
            how='left'
        )

        resultado['Diferencia'] = abs(resultado[ultima_columna_bitacora] - resultado['CONSUMO'])
        resultado['Es Diferente'] = resultado['Diferencia'] > 1
        diferencias = resultado[resultado['Es Diferente']][['NIU', 'CONSUMO', ultima_columna_bitacora]]

        # Mostrar tabla en diferencias
        st.write("### Tabla de diferencias:")
        st.dataframe(diferencias)

        # Mostrar tabla en Streamlit
        st.write("### Tabla de Tarifas Generada:")
        st.dataframe(Tarifas)

        #Creación de informe DANE

        # Filtrar DaNE por Ubicacion='U' y Municipio='Popayán'
        informeDane = Tarifas[(Tarifas['UBICACION'] == 'U') & (Tarifas['MUNICIPIO'] == 'POPAYAN')]

        # Crear la tabla dinámica
        pivot_table = informeDane.pivot_table(
            index='ESTRATO',  # Agrupar por la columna 'ESTRATO'
            values=['NIU', 'CONSUMO', 'FACTURACION CONSUMO'],  # Columnas a agregar
            aggfunc={'NIU': 'count', 'CONSUMO': 'sum', 'FACTURACION CONSUMO': 'sum'}  # Funciones de agregación
        )

        # Renombrar las columnas para mayor claridad
        pivot_table.rename(columns={'NIU': 'CONTEO_NIU', 'CONSUMO': 'SUMA_CONSUMO', 'FACTURACION CONSUMO': 'SUMA_FACTURACION'}, inplace=True)

        # Crear un nuevo DataFrame con el resultado
        informeDaneVf = pivot_table.reset_index()

        # Mostrar tabla en Streamlit
        st.write("### Tabla de informe DANE:")
        st.dataframe(informeDaneVf)

        #Descargar los archivos
        # Mostrar tabla en Streamlit
        st.write("Descargar los informes")
        import io
        import zipfile

        # Función para convertir DataFrame en CSV y agregarlo a un archivo ZIP
        def create_zip():
            zip_buffer = io.BytesIO()
    
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                # Guardar Tarifas.csv
                tarifas_buffer = io.StringIO()
                Tarifas.to_csv(tarifas_buffer, index=False, encoding='utf-8-sig')
                zip_file.writestr("Tarifas.csv", tarifas_buffer.getvalue())

                # Guardar Informe_DANE.csv
                dane_buffer = io.StringIO()
                informeDaneVf.to_csv(dane_buffer, index=False, encoding='utf-8-sig')
                zip_file.writestr("Informe_DANE.csv", dane_buffer.getvalue())

                # Guardar Diferencias_Tarifas_Bitacora.csv
                diferencias_buffer = io.StringIO()
                diferencias.to_csv(diferencias_buffer, index=False, encoding='utf-8-sig')
                zip_file.writestr("Diferencias_Tarifas_Bitacora.csv", diferencias_buffer.getvalue())

            zip_buffer.seek(0)
            return zip_buffer

        # Botón para descargar los 3 archivos en un ZIP
        st.download_button(
            label="📥 Descargar Tarifas, Informe DANE y Diferencias",
            data=create_zip(),
            file_name="Reportes_Tarifas.zip",
            mime="application/zip"
        )
        st.stop()

    else:
        st.error("❌ No se encontraron todas las columnas necesarias en TC1. Verifica el archivo.")

# **Botón para limpiar la app**
if st.button("Limpiar"):
    st.rerun()
