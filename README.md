# 🛰️ Práctica 1 — Posicionamiento GPS (NMEA GGA → Lat/Lon → UTM)

Aplicación en **Python** que lee un receptor **GPS por puerto serie** (NMEA), detecta tramas **`$GPGGA` / `$GNGGA`**, extrae **latitud/longitud** y (opcional) convierte la posición a **UTM** implementando la **fórmula en código** (sin librerías de conversión).

---

## ✨ Qué hace

✅ Detecta automáticamente el **puerto COM** donde está conectado el GPS (ej. COM3, COM6, etc.)  
✅ Lee tramas NMEA a **4800 bps** (8N1, sin flujo)  
✅ Filtra y parsea tramas **GGA**  
✅ Convierte:
- NMEA `ddmm.mmmm` / `dddmm.mmmm` → **grados decimales**
- (Opcional) Grados decimales → **UTM** (WGS84, Transverse Mercator) **programado a mano**

---

## ⚙️ Configuración del puerto serie (requerida)

- **Velocidad**: 4800 bps  
- **Bits de datos**: 8  
- **Paridad**: None  
- **Bits de parada**: 1  
- **Control de flujo**: None
