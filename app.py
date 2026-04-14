import streamlit as st
import requests
from PIL import Image
import io
import zipfile
import base64
import time
import unicodedata
import re

# ==========================================
#  CONSTANTES
# ==========================================
TAMANO_MAXIMO_MB = 25
TAMANO_MAXIMO_BYTES = TAMANO_MAXIMO_MB * 1024 * 1024
MAX_INTENTOS_POLLING = 60   # 60 × 2s = 2 minutos máximo por imagen
MAX_REINTENTOS_RED = 3      # Reintentos ante fallos de red


# ==========================================
#  FUNCIONES AUXILIARES
# ==========================================
def sanitizar_nombre(nombre: str) -> str:
    """
    Elimina tildes, espacios y caracteres especiales de un nombre de archivo
    para garantizar compatibilidad entre sistemas operativos al descomprimir el ZIP.
    Ejemplo: 'Camiseta ñoña 2.jpg' → 'Camiseta_nona_2'
    """
    # Normaliza unicode y elimina caracteres de acento (NFD separa letras de sus diacríticos)
    nombre_normalizado = unicodedata.normalize('NFD', nombre)
    nombre_sin_tildes = nombre_normalizado.encode('ascii', 'ignore').decode('ascii')
    # Reemplaza cualquier carácter que no sea letra, número o guión por guión bajo
    return re.sub(r'[^\w\-]', '_', nombre_sin_tildes)


def hacer_peticion_con_reintento(metodo: str, url: str, headers: dict, json_body=None, max_reintentos: int = MAX_REINTENTOS_RED):
    """
    Ejecuta una petición HTTP (GET o POST) con reintentos automáticos ante
    fallos de red puntuales (timeout, error 5xx del servidor).
    Lanza una excepción si se agotan todos los intentos.
    """
    ultimo_error = None
    for intento in range(1, max_reintentos + 1):
        try:
            if metodo.upper() == "POST":
                respuesta = requests.post(url, headers=headers, json=json_body, timeout=30)
            else:
                respuesta = requests.get(url, headers=headers, timeout=30)

            # Reintenta solo en errores de servidor (5xx), no en errores de cliente (4xx)
            if respuesta.status_code >= 500:
                raise requests.exceptions.RequestException(
                    f"Error del servidor: HTTP {respuesta.status_code}"
                )
            return respuesta

        except requests.exceptions.RequestException as e:
            ultimo_error = e
            if intento < max_reintentos:
                time.sleep(2 * intento)  # Espera progresiva: 2s, 4s, 6s

    raise Exception(f"Fallo tras {max_reintentos} intentos: {ultimo_error}")


# ==========================================
#  FUNCIÓN DEL BACKEND (IA)
# ==========================================
def procesar_con_modelia(foto_bytes: bytes) -> bytes:
    """
    Envía una imagen a la API de Modelia.ai para eliminar su fondo.
    - Usa reintentos ante fallos de red.
    - Implementa timeout para evitar bucles infinitos si la IA no responde.
    Devuelve los bytes de la imagen resultante (sin fondo).
    """
    try:
        api_key = st.secrets["API_KEY_MODELIA"]
    except Exception:
        raise Exception("Falta la API_KEY_MODELIA en la carpeta .streamlit/secrets.toml")

    base_url = "https://modelia.ai"
    headers = {"Content-Type": "application/json", "X-API-Key": api_key}
    foto_base64 = base64.b64encode(foto_bytes).decode('utf-8')

    # --- POST: enviar imagen ---
    respuesta_post = hacer_peticion_con_reintento(
        "POST",
        f"{base_url}/api/v1/remove_background",
        headers,
        json_body={"image_base64": foto_base64}
    )
    if respuesta_post.status_code != 200:
        raise Exception(f"Error al enviar la imagen: {respuesta_post.text}")

    task_id = respuesta_post.json().get("task_id")
    if not task_id:
        raise Exception("Modelia no devolvió un task_id.")

    # --- GET con polling + timeout ---
    url_estado = f"{base_url}/api/v1/get_task_status/{task_id}"

    for intento in range(MAX_INTENTOS_POLLING):
        respuesta_get = hacer_peticion_con_reintento("GET", url_estado, headers)

        if respuesta_get.status_code != 200:
            raise Exception(f"Error al consultar el estado: {respuesta_get.text}")

        datos = respuesta_get.json()
        estado = datos.get("status")

        if estado == "completed":
            resultado_base64 = datos.get("result", {}).get("image_base64")
            if not resultado_base64:
                raise Exception("Modelia terminó pero no envió la imagen en la respuesta.")
            return base64.b64decode(resultado_base64)

        elif estado in ["failed", "error"]:
            error_msg = datos.get("error", "Error desconocido en la IA")
            raise Exception(f"La IA falló al procesar la imagen: {error_msg}")

        time.sleep(2)
    raise Exception(
        f"Timeout: la IA tardó más de {MAX_INTENTOS_POLLING * 2} segundos y no completó el procesamiento."
    )


