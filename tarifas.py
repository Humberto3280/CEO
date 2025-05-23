"""# **Lectura de los archivos necesarios para el proceso**
* *TC1*
* *TC2*
* *AP*
* *Davipola*
"""

import pandas as pd
#Lectura en csv
tc1 = pd.read_csv('TC1.csv')

#Lectura en xlsx
tc2 = pd.read_excel('TC2.xlsx')

#para leer al archivo AP
def extraer_datos_excel(archivo_entrada, hoja_origen):
    # Leer la hoja con la tabla dinámica, comenzando desde la fila 4 (índice 3)
    df = pd.read_excel(archivo_entrada, sheet_name=hoja_origen, header=3)

    # Remover la fila de "Total general" (ajustar si el nombre varía)
    df = df[~df.iloc[:, 0].astype(str).str.contains("Total general", na=False)]

    return df  # Devuelve el DataFrame limpio

archivo_entrada = "/workspaces/codespaces-jupyter/data/AP.xlsx"
hoja_origen = "TABLA TARIFAS"
archivo_ap = extraer_datos_excel(archivo_entrada, hoja_origen)

#leer archivo divipola para los nombres de los municipios
davipola = pd.read_excel('Dane_Divipola_08_2012.xlsx')
bitacora = pd.read_excel('Bitacora.xlsx')

# Imprimir nombres de columnas de TC1 y TC2 para verificar
print("Columnas en TC1:", tc1.columns)
print("Columnas en TC2:", tc2.columns)
print("Columnas en AP:", archivo_ap.columns)

"""# **Empezamos con el primer paso:**
Filtrar en TC1 por ID_COMERCIALIZADOR = 23442 Y con ello verificamos el numero de clientes presentes en TC1
"""

# Filtrar por ID de comercializador 23442 y contar los NIUs en TC1
# Ajustar el nombre de la columna según la salida anterior
id_comercializador_col = 'ID COMERCIALIZADOR'  # Ajustar según sea necesario
niu_col = 'NIU'  # Ajustar según sea necesario

tc1_filtrado = tc1[tc1[id_comercializador_col] == 23442]
count_nius_tc1 = tc1_filtrado[niu_col].nunique()

print(f"Número de NIUs en TC1 después de filtrar: {count_nius_tc1}")

"""# **Ahora Verificamos en TC2 que cumpla con el numero de clientes, para ello:**

* *Se eliminan duplicados*
* *Se valida si el número de clientes -1 un cliente, es igual al antes dado en TC1*
"""

# Paso 2: Eliminar duplicados y contar NIUs en TC2
tc2_sin_duplicados = tc2.drop_duplicates(subset='NIU')
count_nius_tc2 = tc2_sin_duplicados['NIU'].nunique()

print(f"Número de NIUs en TC2 después de eliminar duplicados: {count_nius_tc2}")

# Verificar que los NIUs coinciden (deben coincidir con el valor enviado por Genit menos uno)
if count_nius_tc1 == count_nius_tc2 - 1:
    print("El número de NIUs coincide con el valor esperado.")
else:
  assert count_nius_tc1 == count_nius_tc2 - 2,"El número de NIUs no coincide con el valor esperado."

"""# **Verificamos que el cliente que es de otro mercado "898352932" corresponda con el ID de Mercado "443"**"""

## Paso 3: Verificar el cliente en otro mercado
#clientes_otro_mercado = [898352932, 18124198] # Lista de clientes en otro mercado
#id_mercado_col = 'ID mercado'

# Filtrar el DataFrame para obtener los IDs de mercado de los clientes
#id_mercado_tc2 = tc2[tc2['NIU'].isin(clientes_otro_mercado)][id_mercado_col].iloc[0]

#if id_mercado_tc2 == 443:
#    print(f"El cliente está en el mercado con ID: {id_mercado_tc2}")
#else:
#    warnings.warn(f"Advertencia: El ID de mercado no coincide. Se encontró ID: {id_mercado_tc2}", UserWarning)

