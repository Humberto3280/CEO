import streamlit as st
import pandas as pd
import io

st.title("Usuarios Facturados 📊")

# Subida de archivos
tc1_file = st.file_uploader("Sube el archivo TC1 (CSV)", type=["csv"])
divipola_file = st.file_uploader("Sube el archivo Divipola (XLSX)", type=["xlsx"])

if tc1_file and divipola_file:
    # Leer los archivos
    tc1 = pd.read_csv(tc1_file)
    divipola = pd.read_excel(divipola_file)

    # Mostrar primeras filas de los archivos subidos
    st.subheader("Vista previa de TC1")
    st.write(tc1.head())

    st.subheader("Vista previa de Divipola")
    st.write(divipola.head())

    # Filtrar por ID_COMERCIALIZADOR = 23442
    tc1_filtrado = tc1[tc1['ID_COMERCIALIZADOR'] == 23442]
    count_nius_tc1 = tc1_filtrado['PRODUCT_ID'].nunique()

    st.subheader("Número de NIUs en TC1 después de filtrar:")
    st.write(count_nius_tc1)

    # Selección de columnas y renombrado
    usuariosFac = tc1_filtrado[['PRODUCT_ID', 'COD_DANE', 'ESTRATO']]
    usuariosFac.columns = ['NIU', 'DIVIPOLA', 'ESTRATO']

    # Unir con Divipola para obtener Municipio y Zona
    usuariosFac1 = usuariosFac.merge(divipola[['Código DIVIPOLA', 'Nombre Municipio ']],
                                     left_on='DIVIPOLA', right_on='Código DIVIPOLA', how='left')
    usuariosFac1 = usuariosFac1.rename(columns={'Nombre Municipio ': 'MUNICIPIO'})
    usuariosFac1 = usuariosFac1.drop(columns=['Código DIVIPOLA'])

    usuariosFac2 = usuariosFac1.merge(divipola[['Código DIVIPOLA', 'Zona']],
                                      left_on='DIVIPOLA', right_on='Código DIVIPOLA', how='left')
    usuariosFac2 = usuariosFac2.rename(columns={'Zona ': 'ZONA'})
    usuariosFac2 = usuariosFac2.drop(columns=['Código DIVIPOLA'])

    # Eliminar registros con "CALP"
    usuariosFac2['NIU'] = usuariosFac2['NIU'].astype(str).fillna('')
    usuariosFacDf = usuariosFac2[~usuariosFac2['NIU'].str.contains('CAL')]

    st.subheader("Número de NIUs en usuarios facturados:")
    count_usrfact = usuariosFacDf['NIU'].nunique()
    st.write(count_usrfact)

    # Crear archivo Excel en memoria
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        usuariosFacDf.to_excel(writer, sheet_name='Consolidado-sin-calp', index=False)

        # Filtros por zona
        zonas = usuariosFacDf['ZONA'].unique()
        for zona in zonas:
            df_zona = usuariosFacDf[usuariosFacDf['ZONA'] == zona]
            tabla_resumen = df_zona.groupby(['ESTRATO', 'MUNICIPIO']).size().unstack(fill_value=0)

            # Totales generales
            tabla_resumen.loc['Total general'] = tabla_resumen.sum()
            tabla_resumen['Total general'] = tabla_resumen.sum(axis=1)

            # Guardar cada zona en una hoja diferente
            tabla_resumen.to_excel(writer, sheet_name=f'ZONA {zona}')

    output.seek(0)

    # Botón para descargar el Excel
    st.download_button(label="📥 Descargar Usuarios Facturados",
                       data=output,
                       file_name="Usuarios_Facturados_2024.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