# ==========================================
#  PLANTILLAS PREDETERMINADAS
# ==========================================
plantillas_fijas = {
    "Prenda 1200": {
        'ancho_lienzo': 1200, 'alto_lienzo': 1200,
        'margen_arriba': 100, 'margen_abajo': 100,
        'margen_izquierda': 100, 'margen_derecha': 100,
        'color_fondo': "#FFFFFF", 'formato_salida': "JPG (Fondo de color)",
        'ppp_salida': 72
    },
    "Modelo 1200": {
        'ancho_lienzo': 1200, 'alto_lienzo': 1200,
        'margen_arriba': 0, 'margen_abajo': 0,
        'margen_izquierda': 0, 'margen_derecha': 0,
        'color_fondo': "#FFFFFF", 'formato_salida': "JPG (Fondo de color)",
        'ppp_salida': 72
    },
    "Shopify modelo": {
        'ancho_lienzo': 900, 'alto_lienzo': 1125,
        'margen_arriba': 0, 'margen_abajo': 0,
        'margen_izquierda': 0, 'margen_derecha': 0,
        'color_fondo': "#FFFFFF", 'formato_salida': "JPG (Fondo de color)",
        'ppp_salida': 72
    },
    "Shopify prenda": {
        'ancho_lienzo': 900, 'alto_lienzo': 1125,
        'margen_arriba': 65, 'margen_abajo': 65,
        'margen_izquierda': 65, 'margen_derecha': 65,
        'color_fondo': "#FFFFFF", 'formato_salida': "JPG (Fondo de color)",
        'ppp_salida': 72
    },
    "Kings modelo": {
        'ancho_lienzo': 700, 'alto_lienzo': 1000,
        'margen_arriba': 0, 'margen_abajo': 0,
        'margen_izquierda': 0, 'margen_derecha': 0,
        'color_fondo': "#FFFFFF", 'formato_salida': "JPG (Fondo de color)",
        'ppp_salida': 72
    },
    "Kings prenda": {
        'ancho_lienzo': 700, 'alto_lienzo': 1000,
        'margen_arriba': 65, 'margen_abajo': 65,
        'margen_izquierda': 65, 'margen_derecha': 65,
        'color_fondo': "#FFFFFF", 'formato_salida': "JPG (Fondo de color)",
        'ppp_salida': 72
    }
}