"""# Aquí se empieza a construir el archivo de tarifas teniendo en cuenta que este incluye:

* *NIU*
* *ESTRATO*
* *DIVIPOLA*
* *UBICACION*
* *NIVEL DE TENSION*
* *CARGA DE INVERSION*
* *ZE*
"""

# Paso 4: Crear la nueva tabla filtrada y guardarla si es necesario
columns_to_select = ['NIU', 'ESTRATO', 'CODIGO DANE (NIU)', 'UBICACION', 'NIVEL DE TENSION', 'PORCENTAJE PROPIEDAD DEL ACTIVO', 'CODIGO AREA ESPECIAL']
Tarifas = tc1_filtrado[columns_to_select]
Tarifas.columns = ['NIU', 'ESTRATO', 'DIVIPOLA', 'UBICACION', 'NIVEL DE TENSION', 'CARGA DE INVERSION', 'ZE']


"""# Ahora se le tienen que hacer algunas modificaciones en este caso:

* *El estrato esta condicionado asi 7=I - 8=C - 9=O - 11=AP*
* *La ubicación esta de la siguiente forma 1=R (Rural) - 2=U (Urbano)*
* *La carga de inversión donde en 101=0*
"""

# Modificar valores en 'ESTRATO'
Tarifas['ESTRATO'] = Tarifas['ESTRATO'].replace({7: 'I', 8: 'C', 9: 'O', 11: 'AP'})

# Modificar valores en 'UBICACION'
Tarifas['UBICACION'] = Tarifas['UBICACION'].replace({1: 'R', 2: 'U'})

#Modificar valores de "CARGA DE INVERSION"
Tarifas['CARGA DE INVERSION'] = Tarifas['CARGA DE INVERSION'].replace({101:0})

"""# Ahora se traen los nombre de los municipios según correspondan al código DAVIPOLA"""

# Realiza la combinación de los DataFrames
Tarifas1 = Tarifas.merge(davipola[['Código DIVIPOLA', 'Nombre Municipio ']],
                        left_on='DIVIPOLA', right_on='Código DIVIPOLA', how='left')

# Renombra la nueva columna con el nombre del municipio
Tarifas1 = Tarifas1.rename(columns={'Nombre Municipio ': 'Municipio'})

# Elimina la columna 'Código DIVIPOLA' si no es necesaria
Tarifas1 = Tarifas1.drop(columns=['Código DIVIPOLA'])

"""# Se verifica que los NIU que estan duplicados cuenten con el mismo tipo de tarifa"""

#Verificar tipo de tarifa en los NIU repetidos
# Paso 1: Encontrar NIU duplicados
duplicated_nius = tc2[tc2.duplicated(subset='NIU', keep=False)]

# Paso 2: Verificar si esos NIU duplicados tienen el mismo tipo de tarifa
different_tarifas = duplicated_nius.groupby('NIU')['Tipo de Tarifa'].nunique()

# Paso 3: Filtrar los NIU que tienen más de un tipo de tarifa
nius_with_different_tarifas = different_tarifas[different_tarifas > 1]

# Paso 4: Imprimir los resultados
if not nius_with_different_tarifas.empty:
    print("NIU igual, pero con tipo de tarifa diferente son:")
    niu_different_tarifa_df = duplicated_nius[duplicated_nius['NIU'].isin(nius_with_different_tarifas.index)]
    print(niu_different_tarifa_df[['NIU', 'Tipo de Tarifa']])

    # Asegurarte de que la cantidad de NIUs con diferentes tarifas sea cero
    assert niu_different_tarifa_df.empty, "Error: Hay NIUs con diferentes tipos de tarifa."
else:
    print("TODO BIEN CON LOS TIPOS DE TARIFA!")

