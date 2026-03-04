import math
import time
import serial
from serial.tools import list_ports

BAUDRATE = 4800
TIMEOUT_S = 1
SCAN_SECONDS_PER_PORT = 2.0


# -------------------------
# 1) GPS: detectar puerto
# -------------------------
def looks_like_nmea(line: str) -> bool:
    line = line.strip()
    return line.startswith("$GP") or line.startswith("$GN")


def find_gps_port(baudrate: int = BAUDRATE) -> str:
    ports = list(list_ports.comports())
    if not ports:
        raise RuntimeError("No se detecta ningún puerto serie en el sistema.")

    for p in ports:
        port_name = p.device
        try:
            with serial.Serial(
                port=port_name,
                baudrate=baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=TIMEOUT_S,
            ) as ser:
                start = time.time()
                while time.time() - start < SCAN_SECONDS_PER_PORT:
                    raw = ser.readline()
                    if not raw:
                        continue
                    line = raw.decode(errors="ignore").strip()
                    if looks_like_nmea(line):
                        return port_name
        except (serial.SerialException, OSError):
            continue

    raise RuntimeError("No se encontró ningún puerto que emita tramas NMEA.")


# -------------------------
# 2) Parsear GGA -> lat/lon
# -------------------------
def nmea_dm_to_deg(dm: str, hemi: str, is_lat: bool) -> float:
    """
    dm: ddmm.mmmm (lat) o dddmm.mmmm (lon)
    hemi: N/S/E/W
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
    Devuelve (lat_deg, lon_deg, fix_quality, num_sats, altitude_m) o None si no sirve.
    """
    if not (line.startswith("$GPGGA") or line.startswith("$GNGGA")):
        return None

    parts = line.split(",")
    if len(parts) < 10:
        return None

    lat_raw, lat_hemi = parts[2], parts[3]
    lon_raw, lon_hemi = parts[4], parts[5]
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
# 3) UTM “a mano” (WGS84)
# -------------------------
def utm_zone_from_lon(lon_deg: float) -> int:
    # zona estándar UTM: 1..60
    return int((lon_deg + 180.0) / 6.0) + 1


def latlon_to_utm_wgs84(lat_deg: float, lon_deg: float, force_zone: int | None = None):
    """
    Conversión a UTM usando WGS84 (Transverse Mercator).
    Devuelve: (Easting, Northing, zone, hemisphere)
    """
    # WGS84: a y f según práctica (WGS84 a=6378137; f=1/298.25722) :contentReference[oaicite:5]{index=5}
    a = 6378137.0
    f = 1.0 / 298.25722
    k0 = 0.9996

    e2 = f * (2.0 - f)              # excentricidad^2
    ep2 = e2 / (1.0 - e2)           # e'^2

    zone = force_zone if force_zone is not None else utm_zone_from_lon(lon_deg)
    hemi = "N" if lat_deg >= 0 else "S"

    lat = math.radians(lat_deg)
    lon = math.radians(lon_deg)

    # meridiano central de la zona
    lon0_deg = (zone - 1) * 6 - 180 + 3
    lon0 = math.radians(lon0_deg)

    sin_lat = math.sin(lat)
    cos_lat = math.cos(lat)
    tan_lat = math.tan(lat)

    N = a / math.sqrt(1.0 - e2 * sin_lat * sin_lat)
    T = tan_lat * tan_lat
    C = ep2 * cos_lat * cos_lat
    A = cos_lat * (lon - lon0)

    # M: arco meridiano (serie)
    M = a * (
        (1 - e2/4 - 3*e2**2/64 - 5*e2**3/256) * lat
        - (3*e2/8 + 3*e2**2/32 + 45*e2**3/1024) * math.sin(2*lat)
        + (15*e2**2/256 + 45*e2**3/1024) * math.sin(4*lat)
        - (35*e2**3/3072) * math.sin(6*lat)
    )

    # Easting
    easting = k0 * N * (
        A
        + (1 - T + C) * A**3 / 6
        + (5 - 18*T + T**2 + 72*C - 58*ep2) * A**5 / 120
    ) + 500000.0

    # Northing
    northing = k0 * (
        M + N * tan_lat * (
            A**2 / 2
            + (5 - T + 9*C + 4*C**2) * A**4 / 24
            + (61 - 58*T + T**2 + 600*C - 330*ep2) * A**6 / 720
        )
    )

    if hemi == "S":
        northing += 10000000.0

    return easting, northing, zone, hemi


def main():
    port = find_gps_port()
    print(f"✅ GPS detectado en: {port}")

    ser = serial.Serial(
        port=port,
        baudrate=BAUDRATE,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        timeout=TIMEOUT_S,
    )

    print("Leyendo GGA y convirtiendo a UTM (Ctrl+C para parar)...\n")

    try:
        while True:
            line = ser.readline().decode(errors="ignore").strip()
            if not line:
                continue

            gga = parse_gga(line)
            if gga is None:
                continue

            lat, lon, fix_q, sats, alt = gga

            # Si quieres forzar huso 30 en España, pon force_zone=30
            E, N, zone, hemi = latlon_to_utm_wgs84(lat, lon, force_zone=None)

            print(f"GGA OK | fix={fix_q} sats={sats} alt={alt:.2f} m")
            print(f"Lat/Lon: {lat:.8f}, {lon:.8f}")
            print(f"UTM: E={E:.3f} m  N={N:.3f} m  Zona={zone}{hemi}")
            print("-" * 40)

    finally:
        ser.close()


if __name__ == "__main__":
    main()