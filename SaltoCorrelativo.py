import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

# --- CONFIGURACIÓN E INICIALIZACIÓN ---
st.set_page_config(
    page_title="Proceso Automatizado de Correlativos",
    page_icon="📊",
    layout="centered",
    initial_sidebar_state="auto"
)

# Inicialización de DataFrames y otros estados necesarios
if 'df1' not in st.session_state:
    st.session_state['df1'] = None
if 'df2' not in st.session_state:
    st.session_state['df2'] = None
if 'Resultado_Salto_2' not in st.session_state:
    st.session_state['Resultado_Salto_2'] = None
if 'last_file1_id' not in st.session_state:
    st.session_state['last_file1_id'] = None
if 'last_file2_id' not in st.session_state:
    st.session_state['last_file2_id'] = None


# --- FUNCIONES DE CARGA DE DATOS ---
def load_data(uploaded_file):
    """
    Función robusta para leer archivos CSV y XLSX.
    Intenta leer la hoja 'Base' para Excel; si falla, lee la primera hoja.
    """
    try:
        if uploaded_file.name.endswith('.csv'):
            return pd.read_csv(uploaded_file)
        elif uploaded_file.name.endswith('.xlsx'):
            try:
                # Intentar leer 'Base' (como en tu Jupyter original)
                return pd.read_excel(uploaded_file, sheet_name='Base')
            except ValueError:
                # Si 'Base' no existe, leer la primera hoja
                return pd.read_excel(uploaded_file)
        return None
    except Exception as e:
        st.error(f"Error al leer el archivo {uploaded_file.name}: {e}. Verifica el formato y encabezados.")
        return None


# --- INTERFAZ DE USUARIO ---
st.title("Proceso de Archivos Correlativos")
st.write("Sube los dos reportes de Excel (Reporte Anterior y Reporte Actual) para iniciar el análisis.")

with st.container():
    st.subheader("Selección de Archivos")

    # Selector para el Archivo 1 (Reporte Anterior)
    uploaded_file_1 = st.file_uploader(
        "Archivo 1: Reporte Anterior ( XLSX)",
        type=["csv", "xlsx"],
        key="file1"
    )
    # Selector para el Archivo 2 (Reporte Actual)
    uploaded_file_2 = st.file_uploader(
        "Archivo 2: Reporte Actual ( XLSX)",
        type=["csv", "xlsx"],
        key="file2"
    )

st.markdown("---") 
st.subheader("Ejecutar Proceso")

# Cargar los DataFrames en el estado de sesión solo si el archivo ha cambiado
if uploaded_file_1 is not None and uploaded_file_1.file_id != st.session_state['last_file1_id']:
    st.session_state['df1'] = load_data(uploaded_file_1)
    st.session_state['last_file1_id'] = uploaded_file_1.file_id

if uploaded_file_2 is not None and uploaded_file_2.file_id != st.session_state['last_file2_id']:
    st.session_state['df2'] = load_data(uploaded_file_2)
    st.session_state['last_file2_id'] = uploaded_file_2.file_id

# Mostrar mensajes de estado de carga
if st.session_state['df1'] is not None:
    st.success("✅ Archivo 1 (Reporte Anterior) listo.")
if st.session_state['df2'] is not None:
    st.success("✅ Archivo 2 (Reporte Actual) listo.")

# Determinar si el proceso está listo para ejecutarse
is_ready = st.session_state['df1'] is not None and st.session_state['df2'] is not None

# Botón de Ejecución
run_process_button = st.button(
    "Ejecutar Proceso", 
    type="primary", 
    disabled=not is_ready
)

if not is_ready:
    st.info("Sube ambos archivos y espera el mensaje 'listo' para habilitar el botón.")


