import streamlit as st
import requests
from PIL import Image
import io
import zipfile
import base64
import time

# ==========================================
#  FUNCIONES DEL BACKEND
# ==========================================
def procesar_con_modelia(foto_bytes):
    try:
        api_key = st.secrets["API_KEY_MODELIA"]
    except:
        raise Exception("Falta la API_KEY_MODELIA en la carpeta .streamlit/secrets.toml")

    base_url = "https://modelia.ai"
    headers = {"Content-Type": "application/json", "X-API-Key": api_key}
    
    foto_base64 = base64.b64encode(foto_bytes).decode('utf-8')
    
    payload_post = {"image_base64": foto_base64}
    url_post = f"{base_url}/api/v1/remove_background"
    
    respuesta_post = requests.post(url_post, headers=headers, json=payload_post)
    if respuesta_post.status_code != 200:
        raise Exception(f"Error al enviar: {respuesta_post.text}")
        
    task_id = respuesta_post.json().get("task_id")
    if not task_id:
        raise Exception("Modelia no devolvió un task_id.")

    url_get = f"{base_url}/api/v1/get_task_status/{task_id}"
    while True:
        respuesta_get = requests.get(url_get, headers=headers)
        if respuesta_get.status_code != 200:
            raise Exception(f"Error al consultar el estado: {respuesta_get.text}")
            
        datos = respuesta_get.json()
        estado = datos.get("status")
        
        if estado == "completed":
            resultado_base64 = datos.get("result", {}).get("image_base64")
            if not resultado_base64:
                raise Exception("Modelia terminó pero no envió la imagen.")
            return base64.b64decode(resultado_base64)
            
        elif estado in ["failed", "error"]:
            error_msg = datos.get("error", "Error desconocido")
            raise Exception(f"La IA falló: {error_msg}")
            
        time.sleep(2)

# ==========================================
#  PLANTILLAS PREDETERMINADAS
# ==========================================
plantillas_fijas = {
    "Prenda 1200": {
        'ancho_lienzo': 1200, 'alto_lienzo': 1200,
        'margen_arriba': 100, 'margen_abajo': 100,
        'margen_izquierda': 100, 'margen_derecha': 100,
        'color_fondo': "#FFFFFF", 'formato_salida': "JPG (Fondo de color)"
    },
    "Modelo 1200": {
        'ancho_lienzo': 1200, 'alto_lienzo': 1200,
        'margen_arriba': 0, 'margen_abajo': 0,
        'margen_izquierda': 0, 'margen_derecha': 0,
        'color_fondo': "#FFFFFF", 'formato_salida': "JPG (Fondo de color)"
    },
    "Shopify modelo": {
        'ancho_lienzo': 900, 'alto_lienzo': 1125,
        'margen_arriba': 0, 'margen_abajo': 0,
        'margen_izquierda': 0, 'margen_derecha': 0,
        'color_fondo': "#FFFFFF", 'formato_salida': "JPG (Fondo de color)"
    },
    "Shopify prenda": {
        'ancho_lienzo': 900, 'alto_lienzo': 1125,
        'margen_arriba': 65, 'margen_abajo': 65,
        'margen_izquierda': 65, 'margen_derecha': 65,
        'color_fondo': "#FFFFFF", 'formato_salida': "JPG (Fondo de color)"
    },
    "Kings modelo": {
        'ancho_lienzo': 700, 'alto_lienzo': 1000,
        'margen_arriba': 0, 'margen_abajo': 0,
        'margen_izquierda': 0, 'margen_derecha': 0,
        'color_fondo': "#FFFFFF", 'formato_salida': "JPG (Fondo de color)"
    },
    "Kings prenda": {
        'ancho_lienzo': 700, 'alto_lienzo': 1000,
        'margen_arriba': 65, 'margen_abajo': 65,
        'margen_izquierda': 65, 'margen_derecha': 65,
        'color_fondo': "#FFFFFF", 'formato_salida': "JPG (Fondo de color)"
    }
}