defaults = {
    'ancho_lienzo': 1200, 'alto_lienzo': 1200,
    'margen_arriba': 0, 'margen_abajo': 0,
    'margen_izquierda': 0, 'margen_derecha': 0,
    'color_fondo': "#FFFFFF", 'formato_salida': "JPG (Fondo de color)",
    'ppp_salida': 72  # CORRECCIÓN #9: ppp_salida ahora forma parte del session_state
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


def aplicar_plantilla():
    seleccion = st.session_state.selector_plantilla
    if seleccion and seleccion in plantillas_fijas:
        p = plantillas_fijas[seleccion]
        for key in defaults.keys():
            if key in p:
                st.session_state[key] = p[key]


if 'uploader_key' not in st.session_state:
    st.session_state.uploader_key = str(time.time())


def limpiar_cola():
    """
    Resetea el file uploader generando una nueva key, y limpia también
    los mensajes de estado anteriores para no confundir al usuario.
    """
    st.session_state.uploader_key = str(time.time())
    if 'ultimo_resultado' in st.session_state:
        del st.session_state['ultimo_resultado']


# ==========================================
#  INTERFAZ DE USUARIO
# ==========================================
st.set_page_config(page_title="Background Remover", page_icon="✂️", layout="centered")
st.title("Background Remover")
st.write("Procesamiento masivo inteligente. Reescala y mantiene el perfil de color original sin pérdidas de calidad.")

with st.sidebar:
    st.header("📂 Plantillas Predeterminadas")
    opciones_plantillas = ["-- Seleccionar Formato --"] + list(plantillas_fijas.keys())
    st.selectbox("Cargar configuración", opciones_plantillas, key="selector_plantilla", on_change=aplicar_plantilla)

    st.divider()

    st.header("📏 Dimensiones del Lienzo")
    col_dim1, col_dim2 = st.columns(2)
    with col_dim1:
        ancho_lienzo = st.number_input("Ancho Total (px)", min_value=100, max_value=4000, key="ancho_lienzo")
    with col_dim2:
        alto_lienzo = st.number_input("Alto Total (px)", min_value=100, max_value=4000, key="alto_lienzo")

    st.header("🔲 Márgenes")
    col_marg1, col_marg2 = st.columns(2)
    with col_marg1:
        margen_arriba = st.number_input("Arriba (px)", min_value=0, max_value=4000, key="margen_arriba")
        margen_izquierda = st.number_input("Izquierda (px)", min_value=0, max_value=4000, key="margen_izquierda")
    with col_marg2:
        margen_abajo = st.number_input("Abajo (px)", min_value=0, max_value=4000, key="margen_abajo")
        margen_derecha = st.number_input("Derecha (px)", min_value=0, max_value=4000, key="margen_derecha")

    espacio_util_w = ancho_lienzo - margen_izquierda - margen_derecha
    espacio_util_h = alto_lienzo - margen_arriba - margen_abajo

    hay_error_margenes = False
    if espacio_util_w <= 0 or espacio_util_h <= 0:
        hay_error_margenes = True
        st.error("❌ ¡Error matemático! Los márgenes son mayores o iguales al tamaño del lienzo. Por favor, redúcelos.")

    st.header("💾 Exportación y Fondo")
    formato_salida = st.selectbox(
        "Formato de Salida",
        ["JPG (Fondo de color)", "PNG (Transparente)"],
        key="formato_salida"
    )

    usar_color = "JPG" in formato_salida

    if not usar_color:
        st.info("ℹ️ En formato PNG el fondo será transparente. El color de fondo no se aplica.")

    color_fondo = st.color_picker("Color de Fondo (Solo JPG)", key="color_fondo", disabled=not usar_color)

    opciones_ppp = [72, 150, 300]
    indice_ppp = opciones_ppp.index(st.session_state.ppp_salida) if st.session_state.ppp_salida in opciones_ppp else 0
    ppp_salida = st.selectbox("Resolución (PPP)", opciones_ppp, index=indice_ppp, help="Píxeles por pulgada")
    st.session_state.ppp_salida = ppp_salida

    st.markdown("<br><br><br><br>", unsafe_allow_html=True)
    st.markdown(
        "<div style='text-align: center; color: #888888; font-size: 13px; font-weight: 300;'>Desarrollado por Silvia Fernández ✨</div>",
        unsafe_allow_html=True
    )


# ==========================================
#  ÁREA PRINCIPAL
# ==========================================
st.header("📂 Subir Archivos")

st.caption(f"⚠️ Tamaño máximo por imagen: {TAMANO_MAXIMO_MB} MB. Formatos admitidos: JPG, PNG, WEBP, AVIF.")

archivos_subidos = st.file_uploader(
    "Arrastra aquí tus imágenes (JPG, PNG, WEBP o AVIF)",
    type=['jpg', 'jpeg', 'png', 'webp', 'avif'],
    accept_multiple_files=True,
    key=st.session_state.uploader_key
)

col_btn1, col_btn2 = st.columns([1, 1])
with col_btn1:
    btn_procesar = st.button(
        "🚀 Iniciar Procesamiento",
        type="primary",
        disabled=hay_error_margenes,
        use_container_width=True
    )
with col_btn2:
    st.button("🧹 Limpiar cola de archivos", on_click=limpiar_cola, use_container_width=True)


# ==========================================
#  MOTOR DE PROCESAMIENTO
# ==========================================
if btn_procesar:

    if not archivos_subidos:
        st.warning("⚠️ No has subido ninguna imagen.")
    else:
        archivos_validos = []
        for archivo in archivos_subidos:
            if len(archivo.getvalue()) > TAMANO_MAXIMO_BYTES:
                st.warning(f"⚠️ '{archivo.name}' supera los {TAMANO_MAXIMO_MB} MB y será ignorado.")
            else:
                archivos_validos.append(archivo)

        if not archivos_validos:
            st.error("❌ Ninguna imagen supera la validación de tamaño. Sube archivos más pequeños.")
        else:
            archivo_zip_memoria = io.BytesIO()
            barra_progreso = st.progress(0)
            texto_estado = st.empty()
            total_fotos = len(archivos_validos)
            imagenes_ok = 0
            imagenes_error = 0

            
            with zipfile.ZipFile(archivo_zip_memoria, "w", compression=zipfile.ZIP_DEFLATED) as zip_final:

                for indice, archivo in enumerate(archivos_validos):
                    texto_estado.text(f"⏳ Procesando: {archivo.name} ({indice + 1}/{total_fotos})...")

                    try:
                        foto_bytes = archivo.getvalue()

                        img_original = Image.open(io.BytesIO(foto_bytes))
                        perfil_icc_original = img_original.info.get('icc_profile')
                        img_original.close()
                        imagen_bytes_procesada = procesar_con_modelia(foto_bytes)

                        # 1. ANÁLISIS
                        img_rgba = Image.open(io.BytesIO(imagen_bytes_procesada)).convert("RGBA")
                        api_w, api_h = img_rgba.size
                        bbox = img_rgba.getbbox()

                        if bbox:
                            tol = 5
                            is_cut_left = bbox[0] <= tol
                            is_cut_top = bbox[1] <= tol
                            is_cut_right = bbox[2] >= api_w - tol
                            is_cut_bottom = bbox[3] >= api_h - tol
                            prenda_recortada = img_rgba.crop(bbox)
                        else:
                            prenda_recortada = img_rgba
                            is_cut_left = is_cut_right = is_cut_top = is_cut_bottom = False

                        orig_w, orig_h = prenda_recortada.size

                        # 2. ESCALADO MATEMÁTICO ESTRICTO
                        ratio_ancho = espacio_util_w / orig_w
                        ratio_alto = espacio_util_h / orig_h
                        factor_ajuste = min(ratio_ancho, ratio_alto)

                        nuevo_ancho = int(orig_w * factor_ajuste)
                        nuevo_alto = int(orig_h * factor_ajuste)
                        prenda_escalada = prenda_recortada.resize((nuevo_ancho, nuevo_alto), Image.Resampling.LANCZOS)

                        # 3. COMPOSICIÓN AUTÓNOMA
                        if is_cut_right and not is_cut_left:
                            pos_x = ancho_lienzo - margen_derecha - nuevo_ancho
                        elif is_cut_left and not is_cut_right:
                            pos_x = margen_izquierda
                        else:
                            pos_x = margen_izquierda + (espacio_util_w - nuevo_ancho) // 2

                        if is_cut_bottom and not is_cut_top:
                            pos_y = alto_lienzo - margen_abajo - nuevo_alto
                        elif is_cut_top and not is_cut_bottom:
                            pos_y = margen_arriba
                        else:
                            pos_y = margen_arriba + (espacio_util_h - nuevo_alto) // 2

                        # 4. PEGADO Y EXPORTACIÓN CON PERFIL DE COLOR
                        parametros_guardado = {"dpi": (ppp_salida, ppp_salida)}

                        if perfil_icc_original:
                            parametros_guardado["icc_profile"] = perfil_icc_original

                        if "PNG" in formato_salida:
                            lienzo = Image.new("RGBA", (ancho_lienzo, alto_lienzo), (255, 255, 255, 0))
                            lienzo.paste(prenda_escalada, (pos_x, pos_y), prenda_escalada)
                            parametros_guardado["format"] = "PNG"
                            extension = "png"
                        else:
                            lienzo = Image.new("RGB", (ancho_lienzo, alto_lienzo), color_fondo)
                            lienzo.paste(prenda_escalada, (pos_x, pos_y), prenda_escalada)
                            parametros_guardado["format"] = "JPEG"
                            parametros_guardado["quality"] = 95
                            extension = "jpg"

                        imagen_final_bytes = io.BytesIO()
                        lienzo.save(imagen_final_bytes, **parametros_guardado)

                        nombre_sin_extension = archivo.name.rsplit('.', 1)[0]
                        nombre_seguro = sanitizar_nombre(nombre_sin_extension)
                        zip_final.writestr(f"{nombre_seguro}_procesada.{extension}", imagen_final_bytes.getvalue())

                        imagenes_ok += 1

                    except Exception as e:
                        st.error(f"❌ Error procesando '{archivo.name}': {e}")
                        imagenes_error += 1

                    barra_progreso.progress((indice + 1) / total_fotos)

            if imagenes_ok == 0:
                texto_estado.error("❌ Ninguna imagen se procesó correctamente. Revisa los errores anteriores.")
            else:
                if imagenes_error > 0:
                    texto_estado.warning(
                        f"⚠️ Lote completado con incidencias: {imagenes_ok} procesadas correctamente, {imagenes_error} con error."
                    )
                else:
                    texto_estado.success(f"✨ ¡Lote procesado con éxito! {imagenes_ok} imágenes listas.")

                st.download_button(
                    label=f"📦 Descargar {imagenes_ok} imagen(es) en ZIP",
                    data=archivo_zip_memoria.getvalue(),
                    file_name="imagenes_procesadas.zip",
                    mime="application/zip",
                    type="primary"
                )
