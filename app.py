import streamlit as st
import requests
from PIL import Image
import io
import zipfile
import base64
import time
import json
import os

# ==========================================
#  FUNCIONES DEL BACKEND
# ==========================================
def procesar_con_modelia(archivo):
    try:
        api_key = st.secrets["API_KEY_MODELIA"]
    except:
        raise Exception("Falta la API_KEY_MODELIA en la carpeta .streamlit/secrets.toml")

    base_url = "https://modelia.ai"
    headers = {"Content-Type": "application/json", "X-API-Key": api_key}
    
    foto_bytes = archivo.getvalue()
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
#  GESTIÓN DE PLANTILLAS
# ==========================================
ARCHIVO_PLANTILLAS = "plantillas.json"

def cargar_plantillas():
    if os.path.exists(ARCHIVO_PLANTILLAS):
        with open(ARCHIVO_PLANTILLAS, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def guardar_plantillas(plantillas):
    with open(ARCHIVO_PLANTILLAS, "w", encoding="utf-8") as f:
        json.dump(plantillas, f, indent=4)

plantillas = cargar_plantillas()

defaults = {
    'ancho_lienzo': 1200, 'alto_lienzo': 1200,
    'margen_arriba': 100, 'margen_abajo': 100,
    'margen_izquierda': 100, 'margen_derecha': 100,
    'color_fondo': "#FFFFFF"
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

def aplicar_plantilla():
    seleccion = st.session_state.selector_plantilla
    if seleccion and seleccion in plantillas:
        p = plantillas[seleccion]
        for key in defaults.keys():
            if key in p: st.session_state[key] = p[key]

# ==========================================
#  INTERFAZ DE USUARIO (FRONTEND)
# ==========================================
st.set_page_config(page_title="Background Remover", page_icon="✂️", layout="centered")
st.title("Background Remover")
st.write("Procesamiento masivo inteligente. Escala matemáticamente y ancla cada foto de forma autónoma según sus cortes originales.")

with st.sidebar:
    st.header("📂 Mis Plantillas")
    opciones_plantillas = ["-- Seleccionar Plantilla --"] + list(plantillas.keys())
    st.selectbox("Cargar configuración", opciones_plantillas, key="selector_plantilla", on_change=aplicar_plantilla)
    
    with st.expander("➕ Guardar configuración actual"):
        nombre_nueva_plantilla = st.text_input("Nombre (ej: Camisetas Mujer)")
        if st.button("Guardar Plantilla", use_container_width=True):
            if nombre_nueva_plantilla:
                plantillas[nombre_nueva_plantilla] = {k: st.session_state[k] for k in defaults.keys()}
                guardar_plantillas(plantillas)
                st.success("¡Plantilla guardada!")
                time.sleep(1)
                st.rerun()
            else:
                st.warning("Escribe un nombre.")
    
    st.divider()

    st.header("📏 Dimensiones del Lienzo")
    col_dim1, col_dim2 = st.columns(2)
    with col_dim1: ancho_lienzo = st.number_input("Ancho Total (px)", min_value=100, max_value=4000, key="ancho_lienzo")
    with col_dim2: alto_lienzo = st.number_input("Alto Total (px)", min_value=100, max_value=4000, key="alto_lienzo")
    
    st.header("🔲 Márgenes")
    st.info("💡 Si pones 0px, las zonas cortadas de la foto original se pegarán como imanes a ese margen.")
    col_marg1, col_marg2 = st.columns(2)
    with col_marg1:
        margen_arriba = st.number_input("Arriba (px)", min_value=0, max_value=4000, key="margen_arriba")
        margen_izquierda = st.number_input("Izquierda (px)", min_value=0, max_value=4000, key="margen_izquierda")
    with col_marg2:
        margen_abajo = st.number_input("Abajo (px)", min_value=0, max_value=4000, key="margen_abajo")
        margen_derecha = st.number_input("Derecha (px)", min_value=0, max_value=4000, key="margen_derecha")
        
    # ---  MATEMÁTICA (Validación en tiempo real) ---
    espacio_util_w = ancho_lienzo - margen_izquierda - margen_derecha
    espacio_util_h = alto_lienzo - margen_arriba - margen_abajo
    
    hay_error_margenes = False
    if espacio_util_w <= 0 or espacio_util_h <= 0:
        hay_error_margenes = True
        st.error("❌ ¡Error matemático! Los márgenes que has puesto son mayores o iguales al tamaño del lienzo. No hay espacio físico para meter la foto. Por favor, redúcelos.")

    st.header("🎨 Color de Fondo")
    color_fondo = st.color_picker("Haz clic para abrir la paleta", key="color_fondo")

    st.divider()

    st.header("💾 Exportación")
    col_exp1, col_exp2 = st.columns(2)
    with col_exp1: formato_salida = st.selectbox("Formato", ["JPG"], help="Exportación optimizada")
    with col_exp2: ppp_salida = st.selectbox("Resolución", [72], help="Píxeles por pulgada")
        
    st.markdown("<br><br><br><br>", unsafe_allow_html=True)
    st.markdown("<div style='text-align: center; color: #888888; font-size: 13px; font-weight: 300;'>Desarrollado por Silvia Fernández ✨</div>", unsafe_allow_html=True)

st.header("📂 Subir Archivos")
archivos_subidos = st.file_uploader("Arrastra aquí tus imágenes (JPG o PNG)", type=['jpg', 'jpeg', 'png'], accept_multiple_files=True)

# ==========================================
#  MOTOR DE PROCESAMIENTO
# ==========================================
# Fíjate que al botón le pasamos "disabled=hay_error_margenes". Si hay error, no se puede clicar.
if st.button("🚀 Iniciar Procesamiento", type="primary", disabled=hay_error_margenes):
    
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
                    imagen_bytes = procesar_con_modelia(archivo)
                    
                    # 1. ANÁLISIS 360º DE LA IMAGEN ORIGINAL
                    img_rgba = Image.open(io.BytesIO(imagen_bytes)).convert("RGBA")
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
                    
                    # Eje X
                    if is_cut_right and not is_cut_left:
                        pos_x = ancho_lienzo - margen_derecha - nuevo_ancho
                    elif is_cut_left and not is_cut_right:
                        pos_x = margen_izquierda
                    else:
                        pos_x = margen_izquierda + (espacio_util_w - nuevo_ancho) // 2

                    # Eje Y
                    if is_cut_bottom and not is_cut_top:
                        pos_y = alto_lienzo - margen_abajo - nuevo_alto
                    elif is_cut_top and not is_cut_bottom:
                        pos_y = margen_arriba
                    else:
                        pos_y = margen_arriba + (espacio_util_h - nuevo_alto) // 2
                    
                    # 4. PEGADO Y GUARDADO
                    lienzo = Image.new("RGB", (ancho_lienzo, alto_lienzo), color_fondo)
                    lienzo.paste(prenda_escalada, (pos_x, pos_y), prenda_escalada)
                    
                    imagen_final_bytes = io.BytesIO()
                    lienzo.save(imagen_final_bytes, format="JPEG", quality=95, dpi=(ppp_salida, ppp_salida))
                    
                    nombre_sin_extension = archivo.name.rsplit('.', 1)[0]
                    zip_final.writestr(f"{nombre_sin_extension}_procesada.jpg", imagen_final_bytes.getvalue())
                        
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