defaults = {
    'ancho_lienzo': 1200, 'alto_lienzo': 1200,
    'margen_arriba': 0, 'margen_abajo': 0,
    'margen_izquierda': 0, 'margen_derecha': 0,
    'color_fondo': "#FFFFFF", 'formato_salida': "JPG (Fondo de color)"
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

def aplicar_plantilla():
    seleccion = st.session_state.selector_plantilla
    if seleccion and seleccion in plantillas_fijas:
        p = plantillas_fijas[seleccion]
        for key in defaults.keys():
            if key in p: st.session_state[key] = p[key]

# Generador de llave para resetear el uploader
if 'uploader_key' not in st.session_state:
    st.session_state.uploader_key = str(time.time())

def limpiar_cola():
    # Al cambiar la llave, Streamlit borra el uploader anterior y crea uno vacío
    st.session_state.uploader_key = str(time.time())

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
    with col_dim1: ancho_lienzo = st.number_input("Ancho Total (px)", min_value=100, max_value=4000, key="ancho_lienzo")
    with col_dim2: alto_lienzo = st.number_input("Alto Total (px)", min_value=100, max_value=4000, key="alto_lienzo")
    
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
        st.error("❌ ¡Error matemático! Los márgenes que has puesto son mayores o iguales al tamaño del lienzo. Por favor, redúcelos.")

    st.header("💾 Exportación y Fondo")
    formato_salida = st.selectbox("Formato de Salida", ["JPG (Fondo de color)", "PNG (Transparente)"], key="formato_salida")
    
    # Si elige PNG, deshabilita visualmente el color porque no se va a usar
    usar_color = "JPG" in formato_salida
    color_fondo = st.color_picker("Color de Fondo (Solo JPG)", key="color_fondo", disabled=not usar_color)
    ppp_salida = st.selectbox("Resolución", [72, 150, 300], help="Píxeles por pulgada")
        
    st.markdown("<br><br><br><br>", unsafe_allow_html=True)
    st.markdown("<div style='text-align: center; color: #888888; font-size: 13px; font-weight: 300;'>Desarrollado por Silvia Fernández ✨</div>", unsafe_allow_html=True)

st.header("📂 Subir Archivos")

archivos_subidos = st.file_uploader("Arrastra aquí tus imágenes (JPG, PNG o WEBP)", type=['jpg', 'jpeg', 'png', 'webp'], accept_multiple_files=True, key=st.session_state.uploader_key)

col_btn1, col_btn2 = st.columns([1, 1])
with col_btn1:
    btn_procesar = st.button("🚀 Iniciar Procesamiento", type="primary", disabled=hay_error_margenes, use_container_width=True)
with col_btn2:
    st.button("🧹 Limpiar cola de archivos", on_click=limpiar_cola, use_container_width=True)

# ==========================================
#  MOTOR DE PROCESAMIENTO
# ==========================================
if btn_procesar:
    
    if not archivos_subidos:
        st.warning("⚠️ No has subido ninguna imagen.")
    else:
        archivo_zip_memoria = io.BytesIO()
        barra_progreso = st.progress(0)
        texto_estado = st.empty()
        
        with zipfile.ZipFile(archivo_zip_memoria, "w") as zip_final:
            total_fotos = len(archivos_subidos)
            
            for indice, archivo in enumerate(archivos_subidos):
                texto_estado.text(f"⏳ Procesando: {archivo.name} ({indice + 1}/{total_fotos})...")
                
                try:
                    # 0. EXTRACCIÓN DEL PERFIL DE COLOR ORIGINAL
                    foto_bytes = archivo.getvalue()
                    img_original_temp = Image.open(io.BytesIO(foto_bytes))
                    perfil_icc_original = img_original_temp.info.get('icc_profile')
                    
                    # Llamada a la IA
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
                    
                    # Si tiene perfil de color (sRGB, AdobeRGB, etc), se guarda para inyectarlo
                    if perfil_icc_original:
                        parametros_guardado["icc_profile"] = perfil_icc_original
                        
                    if "PNG" in formato_salida:
                        # Lienzo Transparente
                        lienzo = Image.new("RGBA", (ancho_lienzo, alto_lienzo), (255, 255, 255, 0))
                        lienzo.paste(prenda_escalada, (pos_x, pos_y), prenda_escalada)
                        
                        parametros_guardado["format"] = "PNG"
                        extension = "png"
                    else:
                        # Lienzo JPG con color
                        lienzo = Image.new("RGB", (ancho_lienzo, alto_lienzo), color_fondo)
                        lienzo.paste(prenda_escalada, (pos_x, pos_y), prenda_escalada)
                        
                        parametros_guardado["format"] = "JPEG"
                        parametros_guardado["quality"] = 95
                        extension = "jpg"
                    
                    imagen_final_bytes = io.BytesIO()
                    lienzo.save(imagen_final_bytes, **parametros_guardado)
                    
                    nombre_sin_extension = archivo.name.rsplit('.', 1)[0]
                    zip_final.writestr(f"{nombre_sin_extension}_procesada.{extension}", imagen_final_bytes.getvalue())
                        
                except Exception as e:
                    st.error(f"Error procesando '{archivo.name}': {e}")
                
                barra_progreso.progress((indice + 1) / total_fotos)
        
        texto_estado.success("✨ ¡Lote procesado con éxito!")
        
        st.download_button(
            label="📦 Descargar todas las imágenes en ZIP",
            data=archivo_zip_memoria.getvalue(),
            file_name="imagenes_procesadas.zip",
            mime="application/zip",
            type="primary"
        )
