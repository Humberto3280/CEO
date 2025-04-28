import pandas as pd
import streamlit as st
import io
import zipfile
import xlsxwriter
from typing import Any, Dict

st.title("Generación de informes (tarifas e informe Dane)")

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
        # Leer archivos (se especifica low_memory para evitar advertencias)
        tc1 = pd.read_csv(file_dict["TC1"], low_memory=False)
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
            tc2_sin_duplicados.loc[:, 'NIU'] = tc2_sin_duplicados['NIU'].astype(str).str.strip()
            count_nius_tc2 = tc2_sin_duplicados[niu_col].nunique()
            st.write(f"Número de NIUs en TC2 después de eliminar duplicados: {count_nius_tc2}")

            # Comparación de NIUs TC1 vs TC2
            if count_nius_tc1 == count_nius_tc2 - 1:
                st.success("✅ El número de NIUs en TC2 coincide con el valor esperado.")
            else:
                st.error("❌ El número de NIUs en TC2 no coincide con el valor esperado. Verifica los archivos.")
            # Validar NIUs duplicados con diferentes tarifas
            if 'TIPO DE TARIFA' in tc2.columns:
                duplicated_nius = tc2[tc2.duplicated(subset='NIU', keep=False)]
                different_tarifas = duplicated_nius.groupby('NIU')['TIPO DE TARIFA'].nunique()
                nius_with_different_tarifas = different_tarifas[different_tarifas > 1]
                if not nius_with_different_tarifas.empty:
                    st.error("❌ Hay NIUs con diferentes tipos de tarifa. Revisa los datos.")
                    niu_different_tarifa_df = duplicated_nius[duplicated_nius['NIU'].isin(nius_with_different_tarifas.index)]
                    st.write("### NIUs con tipo de tarifa diferente:")
                    st.dataframe(niu_different_tarifa_df[['NIU', 'TIPO DE TARIFA']])
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
        # Combinar con divipola para traer nombre de municipio
        divipola.columns = divipola.columns.str.strip()
        Tarifas = Tarifas.merge(divipola[['Código DIVIPOLA', 'Nombre Municipio']],
                                left_on='DIVIPOLA', right_on='Código DIVIPOLA', how='left')
        Tarifas = Tarifas.rename(columns={'Nombre Municipio': 'Municipio'})
        Tarifas = Tarifas.drop(columns=['Código DIVIPOLA'])

        # Crear tabla dinámica a partir de TC2
        pivot_table = pd.pivot_table(tc2, index='NIU', values=['CONSUMO USUARIO (KWH)', 'VALOR FACTURACION POR CONSUMO USUARIO ()'], aggfunc='sum')
        pivot_table.reset_index(inplace=True)
        tblDinamicaTc2 = pivot_table[['NIU', 'CONSUMO USUARIO (KWH)', 'VALOR FACTURACION POR CONSUMO USUARIO ()']]

        # Convertir columnas NIU a string y limpiar espacios
        Tarifas['NIU'] = Tarifas['NIU'].astype(str).str.strip()
        tblDinamicaTc2['NIU'] = tblDinamicaTc2['NIU'].astype(str).str.strip()
        tc2_sin_duplicados['NIU'] = tc2_sin_duplicados['NIU'].astype(str).str.strip()

        # Añadir 'Tipo de Tarifa'
        tblDinamicaTc2 = tblDinamicaTc2.merge(tc2_sin_duplicados[['NIU', 'TIPO DE TARIFA']], on='NIU', how='left')
        Tarifas = Tarifas.merge(tblDinamicaTc2, on='NIU', how='left')
        Tarifas['TIPO DE TARIFA'] = Tarifas['TIPO DE TARIFA'].replace({1: 'R', 2: 'NR'})
        
        Tarifas = Tarifas[['NIU', 'ESTRATO', 'TIPO DE TARIFA', 'CONSUMO USUARIO (KWH)',
                             'VALOR FACTURACION POR CONSUMO USUARIO ()', 'UBICACION',
                             'DIVIPOLA', 'Municipio', 'NIVEL DE TENSION',
                             'CARGA DE INVERSION', 'ZE']]
        Tarifas = Tarifas.rename(columns={
            'TIPO DE TARIFA': 'TIPO TARIFA',
            'CONSUMO USUARIO (KWH)': 'CONSUMO',
            'VALOR FACTURACION POR CONSUMO USUARIO ()': 'FACTURACION CONSUMO',
            'Municipio': 'MUNICIPIO',
            'DIVIPOLA': 'DAVIPOLA'
        })
        # Añadir Cliente de otro mercado
        niu_filtrado = tc2[(tc2['NIU'] == 898352932) | (tc2['NIU'] == 18124198)]
        consumo_usuario = niu_filtrado['CONSUMO USUARIO (KWH)'].values[0]
        valor_facturacion = niu_filtrado['VALOR FACTURACION POR CONSUMO USUARIO ()'].values[0]
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
        
        # Eliminación de NIUs que contienen 'CAL'
        Tarifas['NIU'] = Tarifas['NIU'].astype(str).fillna('')
        Tarifas = Tarifas[~Tarifas['NIU'].str.contains('CAL')]
        
        # Procesar archivo AP
        ap['producto'] = ap['producto'].astype(str).str.strip()
        if ap['producto'].eq('').any():
            st.error("❌ El archivo AP contiene productos vacíos. Por favor, corrige los datos.")
            st.stop()
        else:
            st.success("✅ Validación exitosa: No hay productos vacíos en el archivo AP.")
        ap['tipo de tarifa'] = ap['tipo de tarifa'].replace({1: 'R', 2: 'NR'})
        ap['estrato'] = ap['estrato'].replace({11: 'AP'})
        ap = ap[ap['estrato'] == 'AP']

        tarifas_val = Tarifas[Tarifas['ESTRATO'] == 'AP']
        nius_archivo_ap = set(ap['producto'].astype(str).str.strip())
        nius_tarifas_ap = set(tarifas_val['NIU'].astype(str).str.strip())
        niu_faltantes_en_ap = nius_tarifas_ap - nius_archivo_ap
        niu_faltantes_en_tarifas = nius_archivo_ap - nius_tarifas_ap
        if niu_faltantes_en_ap:
            st.error(f"❌ NIU en Tarifas (AP) que no están en archivo AP: {niu_faltantes_en_ap}")
            st.stop()
        if niu_faltantes_en_tarifas:
            st.error(f"❌ NIU en archivo AP (AP) que no están en Tarifas: {niu_faltantes_en_tarifas}")
            st.stop()
        if not niu_faltantes_en_ap and not niu_faltantes_en_tarifas:
            st.success("✅ Validación exitosa: se puede hacer cruce de AP con tarifas.")

        Tarifas = Tarifas.merge(
            ap[['producto', 'Suma de consumo', 'Suma de facturacion consumo', 'tipo de tarifa']],
            left_on='NIU', right_on='producto',
            how='left'
        )
        Tarifas.loc[Tarifas['Suma de consumo'] > 0, 'CONSUMO'] = Tarifas['Suma de consumo']
        Tarifas.loc[(Tarifas['Suma de facturacion consumo'].notna()) & (Tarifas['Suma de facturacion consumo'] != 0), 'FACTURACION CONSUMO'] = Tarifas['Suma de facturacion consumo']
        Tarifas.loc[Tarifas['tipo de tarifa'].notna(), 'TIPO TARIFA'] = Tarifas['tipo de tarifa']
        Tarifas = Tarifas.drop(columns=['producto', 'Suma de consumo', 'Suma de facturacion consumo', 'tipo de tarifa'])

        import numpy as np
        problemas = Tarifas[
            Tarifas[['CONSUMO', 'FACTURACION CONSUMO']].isna().any(axis=1) |
            Tarifas[['CONSUMO', 'FACTURACION CONSUMO']].isin([np.inf, -np.inf]).any(axis=1)
        ]
        if not problemas.empty:
            st.error("⚠️ Atención: Se encontraron valores no válidos en las siguientes NIU:")
            st.write(problemas[['NIU', 'CONSUMO', 'FACTURACION CONSUMO']])
            st.stop()
        else:
            Tarifas['CONSUMO'] = np.floor(Tarifas['CONSUMO'] + 0.5).astype(int)
            Tarifas['FACTURACION CONSUMO'] = np.floor(Tarifas['FACTURACION CONSUMO'] + 0.5).astype(int)

        if Tarifas['NIU'].eq('').any():
            st.error("Error: La columna NIU tiene valores vacíos. Revisar los archivos TC1 y TC2.")
            st.stop()
        else:
            st.success("✅ Validación exitosa: La columna NIU no tiene valores vacíos.")

        if (Tarifas['CONSUMO'] < 0).any():
            st.error("Error: La columna CONSUMO tiene valores negativos. Verifica los datos.")
            st.stop()
        else:
            st.success("✅ Validación exitosa: La columna CONSUMO no tiene valores negativos.")

        if (Tarifas['FACTURACION CONSUMO'] < 0).any():
            st.error("Error: La columna FACTURACION CONSUMO tiene valores negativos. Verifica los datos.")
            st.stop()
        else:
            st.success("✅ Validación exitosa: La columna FACTURACION CONSUMO no tiene valores negativos.")

        if ((Tarifas['CONSUMO'] == 0) & (Tarifas['FACTURACION CONSUMO'] != 0)).any():
            st.error("Error: Si CONSUMO es 0, FACTURACION CONSUMO también debe ser 0. Hay inconsistencias en los datos.")
            st.stop()
        else:
            st.success("✅ Validación exitosa: No hay inconsistencias entre CONSUMO y FACTURACION CONSUMO.")

        if Tarifas.isnull().any().any():
            st.error("Error: El DataFrame contiene valores nulos. Verifica las columnas y corrige los datos.")
            st.stop()
        else:
            st.success("✅ Validación exitosa: El DataFrame no tiene valores nulos.")

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
        st.write("### Tabla de diferencias tarifas con bitacora:")
        st.dataframe(diferencias)
        st.write("### Tabla de Tarifas Generada:")
        st.dataframe(Tarifas)

        # Creación de informe DANE
        informeDane = Tarifas[(Tarifas['UBICACION'] == 'U') & (Tarifas['MUNICIPIO'] == 'POPAYAN')]
        pivot_table = pd.pivot_table(
            informeDane, index='ESTRATO',
            values=['NIU', 'CONSUMO', 'FACTURACION CONSUMO'],
            aggfunc={'NIU': 'count', 'CONSUMO': 'sum', 'FACTURACION CONSUMO': 'sum'}
        )
        pivot_table.rename(columns={'NIU': 'CONTEO_NIU', 'CONSUMO': 'SUMA_CONSUMO', 'FACTURACION CONSUMO': 'SUMA_FACTURACION'}, inplace=True)
        informeDaneVf = pivot_table.reset_index()
        st.write("### Tabla de informe DANE:")
        st.dataframe(informeDaneVf)
        Tarifas['ESTRATO'] = Tarifas['ESTRATO'].astype(str)

        # Descargar los archivos
        st.write("Descargar los informes")
        def generar_informes_excel_bytes(Tarifas: pd.DataFrame) -> bytes:
            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            worksheet_consolidado = workbook.add_worksheet("Consolidado")
            worksheet_informe = workbook.add_worksheet("Informe")
            header_format = workbook.add_format({
                'bold': True,
                'align': 'center',
                'valign': 'vcenter',
                'border': 1,
                'bg_color': '#D9D9D9'
            })
            text_format = workbook.add_format({
                'align': 'center',
                'valign': 'vcenter',
                'border': 1
            })
            num_format = workbook.add_format({
                'num_format': '_(* #,##0_);_(* (#,##0);_(* "-"??_);_(@_)',
                'align': 'center',
                'valign': 'vcenter',
                'border': 1
            })
            #############################
            # Hoja "Consolidado"
            #############################
            for col_idx, col_name in enumerate(Tarifas.columns):
                worksheet_consolidado.write(0, col_idx, col_name, header_format)
            for row_idx, row_data in enumerate(Tarifas.values, start=1):
                for col_idx, cell in enumerate(row_data):
                    if isinstance(cell, (int, float)):
                        worksheet_consolidado.write(row_idx, col_idx, cell, num_format)
                    else:
                        worksheet_consolidado.write(row_idx, col_idx, cell, text_format)
            #############################
            # Hoja "Informe"
            #############################
            worksheet_informe.set_column('A:A', 20)
            worksheet_informe.set_column('B:D', 15)
            worksheet_informe.set_column('E:E', 15)
            worksheet_informe.set_column('F:F', 20)
            worksheet_informe.write(0, 0, "", header_format)
            worksheet_informe.merge_range(0, 1, 0, 3, "Número de usuarios", header_format)
            worksheet_informe.write(0, 4, "Consumo", header_format)
            worksheet_informe.write(0, 5, "Facturación consumo", header_format)
            row = 1
            df_nr = Tarifas[Tarifas["TIPO TARIFA"] == "NR"]
            no_regulados_niu = df_nr["NIU"].nunique()
            no_regulados_consumo = df_nr["CONSUMO"].sum()
            no_regulados_facturacion = df_nr["FACTURACION CONSUMO"].sum()
            worksheet_informe.write(row, 0, "No regulados", text_format)
            worksheet_informe.merge_range(row, 1, row, 3, no_regulados_niu, num_format)
            worksheet_informe.write(row, 4, no_regulados_consumo, num_format)
            worksheet_informe.write(row, 5, no_regulados_facturacion, num_format)
            row += 1
            df_r = Tarifas[Tarifas["TIPO TARIFA"] == "R"]
            regulados_niu = df_r["NIU"].nunique()
            regulados_consumo = df_r["CONSUMO"].sum()
            regulados_facturacion = df_r["FACTURACION CONSUMO"].sum()
            worksheet_informe.write(row, 0, "Regulados", text_format)
            worksheet_informe.merge_range(row, 1, row, 3, regulados_niu, num_format)
            worksheet_informe.write(row, 4, regulados_consumo, num_format)
            worksheet_informe.write(row, 5, regulados_facturacion, num_format)
            row += 1
            def escribir_estrato(worksheet, start_row, categoria, rural_usuarios, urbano_usuarios, total_usuarios, consumo, facturacion, text_format, num_format):
                worksheet.merge_range(start_row, 0, start_row+1, 0, categoria, text_format)
                worksheet.write(start_row, 1, "Rural", text_format)
                worksheet.write(start_row, 2, rural_usuarios, num_format)
                worksheet.merge_range(start_row, 3, start_row+1, 3, total_usuarios, num_format)
                worksheet.merge_range(start_row, 4, start_row+1, 4, consumo, num_format)
                worksheet.merge_range(start_row, 5, start_row+1, 5, facturacion, num_format)
                start_row += 1
                worksheet.write(start_row, 1, "Urbano", text_format)
                worksheet.write(start_row, 2, urbano_usuarios, num_format)
                start_row += 1
                return start_row
            estratos_info = [
                {"categoria": "Estrato 1", "estrato": "1"},
                {"categoria": "Estrato 2", "estrato": "2"},
                {"categoria": "Estrato 3", "estrato": "3"},
                {"categoria": "Estrato 4", "estrato": "4"},
                {"categoria": "Estrato 5", "estrato": "5"},
                {"categoria": "Estrato 6", "estrato": "6"},
                {"categoria": "Alumbrado público", "estrato": "AP"},
                {"categoria": "Comercial", "estrato": "C"},
                {"categoria": "Industrial", "estrato": "I"},
                {"categoria": "Oficial", "estrato": "O"}
            ]
            def obtener_metricas_estrato(df, estrato_value):
                df_estrato = df[df["ESTRATO"] == estrato_value]
                total_usuarios = df_estrato["NIU"].nunique()
                consumo = df_estrato["CONSUMO"].sum()
                facturacion = df_estrato["FACTURACION CONSUMO"].sum()
                rural_usuarios = df_estrato[df_estrato["UBICACION"] == "R"]["NIU"].nunique()
                urbano_usuarios = df_estrato[df_estrato["UBICACION"] == "U"]["NIU"].nunique()
                return {
                    "total_usuarios": total_usuarios,
                    "consumo": consumo,
                    "facturacion": facturacion,
                    "rural_usuarios": rural_usuarios,
                    "urbano_usuarios": urbano_usuarios
                }
            for info in estratos_info:
                metrics = obtener_metricas_estrato(df_r, info["estrato"])
                row = escribir_estrato(
                    worksheet_informe,
                    start_row=row,
                    categoria=info["categoria"],
                    rural_usuarios=metrics["rural_usuarios"],
                    urbano_usuarios=metrics["urbano_usuarios"],
                    total_usuarios=metrics["total_usuarios"],
                    consumo=metrics["consumo"],
                    facturacion=metrics["facturacion"],
                    text_format=text_format,
                    num_format=num_format
                )
            workbook.close()
            output.seek(0)
            return output.getvalue()
        
        def create_zip(Tarifas, informeDaneVf, diferencias):
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:       
                dane_buffer = io.StringIO()
                informeDaneVf.to_csv(dane_buffer, index=False, encoding='utf-8-sig')
                zip_file.writestr("Informe_DANE.csv", dane_buffer.getvalue())
                diferencias_buffer = io.StringIO()
                diferencias.to_csv(diferencias_buffer, index=False, encoding='utf-8-sig')
                zip_file.writestr("Diferencias_Tarifas_Bitacora.csv", diferencias_buffer.getvalue())
                excel_bytes = generar_informes_excel_bytes(Tarifas)
                zip_file.writestr("Informe_Tarifas.xlsx", excel_bytes)
            zip_buffer.seek(0)
            return zip_buffer

        st.download_button(
            label="📥 Descargar Tarifas, Informe DANE y Diferencias",
            data=create_zip(Tarifas, informeDaneVf, diferencias),
            file_name="Reportes_Tarifas.zip",
            mime="application/zip"
        )
    else:
        st.error("❌ No se encontraron todas las columnas necesarias en TC1. Verifica el archivo.")
        
if st.button("Limpiar"):
    st.session_state.clear()
    st.rerun()