"""# Paso 2. Se traen los siguientes valores de TC2:

* *Consumo Usuario (Con tabla dinámica)*
* *Valor facturación usuario (Con tabla dinámica)*
* *Tipo de tarifas (Sin tabla dinámica)*


Como paso añadido se tiene que cambiar el tipo dew tarifa de la siguiente forma:
 * *Tarifa 2 = NR (No regulada)*
 * *Tarifa 1 = R (Regulada)*
"""

# Crear la tabla dinámica sumando los valores
pivot_table = pd.pivot_table(tc2,
                             index='NIU',
                             values=['Consumo Usuario (kWh)', 'Valor Facturación por Consumo Usuario'],
                             aggfunc='sum')  # Usamos 'sum' para agregar los valores

# Reiniciar el índice para que 'NIU' sea una columna
pivot_table.reset_index(inplace=True)

# Extraer las columnas requeridas en un nuevo DataFrame
tblDinamicaTc2 = pivot_table[['NIU', 'Consumo Usuario (kWh)', 'Valor Facturación por Consumo Usuario']]

# Convertir las columnas NIU a tipo string y eliminar espacios en blanco en ambos DataFrames
Tarifas1['NIU'] = Tarifas1['NIU'].astype(str).str.strip()
tblDinamicaTc2['NIU'] = tblDinamicaTc2['NIU'].astype(str).str.strip()
tc2_sin_duplicados['NIU'] = tc2_sin_duplicados['NIU'].astype(str).str.strip()

# Realizar la combinación para añadir 'Tipo_tarifa' basado en 'NIU'
tblDinamicaTc2 = tblDinamicaTc2.merge(tc2_sin_duplicados[['NIU', 'Tipo de Tarifa']], on='NIU', how='left')
# Realizar la combinación para añadir las columnas que faltan de tblDinamicaTc2 a Tarifas1
Tarifas2 = Tarifas1.merge(tblDinamicaTc2[['NIU', 'Consumo Usuario (kWh)', 'Valor Facturación por Consumo Usuario', 'Tipo de Tarifa']],
                          on='NIU', how='left')

# Modificar valores en 'Tipo_tarifa'
Tarifas2['Tipo de Tarifa'] = Tarifas2['Tipo de Tarifa'].replace({1: 'R', 2: 'NR'})

"""# Ahora se organizan las columnas en el orden que se debe presentar:

* *NIU*
* *ESTRATO*
* *TIPO DE TARIFA*
* *CONSUMO*
* *FACTURACION CONSUMO*
* *UBICACION*
* *DAVIPOLA*
* *MUNICIPIO*
* *NIVEL DE TENSION*
* *CARGO DE INVERSION*
* *ZE*
"""

# Reorganizar las columnas en el orden deseado
Tarifas3 = Tarifas2[['NIU', 'ESTRATO', 'Tipo de Tarifa', 'Consumo Usuario (kWh)',
                                         'Valor Facturación por Consumo Usuario', 'UBICACION',
                                         'DIVIPOLA', 'Municipio', 'NIVEL DE TENSION',
                                         'CARGA DE INVERSION', 'ZE']]

# Renombrar las columnas según los nuevos nombres proporcionados
Tarifas3 = Tarifas3.rename(columns={
    'Tipo de Tarifa': 'TIPO TARIFA',
    'Consumo Usuario (kWh)': 'CONSUMO',
    'Valor Facturación por Consumo Usuario': 'FACTURACION CONSUMO',
    'Municipio': 'MUNICIPIO',
    'DIVIPOLA': 'DAVIPOLA'
})

"""# Añadir el Cliente de otro mercado"""

# Filtrar el DataFrame `tc2` por NIU
niu_filtrado = tc2[(tc2['NIU'] == 898352932) | (tc2['NIU'] == 18124198)]

# Extraer los valores de Consumo Usuario y Valor Facturación por Consumo Usuario ($)
consumo_usuario = niu_filtrado['Consumo Usuario (kWh)'].values[0]
valor_facturacion = niu_filtrado['Valor Facturación por Consumo Usuario'].values[0]

# Crear un nuevo DataFrame con la fila que quieres añadir
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

