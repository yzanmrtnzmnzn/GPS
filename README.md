<div align="center">

# 🛰️ Prácticas GPS — Sistemas de Navegación

📡 Lectura por **puerto serie** · 🌍 Conversión a **UTM** · 🗺️ Visualización en mapa georreferenciado · 🚗 Sistemas de ayuda al conductor

</div>

---

# 🧪 Práctica 1 — GPS (NMEA GGA → Lat/Lon → UTM)

📡 Lectura por **puerto serie** · 🔎 Detección automática de **COM** · 🌍 Conversión a **UTM** implementada en código (sin librerías externas)

---

## 📌 Vista rápida

| Módulo | Qué hace | Entrada | Salida |
|---|---|---|---|
| 🧪 **RAW** | Comprueba si el GPS **emite datos** | Puerto serie | Tramas NMEA en consola |
| 🔎 **Auto-COM** | Encuentra el **puerto correcto** (COM3/COM6/…) | Puertos del sistema | Puerto detectado + NMEA |
| 🧭 **Práctica 1** | `$GPGGA/$GNGGA` → Lat/Lon → **UTM** (WGS84) | Trama GGA | Lat/Lon + UTM + calidad fix |

---

## ⚙️ Configuración del puerto serie

| Parámetro | Valor |
|---|---|
| Velocidad | **4800 bps** |
| Bits de datos | **8** |
| Paridad | **Ninguno (None)** |
| Bits de parada | **1** |
| Control de flujo | **Ninguno** |

---

## ✨ Funcionalidades

✅ Detecta automáticamente el puerto donde esté conectado el GPS (COM3, COM6, …)  
✅ Lee tramas NMEA y filtra **GGA** (`$GPGGA` / `$GNGGA`)  
✅ Extrae **hora**, **latitud**, **longitud**, **fix**, **satélites**, **HDOP** y **altitud**  
✅ Convierte **ddmm.mmmm / dddmm.mmmm → grados decimales**  
✅ Convierte **Lat/Lon → UTM** con **fórmula programada** (sin librerías externas)  

---

# 🗺️ Práctica 2 — Mapa electrónico (GPS → UTM → Visualización)

📍 Representación en **tiempo real** sobre mapa · 🖼️ Imagen **georreferenciada** · 🧭 Visualización tipo navegador

---

## 📌 Vista rápida

| Módulo | Qué hace | Entrada | Salida |
|---|---|---|---|
| 🧭 **GPS** | Obtiene posición desde GGA | Trama NMEA | Lat/Lon + UTM |
| 🗺️ **Mapa** | Carga imagen de Google Earth | Archivo `.png` | Mapa en pantalla |
| 📍 **Georef** | Convierte UTM → píxeles | Coordenadas UTM | Posición en imagen |
| 🚗 **Visualización** | Muestra posición en tiempo real | UTM + mapa | Punto GPS + trayectoria |

---

## ⚙️ Configuración del sistema

| Elemento | Descripción |
|---|---|
| Imagen | Captura de **Google Earth (Campus Sur / INSIA)** |
| Sistema de coordenadas | **UTM (WGS84, zona 30)** |
| Georreferenciación | Transformación afín con **3 puntos de control** |
| Interfaz | Ventana gráfica con **Tkinter** |

---

## ✨ Funcionalidades

✅ Carga una imagen estática del mapa (Google Earth)  
✅ Georreferencia la imagen usando **3 puntos conocidos (UTM ↔ píxel)**  
✅ Convierte la posición GPS a coordenadas UTM (Práctica 1)  
✅ Proyecta la posición sobre la imagen en tiempo real  
✅ Muestra información del GPS (fix, satélites, altitud, coordenadas)  
✅ Dibuja la **trayectoria del vehículo** sobre el mapa  
✅ Indica si la posición está dentro o fuera del mapa  

---

## 🧠 Georreferenciación

Se utilizan **3 puntos de control** para relacionar coordenadas reales con píxeles:

```python
CONTROL_POINTS = [
    {"pixel": (x1, y1), "utm": (E1, N1)},
    {"pixel": (x2, y2), "utm": (E2, N2)},
    {"pixel": (x3, y3), "utm": (E3, N3)},
]
```

---

# 🚦 Práctica 3 — Sistema de aviso al conductor (INSIA)

🚗 Mapa electrónico vectorial · ⚠️ Control de velocidad · 🧭 Detección de sentido de circulación · 📍 Seguimiento GPS en tiempo real

---

## 📌 Vista rápida

| Módulo | Qué hace | Entrada | Salida |
|---|---|---|---|
| 🛰️ **GPS** | Lee datos GGA desde el receptor | Puerto serie | Lat/Lon + UTM |
| 🛣️ **Mapa INSIA** | Carga el circuito electrónico | Coordenadas UTM | Circuito vectorial |
| 📍 **Matching** | Encuentra el punto más cercano de la pista | Posición GPS | Distancia al trazado |
| 🚦 **Avisador** | Compara velocidad real con límite permitido | Velocidad + tramo | Aviso visual |
| 🧭 **Dirección** | Detecta el sentido de circulación | Movimiento del vehículo | Sentido correcto / contrario |

---

## ⚙️ Características principales

| Elemento | Descripción |
|---|---|
| Circuito | Mapa electrónico INSIA v2.0 |
| Coordenadas | UTM WGS84 |
| Interfaz gráfica | Tkinter |
| Límite de pista | Distancia máxima configurable respecto al trazado |
| Velocidad | Calculada en tiempo real mediante GPS |

