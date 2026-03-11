import math
import time
import queue
import threading
import serial

# -------------------------
# CONFIGURACIÓN PUERTO SERIE
# -------------------------
PORT = "COM3"
BAUDRATE = 4800
TIMEOUT_S = 1

# -------------------------
# CONSTANTES WGS84
# -------------------------
A_WGS84 = 6378137.0
E2_WGS84 = 0.00669437999013
K0 = 0.9996


# -------------------------
# 1) Parsear GGA -> lat/lon
# -------------------------
def nmea_dm_to_deg(dm: str, hemi: str, is_lat: bool) -> float:
    """
    Convierte coordenadas NMEA:
    - latitud:  ddmm.mmmm
    - longitud: dddmm.mmmm
    """
    if is_lat:
        deg = int(dm[0:2])
        minutes = float(dm[2:])
    else:
        deg = int(dm[0:3])
        minutes = float(dm[3:])

    val = deg + minutes / 60.0

    if hemi in ("S", "W"):
        val *= -1.0

    return val


def parse_gga(line: str):
    """
    Devuelve:
    (lat_deg, lon_deg, fix_quality, num_sats, altitude_m)
    o None si la línea no es válida.
    """
    if not (line.startswith("$GPGGA") or line.startswith("$GNGGA")):
        return None

    parts = line.split(",")
    if len(parts) < 10:
        return None

    lat_raw = parts[2]
    lat_hemi = parts[3]
    lon_raw = parts[4]
    lon_hemi = parts[5]
    fix_quality = parts[6]
    num_sats = parts[7]
    altitude = parts[9]

    if not lat_raw or not lon_raw:
        return None

    lat = nmea_dm_to_deg(lat_raw, lat_hemi, is_lat=True)
    lon = nmea_dm_to_deg(lon_raw, lon_hemi, is_lat=False)

    try:
        fq = int(fix_quality) if fix_quality else 0
    except ValueError:
        fq = 0

    try:
        ns = int(num_sats) if num_sats else 0
    except ValueError:
        ns = 0

    try:
        alt = float(altitude) if altitude else float("nan")
    except ValueError:
        alt = float("nan")

    return lat, lon, fq, ns, alt


# -------------------------
# 2) Conversión a UTM
# -------------------------
def utm_zone_from_lon(lon_deg: float) -> int:
    return int((lon_deg + 180.0) / 6.0) + 1


def latlon_to_utm_wgs84(lat_deg: float, lon_deg: float, force_zone=None):
    """
    Conversión a UTM usando WGS84.
    Devuelve: (Easting, Northing, zone, hemisphere)
    """
    a = A_WGS84
    e2 = E2_WGS84
    k0 = K0

    ep2 = e2 / (1.0 - e2)

    zone = force_zone if force_zone is not None else utm_zone_from_lon(lon_deg)
    hemi = "N" if lat_deg >= 0 else "S"

    lat = math.radians(lat_deg)
    lon = math.radians(lon_deg)

    lon0_deg = (zone - 1) * 6 - 180 + 3
    lon0 = math.radians(lon0_deg)

    sin_lat = math.sin(lat)
    cos_lat = math.cos(lat)
    tan_lat = math.tan(lat)

    N = a / math.sqrt(1.0 - e2 * sin_lat * sin_lat)
    T = tan_lat * tan_lat
    C = ep2 * cos_lat * cos_lat
    A = cos_lat * (lon - lon0)

    # Arco meridiano
    M = a * (
        (1 - e2 / 4 - 3 * e2**2 / 64 - 5 * e2**3 / 256) * lat
        - (3 * e2 / 8 + 3 * e2**2 / 32 + 45 * e2**3 / 1024) * math.sin(2 * lat)
        + (15 * e2**2 / 256 + 45 * e2**3 / 1024) * math.sin(4 * lat)
        - (35 * e2**3 / 3072) * math.sin(6 * lat)
    )

    # Easting
    easting = k0 * N * (
        A
        + (1 - T + C) * A**3 / 6
        + (5 - 18 * T + T**2 + 72 * C - 58 * ep2) * A**5 / 120
    ) + 500000.0

    # Northing
    northing = k0 * (
        M + N * tan_lat * (
            A**2 / 2
            + (5 - T + 9 * C + 4 * C**2) * A**4 / 24
            + (61 - 58 * T + T**2 + 600 * C - 330 * ep2) * A**6 / 720
        )
    )

    if hemi == "S":
        northing += 10000000.0

    return easting, northing, zone, hemi


# -------------------------
# 3) Hilo lector GPS
# -------------------------
def gps_reader(port, data_queue, stop_event):
    """
    Lee continuamente del GPS en un hilo separado
    y mete las tramas válidas GGA en una cola.
    """
    try:
        ser = serial.Serial(
            port=port,
            baudrate=BAUDRATE,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=TIMEOUT_S,
        )
    except serial.SerialException as e:
        print(f"Error al abrir el puerto {port}: {e}")
        return

    print(f"GPS conectado en {port}")
    print("Leyendo tramas GGA...\n")

    try:
        while not stop_event.is_set():
            try:
                line = ser.readline().decode(errors="ignore").strip()
            except Exception:
                continue

            if not line:
                time.sleep(0.01)
                continue

            gga = parse_gga(line)
            if gga is not None:
                data_queue.put(gga)

    finally:
        ser.close()
        print("Puerto serie cerrado.")


# -------------------------
# 4) Programa principal
# -------------------------
def main():
    data_queue = queue.Queue()
    stop_event = threading.Event()

    gps_thread = threading.Thread(
        target=gps_reader,
        args=(PORT, data_queue, stop_event),
        daemon=True
    )
    gps_thread.start()

    try:
        while True:
            try:
                lat, lon, fix_q, sats, alt = data_queue.get(timeout=1)
            except queue.Empty:
                continue

            E, N, zone, hemi = latlon_to_utm_wgs84(lat, lon, force_zone=None)

            print(f"GGA OK | fix={fix_q} sats={sats} alt={alt:.2f} m")
            print(f"Lat/Lon: {lat:.8f}, {lon:.8f}")
            print(f"UTM: E={E:.3f} m  N={N:.3f} m  Zona={zone}{hemi}")
            print("-" * 40)

            # pequeña pausa para no cargar el hilo principal
            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\nDeteniendo programa...")

    finally:
        stop_event.set()
        gps_thread.join(timeout=2)


if __name__ == "__main__":
    main()