# Añadir esta fila al DataFrame Tarifas3
Tarifas3 = pd.concat([Tarifas3, nueva_fila], ignore_index=True)

"""# Se eliminan los NIU = CALP"""

# Convertir la columna NIU a tipo string y reemplazar NaN con una cadena vacía
Tarifas3['NIU'] = Tarifas3['NIU'].astype(str).fillna('')

# Filtrar el DataFrame para eliminar filas donde NIU contiene 'CAL'
Tarifas_sin_cal = Tarifas3[~Tarifas3['NIU'].str.contains('CAL')]

"""# Se trae del archivo AP entregado por Hector al archivo de tarifas:

* *TIPO DE TARIFA*
* *CONSUMO USUARIO*
* *FACTURACION CONSUMO USUARIO*
"""

#Convertir los elementos de la columna productos a str
archivo_ap['producto'] = archivo_ap['producto'].astype(str).str.strip()

#Validamos que el archivo AP no contenga productos vacíos
if archivo_ap['producto'].eq('').any():
    raise ValueError("El archivo AP contiene productos vacíos. Por favor, corrige los datos.")
else:
    print("Validación exitosa: No hay productos vacíos en el archivo AP.")

# Modificar valores en 'Tipo_tarifa'
archivo_ap['tipo de tarifa'] = archivo_ap['tipo de tarifa'].replace({1: 'R', 2: 'NR'})

# Modificar valores en 'ESTRATO'
archivo_ap['estrato'] = archivo_ap['estrato'].replace({11: 'AP'})

# Filtrar archivo_ap por estrato='AP'
archivo_ap_filtrado = archivo_ap[archivo_ap['estrato'] == 'AP']

# Hacer un merge entre Tarifas_sin_cal y archivo_ap_filtrado basándose en NIU y producto
Tarifas4 = Tarifas_sin_cal.merge(
    archivo_ap_filtrado[['producto', 'Suma de consumo', 'Suma de facturacion consumo', 'tipo de tarifa']],
    left_on='NIU',    right_on='producto',
    how='left'
)

# Actualizar las columnas CONSUMO, FACTURACION CONSUMO y TIPO TARIFA solo si los valores son mayores a cero
Tarifas4.loc[Tarifas4['Suma de consumo'] > 0, 'CONSUMO'] = Tarifas4['Suma de consumo']
Tarifas4.loc[(Tarifas4['Suma de facturacion consumo'].notna()) & (Tarifas4['Suma de facturacion consumo'] != 0), 'FACTURACION CONSUMO'] = Tarifas4['Suma de facturacion consumo']
Tarifas4.loc[Tarifas4['tipo de tarifa'].notna(), 'TIPO TARIFA'] = Tarifas4['tipo de tarifa']

# Eliminar las columnas adicionales si no son necesarias
Tarifas4 = Tarifas4.drop(columns=['producto', 'Suma de consumo', 'Suma de facturacion consumo', 'tipo de tarifa'])

import numpy as np

# Redondeo personalizado
Tarifas4['CONSUMO'] = np.floor(Tarifas4['CONSUMO'] + 0.5).astype(int)
Tarifas4['FACTURACION CONSUMO'] = np.floor(Tarifas4['FACTURACION CONSUMO'] + 0.5).astype(int)

"""# Validación de archivo tarifas"""

# Validación de valores vacíos en la columna NIU
if Tarifas4['NIU'].eq('').any():
    raise ValueError("Error: La columna NIU tiene valores vacíos. Revisar los archivos TC1 y TC2.")
else:
    print("Validación exitosa: La columna NIU no tiene valores vacíos.")

# Validación de valores negativos en la columna CONSUMO
if (Tarifas4['CONSUMO'] < 0).any():
    raise ValueError("Error: La columna CONSUMO tiene valores negativos. Verifica los datos.")
else:
    print("Validación exitosa: La columna CONSUMO no tiene valores negativos.")