---

## ✨ Funcionalidades

✅ Representación vectorial completa del circuito INSIA  
✅ Cálculo de velocidad instantánea del vehículo  
✅ Suavizado de velocidad mediante filtrado simple  
✅ Comparación entre velocidad actual y velocidad límite del tramo  
✅ Sistema de alertas:
- 🟢 Velocidad correcta
- 🟡 Cercano al límite
- 🔴 Exceso de velocidad

✅ Detección de conducción en sentido correcto o contrario  
✅ Dibujo de la trayectoria en tiempo real sobre el circuito  
✅ Compatibilidad con GPS real y modo de simulación (`USE_FAKE_GPS`)  
✅ Visualización de coordenadas, satélites y calidad del fix GPS  

---

## 🧠 Funcionamiento del mapa electrónico

El sistema utiliza un conjunto de puntos UTM que representan el circuito INSIA.  
Cada tramo tiene asociado un límite de velocidad máximo.

El programa:

1. Obtiene la posición GPS del vehículo.
2. Convierte la posición a coordenadas UTM.
3. Busca el segmento más cercano del circuito.
4. Calcula la distancia respecto a la pista.
5. Obtiene la velocidad permitida de ese tramo.
6. Genera avisos visuales según la velocidad actual.

---

# 🌍 Práctica 4 — Servicio georreferenciado con IGN

🛰️ Integración con servicios cartográficos reales · 🗺️ Mapas dinámicos del IGN · 📦 Caché de imágenes · 📍 Navegación avanzada

---

## 📌 Vista rápida

| Módulo | Qué hace | Entrada | Salida |
|---|---|---|---|
| 🌍 **IGN WMS** | Descarga mapas reales desde el IGN | Coordenadas GPS | Imagen dinámica |
| 🗺️ **Mercator** | Convierte coordenadas para el mapa | Lat/Lon | Posición global |
| 📦 **Caché** | Guarda imágenes recientes | Peticiones WMS | Mejor rendimiento |
| 🚗 **Navegación** | Centra y actualiza el mapa automáticamente | Movimiento GPS | Seguimiento en tiempo real |
| 📁 **Caja negra** | Guarda datos del recorrido | GPS + velocidad | Archivo CSV |

---

## ⚙️ Tecnologías utilizadas

| Elemento | Descripción |
|---|---|
| Servicio cartográfico | IGN WMS (PNOA) |
| Proyección | Web Mercator |
| Interfaz gráfica | Tkinter + PIL |
| Almacenamiento | CSV tipo “caja negra” |
| Caché | LRU Cache para imágenes y tiles |

---

## ✨ Funcionalidades

✅ Descarga automática de ortofotos reales desde el IGN  
✅ Visualización dinámica del mapa centrada en el vehículo  
✅ Conversión entre coordenadas GPS, UTM y Web Mercator  
✅ Sistema de doble buffer para evitar parpadeos  
✅ Caché inteligente de mapas para mejorar el rendimiento  
✅ Seguimiento automático del vehículo en pantalla  
✅ Registro completo del recorrido en un archivo CSV  
✅ Sistema de “caja negra” con:
- Posición GPS
- Velocidad
- Límite del tramo
- Distancia al circuito
- Estado de aviso
- Satélites y calidad GPS

✅ Compatibilidad con GPS real y simulación  
✅ Detección de exceso de velocidad y sentido de circulación  

---

## 🧠 Arquitectura del sistema

La práctica 4 combina varios módulos avanzados:

- 📡 Lectura GPS mediante puerto serie.
- 🌍 Descarga de mapas desde servicios WMS reales.
- 🧭 Conversión geográfica entre distintos sistemas de coordenadas.
- 🚗 Representación dinámica del vehículo sobre ortofotografía real.
- 📁 Registro persistente del recorrido en formato CSV.

El sistema se comporta de manera similar a un navegador GPS simplificado.

---

# 🧩 Tecnologías utilizadas

| Tecnología | Uso |
|---|---|
| 🐍 Python | Desarrollo completo del sistema |
| 🛰️ PySerial | Comunicación con GPS |
| 🖼️ PIL / Pillow | Gestión de imágenes |
| 🪟 Tkinter | Interfaz gráfica |
| 🌍 WMS IGN | Mapas reales georreferenciados |
| 📐 Matemáticas UTM | Conversión geodésica |

---

# 🎓 Reflexión sobre la asignatura

Esta asignatura ha permitido aplicar conceptos teóricos de navegación, posicionamiento y representación geográfica en proyectos reales y funcionales.  

A lo largo de las prácticas se han trabajado aspectos muy importantes como:

- 📡 Comunicación con dispositivos GPS reales.
- 🌍 Conversión entre distintos sistemas de coordenadas.
- 🗺️ Georreferenciación y representación cartográfica.
- 🚗 Sistemas de ayuda a la conducción.
- 🧠 Procesamiento de datos en tiempo real.
- 💻 Desarrollo completo de aplicaciones gráficas en Python.

Además de la parte técnica, las prácticas ayudan a comprender cómo funcionan internamente muchos sistemas actuales de navegación y asistencia al conductor.  

La evolución entre prácticas también muestra una progresión clara: desde leer una trama GPS básica hasta construir un sistema avanzado capaz de visualizar mapas reales, detectar velocidad, registrar recorridos y seguir un vehículo dinámicamente sobre ortofotografías del IGN.

En conjunto, la asignatura aporta una visión muy práctica y aplicada de los sistemas de navegación modernos.

