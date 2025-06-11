import pandas as pd
import numpy as np
import streamlit as st
import re
import io
import zipfile
import xlsxwriter
from typing import Any, Dict

st.title("Generación de informes (tarifas e informe Dane)")

# Lista para registrar los errores detectados
errores_detectados = []

# Subida de archivos
uploaded_files = st.file_uploader(
    "Subir archivos (TC1.csv, TC2.xlsx, AP.xlsx, Divipola.xlsx, Bitacora.xlsx)",
    type=["csv", "xlsx"],
    accept_multiple_files=True
)

# Patrones regex para cada clave
pattern_map = {
    "TC1":      re.compile(r'(?i)(?:^|[\s_\-\.])TC1(?:$|[\s_\-\.])'),
    "TC2":      re.compile(r'(?i)(?:^|[\s_\-\.])TC2(?:$|[\s_\-\.])'),
    "AP":       re.compile(r'(?i)(?:^|[\s_\-\.])AP(?:$|[\s_\-\.])'),
    "DIVIPOLA": re.compile(r'(?i)(?:^|[\s_\-\.])DIVIPOLA(?:$|[\s_\-\.])'),
    "BITACORA": re.compile(r'(?i)(?:^|[\s_\-\.])BITACORA(?:$|[\s_\-\.])'),
}

# Asignar archivos subidos
file_dict = {k: None for k in pattern_map}
for f in uploaded_files:
    for k, pat in pattern_map.items():
        if pat.search(f.name):
            file_dict[k] = f
            break

