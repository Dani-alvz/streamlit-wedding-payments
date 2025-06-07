import streamlit as st
import gspread
import pandas as pd
import time

# --- Configuración de Google Sheets ---
# ¡IMPORTANTE!: Reemplaza esta URL con la URL de TU hoja de cálculo de Google.
# Asegúrate de que la hoja esté compartida como "Editor" para "Cualquier persona con el enlace".
# Puedes dejar un valor placeholder ahora, pero DEBES cambiarlo por la URL real de tu Google Sheet
# ANTES de desplegar en Streamlit Community Cloud.
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1kHnQJp5ruV0NvelWYEyXoeXX6dkzoiWlJSzG0wdGrTo/edit?gid=0#gid=0"

# st.cache_resource: Solo se ejecuta una vez por sesión, o cuando los argumentos cambian.
# ttl=3600: Cachea la conexión por 1 hora. Útil para evitar reconexiones constantes.
@st.cache_resource(ttl=3600)
def get_google_sheet_data():
    """Conecta a Google Sheets y obtiene los datos.
    Utiliza las credenciales de Streamlit.secrets.
    """
    try:
        # Asegúrate de que st.secrets está configurado correctamente en Streamlit Cloud
        # con las credenciales de tu cuenta de servicio de GCP.
        gc = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
        spreadsheet = gc.open_by_url(GOOGLE_SHEET_URL)
        worksheet = spreadsheet.get_worksheet(0) # La primera hoja (índice 0)
        data = worksheet.get_all_records() # Obtiene los datos como una lista de diccionarios
        df = pd.DataFrame(data)
        return df, worksheet
    except Exception as e:
        st.error(f"Error al conectar con Google Sheets. Asegúrate de: \n"
                 f"1. La URL de la hoja es correcta.\n"
                 f"2. La hoja está compartida con 'Editor' para 'Cualquier persona con el enlace'.\n"
                 f"3. Las credenciales en Streamlit Cloud (`.streamlit/secrets.toml`) son correctas y completas.\n"
                 f"Error: {e}")
        st.stop() # Detiene la ejecución si hay un error crítico

def update_google_sheet(worksheet, service_name, amount):
    """Actualiza la cantidad aportada para un servicio en Google Sheets."""
    # Obtener la última versión de los datos para asegurar el cálculo correcto de la aportación
    # Esto es vital en un entorno multiusuario para evitar sobrescribir aportaciones concurrentes
    st.cache_resource.clear() # Limpia la caché para obtener los datos más recientes
    df_latest, _ = get_google_sheet_data()

    # Encontrar la fila del servicio por su nombre
    row_index_in_df = df_latest[df_latest['Servicio'] == service_name].index

    if not row_index_in_df.empty:
        # El índice de gspread es 1-based, y la primera fila es la de los encabezados
        # Por lo tanto, si el índice de pandas es 0 (primera fila de datos), en gspread será 2
        gspread_row_index = row_index_in_df[0] + 2

        current_amount = df_latest.loc[row_index_in_df[0], 'Aportado']
        new_amount = current_amount + amount

        # Actualizar la celda en la columna 'Aportado' (que es la columna 3)
        worksheet.update_cell(gspread_row_index, 3, new_amount)
    else:
        st.error(f"Servicio '{service_name}' no encontrado en la hoja de cálculo.")


def app():
    st.set_page_config(
        page_title="Aportaciones para Servicios",
        page_icon="💸",
        layout="centered"
    )

    st.title("💸 Aportaciones para Servicios de tu Evento 💸")
    st.write("¡Apoya tus servicios favoritos! Cada aportación nos ayuda a cumplir los objetivos.")

    # Cargar datos de la hoja de cálculo
    df_servicios, worksheet = get_google_sheet_data()

    # Mostrar la lista de servicios con barras de progreso
    st.header("Progreso de Aportaciones por Servicio:")

    # Ordenar servicios por nombre para una visualización consistente
    df_servicios = df_servicios.sort_values(by='Servicio').reset_index(drop=True)

    for index, row in df_servicios.iterrows():
        servicio = row['Servicio']
        objetivo = row['Objetivo']
        aportado = row['Aportado']

        progreso_porcentaje = min(100, (aportado / objetivo) * 100) if objetivo > 0 else 0

        st.subheader(f"✨ {servicio}")

        # Usamos columnas para alinear la barra y el texto del monto
        col1, col2 = st.columns([3, 1]) # 3 partes para la barra, 1 para el texto
        with col1:
            st.progress(progreso_porcentaje / 100) # st.progress espera un valor entre 0.0 y 1.0
        with col2:
            st.markdown(f"**{aportado}€ / {objetivo}€**")

        if aportado >= objetivo:
            st.success(f"¡Objetivo alcanzado para {servicio}! 🎉")
        else:
            # Sección para que el usuario aporte
            st.markdown(f"### Aportar a {servicio}:")

            # Calcular el máximo de aporte para no exceder el objetivo
            max_aporte = objetivo - aportado

            # Número de entrada con validación
            aporte_input = st.number_input(
                f"¿Cuánto quieres aportar a {servicio}?",
                min_value=0,
                max_value=max_aporte,
                value=0, # Valor por defecto
                step=5, # Incrementos de 5 en 5
                key=f"input_{servicio}" # Clave única para cada widget de input
            )

            # Botón de aportación
            if st.button(f"Aportar {aporte_input}€ a {servicio}", key=f"button_{servicio}"):
                if aporte_input > 0:
                    # Asegurarse de que no se supera el objetivo incluso con la aportación
                    if (aportado + aporte_input) <= objetivo:
                        update_google_sheet(worksheet, servicio, aporte_input)
                        st.success(f"¡Gracias por tu aporte de {aporte_input}€ a {servicio}!")
                        time.sleep(1) # Pequeña pausa para que el usuario vea el mensaje
                        st.rerun() # Recargar la app para mostrar el progreso actualizado
                    else:
                        st.warning(f"Tu aportación de {aporte_input}€ superaría el objetivo. Por favor, aporta un máximo de {max_aporte}€.")
                else:
                    st.warning("Por favor, introduce una cantidad mayor que 0.")
        st.markdown("---") # Separador visual entre servicios

    st.info("¡Mantente atento al progreso! Una vez que un servicio alcanza su objetivo, se llenará y no se podrán hacer más aportaciones.")

if __name__ == "__main__":
    app()