# --- LÓGICA PRINCIPAL DE PROCESAMIENTO (EXACTAMENTE COMO EN JUPYTER) ---
if run_process_button:
    st.write("---")
    st.subheader("Resultado del Proceso")
    
    try:
        # 0. Recuperar y Copiar DataFrames
        Reporte_Anterior = st.session_state['df1'].copy()
        Reporte_Actual = st.session_state['df2'].copy()

        # 1. Selección y Filtro de Columnas
        COLUMNAS_CLAVE = ['Reporte', 'TIPO COMPROBANTE', 'SERIE', 'FACTURA', '1 Periodo ']
        
        Reporte_Anterior = Reporte_Anterior[COLUMNAS_CLAVE].copy()
        Reporte_Actual = Reporte_Actual[COLUMNAS_CLAVE].copy()
        
        # 2. Limpieza de Periodo y Llenado con el Primer Valor Válido
        df_Reporte_Ant_sin_vacios = Reporte_Anterior['1 Periodo '].dropna().reset_index()
        df_Reporte_Act_sin_vacios = Reporte_Actual['1 Periodo '].dropna().reset_index()

        df_Reporte_Act_sin_vacios = df_Reporte_Act_sin_vacios.sort_values(by='1 Periodo ', ascending=False).copy()
        df_Reporte_Ant_sin_vacios = df_Reporte_Ant_sin_vacios.sort_values(by='1 Periodo ', ascending=False).copy()

        primer_valor_RAnt = df_Reporte_Ant_sin_vacios.iloc[0, 1]
        primer_valor_RAct = df_Reporte_Act_sin_vacios.iloc[0, 1]

        Reporte_Anterior['1 Periodo '] = Reporte_Anterior['1 Periodo '].fillna(primer_valor_RAnt)
        Reporte_Actual['1 Periodo '] = Reporte_Actual['1 Periodo '].fillna(primer_valor_RAct)
        
        # 3. Concatenación
        Periodo_reporte = int(primer_valor_RAct) // 100
        
        Reporte_Total = pd.concat([Reporte_Anterior, Reporte_Actual], ignore_index=True)
        Reporte_Total['1 Periodo '] = Reporte_Total['1 Periodo '].astype(int)

        # 4. Ordenar, Crear Correlativos y Diferencia (Shift)
        df_ordenado = Reporte_Total.sort_values(by=['Reporte', 'TIPO COMPROBANTE', 'SERIE', 'FACTURA'], ascending=True)
        
        df_ordenado['FACTURA_ANTERIOR'] = df_ordenado.groupby(['Reporte', 'TIPO COMPROBANTE', 'SERIE'])['FACTURA'].shift(1)
        df_ordenado['FACTURA_ANTERIOR'] = df_ordenado['FACTURA_ANTERIOR'].fillna(-1).astype(int)
        
        df_ordenado['DifFactura'] = df_ordenado['FACTURA'] - df_ordenado['FACTURA_ANTERIOR']

        # 5. Agrupación y Detección de Duplicados
        Agrupacion_Total = df_ordenado.groupby(['Reporte', 'TIPO COMPROBANTE', 'SERIE', 'FACTURA']).agg(
            Recuento=('Reporte', 'size')
        ).reset_index()

        Agrupacion_Total_Duplicados = Agrupacion_Total[Agrupacion_Total['Recuento'] > 1]
        
        # 6. Detección y Agrupación de Saltos Correlativos
        Saltos_Correlativo = df_ordenado[(df_ordenado['DifFactura'] != 1) & (df_ordenado['FACTURA_ANTERIOR'] != -1)]

        Agrupacion_Corrolativo = Saltos_Correlativo.groupby(['Reporte', 'TIPO COMPROBANTE', 'SERIE', 'FACTURA']).agg(
            Recuento=('Reporte', 'size')
        ).reset_index()

        # 7. Primer Merge (Saltos Correlativos)
        Resultado_Salto = pd.merge(
            df_ordenado,
            Agrupacion_Corrolativo,
            left_on=['Reporte', 'TIPO COMPROBANTE', 'SERIE', 'FACTURA'],
            right_on=['Reporte', 'TIPO COMPROBANTE', 'SERIE', 'FACTURA'],
            how='left'
        )

        # 8. Renombrado de Columnas - EXACTAMENTE COMO EN JUPYTER
        Resultado_Salto = Resultado_Salto.rename(columns={
            'TIPO COMPROBANTE': 'Tipo de Comprobante',
            'SERIE': 'Serie',
            'FACTURA': 'Factura',
            '1 Periodo _x': 'Periodo',
            'FACTURA_ANTERIOR_x': 'Factura Anterior',
            'DifFactura_x': 'NroSaltos',
            'Recuento_x': 'Status',
            'Recuento_y': 'Unicos'
        })

        # 9. Segundo Merge (Duplicados Totales) - EXACTAMENTE COMO EN JUPYTER
        Resultado_Salto_2 = pd.merge(
            Resultado_Salto,
            Agrupacion_Total_Duplicados,
            left_on=['Reporte', 'Tipo de Comprobante', 'Serie', 'Factura'],
            right_on=['Reporte', 'TIPO COMPROBANTE', 'SERIE', 'FACTURA'],
            how='left'
        )

        # 10. Creación de Status con np.where - EXACTAMENTE COMO EN JUPYTER
        Resultado_Salto_2['Recuento_x'] = np.where(
            Resultado_Salto_2['Recuento_x'].isnull(), 
            'sin salto', 
            'salto de Correlativo'
        )
        Resultado_Salto_2['Recuento_y'] = np.where(
            Resultado_Salto_2['Recuento_y'].isnull(), 
            'Unicos', 
            'Duplicados'
        )
        
        # 11. Tipo_Serie
        Resultado_Salto_2['Tipo_Serie'] = Resultado_Salto_2['Tipo de Comprobante'].astype(str) + Resultado_Salto_2['Serie']

        # 12. Renombrado Final - EXACTAMENTE COMO EN JUPYTER
        Resultado_Salto_2 = Resultado_Salto_2.rename(columns={
            'Recuento_x': 'Status_Salto', 
            'Recuento_y': 'Status_Duplicado'
        })
        
        # Guardar el resultado final en el estado de sesión para la descarga
        st.session_state['Resultado_Salto_2'] = Resultado_Salto_2
        st.success("✅ ¡Proceso de análisis de correlativos finalizado con éxito!")

        # --- Mostrar Resultado Final y Descarga ---
        st.markdown("### Resultado del Análisis (Últimas 20 Filas)")
        st.dataframe(Resultado_Salto_2.tail(10))
        
        # 13. Conversión a Excel para la descarga
        buffer = BytesIO()
        nombre_archivo = f"Resultado_Salto_Correlativo - OrigenCarga {Periodo_reporte}.xlsx"
        
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            Resultado_Salto_2.to_excel(writer, sheet_name='Resultado', index=False)
        
        st.download_button(
            label="📥 Descargar Resultado Final a Excel",
            data=buffer.getvalue(),
            file_name=nombre_archivo,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary"
        )
        
        # Información adicional en expanders
        with st.expander("📊 Ver Estadísticas del Proceso"):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Registros", len(Resultado_Salto_2))
            with col2:
                saltos = len(Resultado_Salto_2[Resultado_Salto_2['Status_Salto'] == 'salto de Correlativo'])
                st.metric("Saltos Detectados", saltos)
            with col3:
                duplicados = len(Resultado_Salto_2[Resultado_Salto_2['Status_Duplicado'] == 'Duplicados'])
                st.metric("Duplicados", duplicados)
        
        with st.expander("🔍 Ver DataFrame Completo (Primeras 100 filas)"):
            st.dataframe(Resultado_Salto_2.head(20))

    except KeyError as e:
        st.error(f"❌ Error de columna: Se intentó acceder a '{e}' pero no existe. Confirma que tus archivos tienen las columnas: 'Reporte', 'TIPO COMPROBANTE', 'SERIE', 'FACTURA', y '1 Periodo '. (Cuidado con el espacio en '1 Periodo ').")
    except IndexError:
        st.error("❌ Error de datos: La columna '1 Periodo ' está vacía o no tiene suficientes datos válidos para el cálculo inicial del periodo.")
    except Exception as e:
        st.error(f"❌ Ocurrió un error inesperado durante el procesamiento: {e}")
        st.exception(e)  # Muestra el traceback completo para debugging