if all(file_dict.values()):
    try:
        # ─── Lectura de archivos ─────────────────────────────────────────
        tc1      = pd.read_csv(file_dict["TC1"], low_memory=False)
        tc2      = pd.read_excel(file_dict["TC2"])
        ap       = pd.read_excel(file_dict["AP"], sheet_name="TABLA TARIFAS", header=3)
        ap       = ap[~ap.iloc[:,0].astype(str).str.contains("Total general", na=False)]
        divipola = pd.read_excel(file_dict["DIVIPOLA"])
        bitacora = pd.read_excel(file_dict["BITACORA"])

        # ─── Filtrado y normalización TC1 ───────────────────────────────
        tc1_filtrado = tc1[tc1['ID COMERCIALIZADOR']==23442].copy()
        tc1_filtrado.loc[:, 'NIU'] = tc1_filtrado['NIU'].astype(str).str.strip()
        st.write(f"Número de NIUs en TC1: {tc1_filtrado['NIU'].nunique()}")

        # ─── Validación y normalización TC2 ─────────────────────────────
        tc2_sin_dup = tc2.drop_duplicates(subset='NIU').copy()
        tc2_sin_dup.loc[:, 'NIU'] = tc2_sin_dup['NIU'].astype(str).str.strip()
        st.write(f"Número de NIUs en TC2: {tc2_sin_dup['NIU'].nunique()}")

        # ─── Función para normalizar NIU ─────────────────────────────────
        def normalize_niu(x: str) -> str:
            return re.sub(r"\D","", x or "")

        tc1_filtrado.loc[:, 'NIU_norm'] = tc1_filtrado['NIU'].apply(normalize_niu)
        tc2_sin_dup.loc[:,  'NIU_norm'] = tc2_sin_dup['NIU'].apply(normalize_niu)

        set1, set2 = set(tc1_filtrado['NIU_norm']), set(tc2_sin_dup['NIU_norm'])
        faltan, sobran = sorted(set1 - set2), sorted(set2 - set1)
        if faltan:
            df = (tc1_filtrado[tc1_filtrado['NIU_norm'].isin(faltan)]
                  [['NIU']].drop_duplicates().rename(columns={'NIU':'NIU_TC1'}))
            errores_detectados.append(("❌ NIUs de TC1 no en TC2:", df))
        if sobran:
            df = (tc2_sin_dup[tc2_sin_dup['NIU_norm'].isin(sobran)]
                  [['NIU']].drop_duplicates().rename(columns={'NIU':'NIU_TC2'}))
            errores_detectados.append(("❌ NIUs de TC2 no en TC1:", df))
        if not faltan and not sobran:
            st.success("✅ NIUs coinciden tras normalizar")

        # ─── Construcción de la tabla Tarifas ────────────────────────────
        cols_req = ['NIU','ESTRATO','CODIGO DANE (NIU)','UBICACION',
                    'NIVEL DE TENSION','PORCENTAJE PROPIEDAD DEL ACTIVO','CODIGO AREA ESPECIAL']
        Tarifas = tc1_filtrado[cols_req].copy()
        Tarifas.columns = ['NIU','ESTRATO','DIVIPOLA','UBICACION',
                           'NIVEL DE TENSION','CARGA DE INVERSION','ZE']
        Tarifas['NIU']       = Tarifas['NIU'].astype(str)
        Tarifas['ESTRATO']   = Tarifas['ESTRATO'].replace({7:'I',8:'C',9:'O',11:'AP'}).astype(str)
        Tarifas['UBICACION'] = Tarifas['UBICACION'].replace({1:'R',2:'U'}).astype(str)
        Tarifas['DIVIPOLA']  = Tarifas['DIVIPOLA'].astype(str)

        divipola.columns = divipola.columns.str.strip()
        Tarifas = (Tarifas
                   .merge(divipola[['Código DIVIPOLA','Nombre Municipio']],
                          left_on='DIVIPOLA', right_on='Código DIVIPOLA', how='left')
                   .rename(columns={'Nombre Municipio':'MUNICIPIO'})
                   .drop(columns=['Código DIVIPOLA']))

        piv = (pd.pivot_table(tc2, index='NIU',
                values=['CONSUMO USUARIO (KWH)','VALOR FACTURACION POR CONSUMO USUARIO ($)'],
                aggfunc='sum')
               .reset_index())
        piv['NIU'] = piv['NIU'].astype(str).str.strip()
        tc2_sin_dup['TIPO DE TARIFA'] = tc2_sin_dup['TIPO DE TARIFA'].astype(str)
        piv = piv.merge(tc2_sin_dup[['NIU','TIPO DE TARIFA']], on='NIU', how='left')
        piv['TIPO DE TARIFA'] = piv['TIPO DE TARIFA'].replace({'1':'R','2':'NR'}).astype(str)

        Tarifas = (Tarifas
                   .merge(piv, on='NIU', how='left')
                   .rename(columns={
                       'TIPO DE TARIFA':'TIPO TARIFA',
                       'CONSUMO USUARIO (KWH)':'CONSUMO',
                       'VALOR FACTURACION POR CONSUMO USUARIO ($)':'FACTURACION CONSUMO'
                   }))

        # ─── Procesar AP ────────────────────────────────────────────────
        ap['producto']      = ap['producto'].astype(str).str.strip()
        ap = ap[ap['producto']!='']
        ap['tipo de tarifa'] = ap['tipo de tarifa'].replace({1:'R',2:'NR'}).astype(str)
        ap['estrato']        = ap['estrato'].replace({11:'AP'}).astype(str)
        ap = ap[ap['estrato']=='AP']
        tarifas_ap = Tarifas[Tarifas['ESTRATO']=='AP']
        falt_ap  = set(tarifas_ap['NIU']) - set(ap['producto'])
        falt_tar = set(ap['producto']) - set(tarifas_ap['NIU'])
        if falt_ap:
            errores_detectados.append(("❌ NIUs en Tarifas no en AP:",
                pd.DataFrame({'NIU':list(falt_ap)})))
        if falt_tar:
            errores_detectados.append(("❌ NIUs en AP no en Tarifas:",
                pd.DataFrame({'NIU':list(falt_tar)})))
        Tarifas = (Tarifas
                   .merge(ap[['producto','Suma de consumo','Suma de facturacion consumo','tipo de tarifa']],
                          left_on='NIU', right_on='producto', how='left')
                   .assign(
                       CONSUMO=lambda df: np.where(df['Suma de consumo']>0, df['Suma de consumo'], df['CONSUMO']),
                       FACTURACION_CONSUMO=lambda df: np.where(
                           df['Suma de facturacion consumo'].notna() & (df['Suma de facturacion consumo']!=0),
                           df['Suma de facturacion consumo'], df['FACTURACION CONSUMO']
                       ),
                       **{'TIPO TARIFA': lambda df: np.where(df['tipo de tarifa'].notna(), df['tipo de tarifa'], df['TIPO TARIFA'])}
                   )
                   .drop(columns=['producto','Suma de consumo','Suma de facturacion consumo','tipo de tarifa'])
                  )

        # ─── Validaciones finales ──────────────────────────────────────
        mask = (Tarifas[['CONSUMO','FACTURACION CONSUMO']].isna().any(1) |
                Tarifas[['CONSUMO','FACTURACION CONSUMO']].isin([np.inf,-np.inf]).any(1))
        if mask.any():
            errores_detectados.append(("❌ NIUs con valores inválidos:",
                Tarifas.loc[mask, ['NIU','CONSUMO','FACTURACION CONSUMO']]))
        else:
            Tarifas['CONSUMO']             = np.floor(Tarifas['CONSUMO']+0.5).astype(int)
            Tarifas['FACTURACION CONSUMO'] = np.floor(Tarifas['FACTURACION CONSUMO']+0.5).astype(int)

        # ─── Bitácora y diferencias ───────────────────────────────────
        bitacora = bitacora[bitacora['Tipo Frontera']=='Tipo No Regulado'].copy()
        bitacora['Producto'] = bitacora['Producto'].astype(str)
        ultimo = bitacora.columns[-1]
        resultado = (bitacora[['Producto',ultimo]]
                     .merge(Tarifas[['NIU','CONSUMO']],
                            left_on='Producto', right_on='NIU', how='left'))
        resultado['Diferencia']   = abs(resultado[ultimo]-resultado['CONSUMO'])
        resultado['Es Diferente'] = resultado['Diferencia']>1
        diferencias = resultado[resultado['Es Diferente']][['NIU','CONSUMO',ultimo]]

        # ─── Informe DANE ─────────────────────────────────────────────
        informeDane = Tarifas[(Tarifas['UBICACION']=='U') & (Tarifas['MUNICIPIO']=='POPAYAN')]
        informeDaneVf = (pd.pivot_table(
            informeDane, index='ESTRATO',
            values=['NIU','CONSUMO','FACTURACION CONSUMO'],
            aggfunc={'NIU':'count','CONSUMO':'sum','FACTURACION CONSUMO':'sum'}
        ).rename(columns={'NIU':'CONTEO_NIU','CONSUMO':'SUMA_CONSUMO','FACTURACION CONSUMO':'SUMA_FACTURACION'})
        .reset_index())
        informeDaneVf['ESTRATO'] = informeDaneVf['ESTRATO'].astype(str)

    except Exception as e:
        st.error(f"⛔ Error al procesar archivos: {e}")

    # ─── Mostrar errores o éxito ───────────────────────────────────
    if errores_detectados:
        st.error("Se encontraron errores:")
        for msg, df in errores_detectados:
            st.markdown(f"- {msg}")
            if df is not None:
                st.dataframe(df)
    else:
        st.success("✅ Validaciones completadas.")

    # ─── Mostrar tablas ───────────────────────────────────────────
    st.write("### Diferencias tarifas vs bitácora")
    st.dataframe(diferencias)
    st.write("### Tabla de Tarifas")
    st.dataframe(Tarifas)
    st.write("### Informe DANE (Popayán)")
    st.dataframe(informeDaneVf)

    # ─── Generar ZIP con Excel y CSV ─────────────────────────────
    def create_zip():
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            # Excel consol + informe
            out = io.BytesIO()
            wb = xlsxwriter.Workbook(out, {'in_memory':True})
            header_fmt = wb.add_format({'bold':True,'align':'center','valign':'vcenter','border':1,'bg_color':'#D9D9D9'})
            text_fmt   = wb.add_format({'align':'center','valign':'vcenter','border':1})
            num_fmt    = wb.add_format({'num_format':'_(* #,##0_);_(* (#,##0);_(* "-"??_);_(@_)','border':1})

            # Hoja "Consolidado"
            ws1 = wb.add_worksheet("Consolidado")
            for c, col in enumerate(Tarifas.columns):
                ws1.write(0, c, col, header_fmt)
            for r, row in enumerate(Tarifas.values, start=1):
                for c, val in enumerate(row):
                    fmt = num_fmt if isinstance(val,(int,float)) else text_fmt
                    ws1.write(r, c, val, fmt)

            # Hoja "Informe"
            ws2 = wb.add_worksheet("Informe")
            ws2.set_column('A:A',20)
            ws2.set_column('B:D',15)
            ws2.set_column('E:E',15)
            ws2.set_column('F:F',20)
            ws2.write(0,0,"", header_fmt)
            ws2.merge_range(0,1,0,3,"Número de usuarios", header_fmt)
            ws2.write(0,4,"Consumo", header_fmt)
            ws2.write(0,5,"Facturación consumo", header_fmt)
            row = 1
            for tarifa_type in ["NR","R"]:
                df_t = Tarifas[Tarifas["TIPO TARIFA"]==tarifa_type]
                cnt = df_t["NIU"].nunique()
                cons = df_t["CONSUMO"].sum()
                fact = df_t["FACTURACION CONSUMO"].sum()
                label = "No regulados" if tarifa_type=="NR" else "Regulados"
                ws2.write(row,0,label, text_fmt)
                ws2.merge_range(row,1,row,3,cnt,num_fmt)
                ws2.write(row,4,cons,num_fmt)
                ws2.write(row,5,fact,num_fmt)
                row += 1

            def escribir_estrato(ws,sr,cat,val):
                df_e = Tarifas[Tarifas["ESTRATO"]==val]
                cnt = df_e["NIU"].nunique()
                rur = df_e[df_e["UBICACION"]=="R"]["NIU"].nunique()
                urb = df_e[df_e["UBICACION"]=="U"]["NIU"].nunique()
                cons = df_e["CONSUMO"].sum()
                fact = df_e["FACTURACION CONSUMO"].sum()
                ws.merge_range(sr,0,sr+1,0,cat,text_fmt)
                ws.write(sr,1,"Rural",text_fmt); ws.write(sr,2,rur,num_fmt)
                ws.merge_range(sr,3,sr+1,3,cnt,num_fmt)
                ws.merge_range(sr,4,sr+1,4,cons,num_fmt)
                ws.merge_range(sr,5,sr+1,5,fact,num_fmt)
                ws.write(sr+1,1,"Urbano",text_fmt); ws.write(sr+1,2,urb,num_fmt)
                return sr+2

            estratos = [("Estrato 1","1"),("Estrato 2","2"),("Estrato 3","3"),
                        ("Estrato 4","4"),("Estrato 5","5"),("Estrato 6","6"),
                        ("Alumbrado público","AP"),("Comercial","C"),
                        ("Industrial","I"),("Oficial","O")]
            for cat,val in estratos:
                row = escribir_estrato(ws2, row, cat, val)

            wb.close()
            out.seek(0)
            z.writestr("Informe_Tarifas.xlsx", out.getvalue())

            # Añadir CSVs
            z.writestr("Informe_DANE.csv", informeDaneVf.to_csv(index=False, encoding='utf-8-sig'))
            z.writestr("Diferencias.csv", diferencias.to_csv(index=False, encoding='utf-8-sig'))

        buf.seek(0)
        return buf

    st.download_button(
        "📥 Descargar Reportes (ZIP)",
        data=create_zip(),
        file_name="Reportes_Tarifas.zip",
        mime="application/zip"
    )

if st.button("Limpiar"):
    st.session_state.clear()
    st.rerun()
