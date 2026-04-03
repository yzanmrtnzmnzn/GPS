<div align="center">

# 🛰️ Prácticas GPS — Sistemas de Navegación

📡 Lectura por **puerto serie** · 🌍 Conversión a **UTM** · 🗺️ Visualización en mapa georreferenciado

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