# Validación de valores negativos en la columna FACTURACION CONSUMO
if (Tarifas4['FACTURACION CONSUMO'] < 0).any():
    raise ValueError("Error: La columna FACTURACION CONSUMO tiene valores negativos. Verifica los datos.")
else:
    print("Validación exitosa: La columna FACTURACION CONSUMO no tiene valores negativos.")

# Validación de la regla: Si CONSUMO es 0, FACTURACION CONSUMO también debe ser 0
if ((Tarifas4['CONSUMO'] == 0) & (Tarifas4['FACTURACION CONSUMO'] != 0)).any():
    raise ValueError("Error: Si CONSUMO es 0, FACTURACION CONSUMO también debe ser 0. Hay inconsistencias en los datos.")
else:
    print("Validación exitosa: No hay inconsistencias entre CONSUMO y FACTURACION CONSUMO.")

# Validación de valores nulos en todo el DataFrame
if Tarifas4.isnull().any().any():
    raise ValueError("Error: El DataFrame contiene valores nulos. Verifica las columnas y corrige los datos.")
else:
    print("Validación exitosa: El DataFrame no tiene valores nulos.")

"""# Creo el Archivo Tarifas, para que se pueda descargar en la parte inferior izquierda, donde aparecera una vez se ejecute el Script."""

from datetime import datetime
import calendar

# Obtener el mes actual y restarle uno
mes_actual = datetime.today().month
anio_actual = datetime.today().year

if mes_actual == 1:
    mes_anterior = 12
    anio_actual -= 1
else:
    mes_anterior = mes_actual - 1

# Diccionario para obtener el nombre del mes en español
meses_es = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
    7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}
nombre_mes = meses_es[mes_anterior]

# Guardar el archivo con el nombre dinámico
nombre_archivo = f"/workspaces/codespaces-jupyter/informes/tarifas_{nombre_mes}.csv"
Tarifas4.to_csv(nombre_archivo, index=False)

Tarifas4.info()

"""#**Creación de informe DANE**"""

# Filtrar DaNE por Ubicacion='U' y Municipio='Popayán'
informeDane = Tarifas4[(Tarifas4['UBICACION'] == 'U') & (Tarifas4['MUNICIPIO'] == 'POPAYAN')]
informeDane.head()

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

# Mostrar el nuevo DataFrame
informeDaneVf.head(11)

"""# Se guarda el archivo de tarifas, mirar al lado izquierdo (Informe_DANE.csv)"""

# Guardar el archivo con el nombre dinámico
nombre_archivo = f"/workspaces/codespaces-jupyter/informes/informe_Dane_{nombre_mes}.csv"
informeDaneVf.to_csv(nombre_archivo, index=False)

"""# Validación Bitacora"""

# Convertir la columna 'Producto' de bitácora a string para que coincida con el tipo de 'NIU' en tarifas4
bitacora['Producto'] = bitacora['Producto'].astype(str)
# Filtrar bitácora por 'Tipo Frontera' == 'Tipo No Regulado'
bitacora_filtrada = bitacora[bitacora['Tipo Frontera'] == 'Tipo No Regulado']

# Definir el nombre de la última columna en bitacora
ultima_columna_bitacora = bitacora.columns[-1]

# Realizar el merge en base a Producto y NIU
resultado = pd.merge(
    bitacora_filtrada[['Producto', ultima_columna_bitacora]],
    Tarifas4[['NIU', 'CONSUMO']],
    left_on='Producto', right_on='NIU',
    how='left'
)

# Comparar las columnas con una tolerancia de ±1
resultado['Diferencia'] = abs(resultado[ultima_columna_bitacora] - resultado['CONSUMO'])
resultado['Es Diferente'] = resultado['Diferencia'] > 1

# Filtrar las filas que son diferentes
diferencias = resultado[resultado['Es Diferente']][['NIU', 'CONSUMO', ultima_columna_bitacora]]

# Mostrar el DataFrame con las diferencias
print(diferencias)
