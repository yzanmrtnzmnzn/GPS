<div align="center">

# 🛰️ Práctica 1 — GPS (NMEA GGA → Lat/Lon → UTM)

📡 Lectura por **puerto serie** · 🔎 Detección automática de **COM** · 🌍 Conversión a **UTM** implementada en código (sin librerías de conversión)

</div>

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
✅ Convierte **Lat/Lon → UTM** con **fórmula programada** (sin `utm`)  

---
