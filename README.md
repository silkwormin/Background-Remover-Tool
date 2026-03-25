# ✂️ Background Remover Tool (Pro Edition)

Una aplicación web profesional y automatizada construida con **Streamlit** y Python para el procesamiento masivo de imágenes de e-commerce y catálogos. 

La herramienta se encarga de eliminar fondos (usando la API de Modelia), reescalar estrictamente sin deformar y componer la imagen final garantizando que los colores se mantengan intactos y las extremidades cortadas se anclen de forma natural.

## ✨ Características Principales

* **Procesamiento por Lotes (Multi-formato):** Sube múltiples imágenes al mismo tiempo, incluyendo soporte total para formatos de nueva generación fotográfica como **WEBP**, además de los clásicos JPG y PNG.
* **Limpieza Rápida de Cola (Gestión de Memoria):** Un botón dedicado ("🧹 Limpiar cola de archivos") para vaciar el cajón de subida al instante y preparar el entorno para la siguiente tanda de catálogo, ahorrando clics innecesarios.
* **Anclaje Inteligente (Smart Bleed Detection):** El algoritmo escanea la foto original en 360º. Si detecta que una prenda o extremidad (brazo, pierna) tocaba el borde, la "imanta" matemáticamente a ese mismo borde en el lienzo final para evitar que quede flotando en el vacío.
* **Plantillas Industriales Integradas:** Formatos preconfigurados a un solo clic para los estándares más usados: *Shopify (900x1125)*, *Kings (700x1000)* y *Cuadrado Universal (1200x1200)*, con versiones específicas para modelo (sin márgenes) o prenda (con márgenes).
* **Escalado Proporcional Estricto:** Ajusta los productos al área útil del lienzo respetando el *aspect ratio* (proporción) original a través de remuestreo de alta calidad fotográfica (Filtro Lanczos). **Jamás deforma la imagen.**
* **Preservación de Perfil de Color (ICC):** Extrae de la foto original el perfil de color (ej. sRGB, Display P3) y lo inyecta en el lienzo final procesado para asegurar un contraste 100% idéntico, evitando colores lavados.
* **Exportación Transparente o Sólida:** Elige entre exportar en `PNG` puro con canal Alfa (100% transparente) o en `JPG` optimizado con el fondo de color hexagonal que elijas. Todas se entregan en un archivo `.zip` unificado.

## 🛠️ Tecnologías Utilizadas

* **[Streamlit](https://streamlit.io/):** Motor de la interfaz gráfica e interactividad web.
* **[Pillow (PIL)](https://python-pillow.org/):** Core de manipulación fotográfica, gestión de Bounding Boxes, inyección ICC y composición RGBA.
* **[Requests](https://pypi.org/project/requests/):** Conexión HTTP segura con la API externa.
* **Modelia API:** Red neuronal especializada en la extracción ultra-precisa de fondos.
