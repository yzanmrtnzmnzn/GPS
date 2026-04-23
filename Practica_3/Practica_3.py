import math
import time
import queue
import threading
from dataclasses import dataclass
from typing import List, Tuple, Optional

import serial
import tkinter as tk
from tkinter import ttk


# =========================================================
# CONFIGURACIÓN GENERAL
# =========================================================
PORT = "COM3"
BAUDRATE = 4800
TIMEOUT_S = 1

A_WGS84 = 6378137.0
E2_WGS84 = 0.00669437999013
K0 = 0.9996

WINDOW_TITLE = "Práctica 3 - Sistema de aviso al conductor (INSIA)"
MAP_CANVAS_SIZE = (620, 620)
MAX_TRAIL_POINTS = 400

# Si quieres probar sin GPS real, ponlo a True.
USE_FAKE_GPS = True

# Distancia máxima para considerar que el coche está en la pista
MAX_DISTANCE_TO_TRACK_M = 25.0

# Suavizado simple de velocidad
SPEED_ALPHA = 0.35


# =========================================================
# MAPA ELECTRÓNICO INSIA v2.0
# Formato: (UTM_Norte, UTM_Este, Velocidad_Máxima)
# =========================================================
INSIA_TRACK_RAW = """
4470971.219	446367.3453	10
4470971.974	446365.3701	10
4470972.542	446363.3937	10
4470972.927	446361.4159	10
4470973.495	446359.4395	10
4470973.88	446357.4617	10
4470974.452	446355.4853	10
4470974.833	446353.5076	10
4470975.217	446351.5298	10
4470975.602	446349.552	10
4470975.987	446347.5743	10
4470976.185	446345.4549	10
4470976.388	446343.3355	10
4470976.403	446341.2148	10
4470976.418	446339.0887	10
4470976.246	446336.9667	10
4470975.706	446334.9823	10
4470975.166	446332.998	10
4470973.887	446330.868	10
4470972.606	446328.8783	10
4470971.135	446327.3082	10
4470969.483	446325.8825	10
4470967.641	446324.4555	20
4470965.618	446323.0272	20
4470963.404	446321.7377	20
4470961.751	446320.5927	20
4470959.905	446319.5919	20
4470958.064	446318.4455	20
4470956.036	446317.2977	20
4470954.196	446316.1567	20
4470951.984	446315.0076	20
4470949.956	446313.8598	20
4470947.746	446312.5704	20
4470945.348	446311.4254	20
4470942.766	446310.2737	20
4470940.185	446308.9816	20
4470937.791	446307.691	20
4470935.395	446306.2599	20
4470932.815	446304.8276	20
4470930.235	446303.3952	20
4470928.393	446302.3891	20
4470926.551	446301.3884	20
4470924.706	446300.3822	20
4470922.864	446299.3815	20
4470921.207	446298.2363	20
4470919.181	446297.2289	20
4470917.336	446296.2281	20
4470915.311	446295.0804	20
4470913.466	446294.0796	20
4470911.441	446293.0721	20
4470909.413	446291.9298	20
4470907.384	446290.9223	20
4470905.356	446289.7745	20
4470903.332	446288.6321	20
4470901.304	446287.4844	20
4470899.092	446286.3353	20
4470896.881	446285.1862	20
4470894.853	446284.0438	20
4470892.642	446282.8947	20
4470890.614	446281.7469	20
4470888.403	446280.6032	20
4470886.191	446279.4541	20
4470883.98	446278.305	20
4470881.952	446277.1572	20
4470879.741	446276.0135	20
4470877.713	446274.8657	20
4470875.685	446273.7179	20
4470873.475	446272.4285	20
4470871.446	446271.4264	20
4470869.421	446270.2786	20
4470867.577	446269.1322	20
4470865.553	446267.9898	20
4470863.525	446266.842	20
4470861.683	446265.8412	20
4470859.655	446264.6935	20
4470857.814	446263.547	20
4470855.785	446262.5449	20
4470853.944	446261.3984	20
4470852.473	446259.974	20
4470850.632	446258.8275	20
4470848.052	446257.3952	20
4470846.21	446256.389	20
4470843.63	446254.9566	20
4470841.05	446253.5243	20
4470838.47	446252.0919	15
4470836.073	446250.8011	15
4470834.04	446250.3602	15
4470831.458	446249.2139	15
4470829.063	446248.0634	15
4470827.221	446247.203	15
4470824.637	446246.3318	15
4470822.235	446245.6077	15
4470819.466	446245.0212	15
4470817.061	446244.7233	15
4470814.472	446244.7048	15
4470811.881	446244.8265	15
4470809.658	446245.237	15
4470807.247	446245.7863	15
4470805.21	446246.4787	15
4470802.981	446247.31	15
4470800.94	446248.4287	15
4470799.078	446249.8292	15
4470797.218	446251.3701	15
4470795.356	446253.197	15
4470793.859	446255.1669	15
4470792.549	446257.2783	15
4470791.425	446259.5369	15
4470790.668	446261.7926	15
4470790.097	446264.1954	15
4470789.71	446266.4538	15
4470789.694	446268.7203	15
4470789.677	446270.9813	15
4470789.846	446273.1034	15
4470790.387	446275.3739	15
4470791.109	446277.4999	15
4470791.835	446279.626	15
4470792.932	446281.6144	15
4470794.214	446283.4638	15
4470795.867	446285.3158	15
4470797.516	446287.0222	15
4470799.541	446288.5963	15
4470801.752	446289.8857	15
4470804.15	446291.0308	15
4470806.546	446292.0409	15
4470809.318	446292.7677	15
4470812.275	446293.2152	15
4470814.494	446293.3713	15
4470816.529	446293.5262	15
4470818.561	446293.5408	15
4470820.597	446293.5553	15
4470822.816	446293.5712	15
4470825.037	446293.4468	15
4470827.074	446293.3211	15
4470829.482	446293.0523	15
4470831.703	446292.9279	15
4470834.108	446292.659	15
4470836.515	446292.536	15
4470838.737	446292.2712	15
4470841.145	446292.0025	15
4470843.736	446291.8807	15
4470846.14	446291.7576	15
4470848.732	446291.4955	15
4470851.14	446291.367	15
4470853.732	446291.105	15
4470856.323	446290.9832	15
4470858.728	446290.7144	15
4470861.319	446290.5926	15
4470863.91	446290.4708	15
4470866.501	446290.3491	15
4470869.092	446290.2219	15
4470871.683	446290.1001	15
4470874.272	446290.1187	15
4470877.05	446289.9983	15
4470879.64	446290.0168	15
4470882.414	446290.0366	15
4470885.003	446290.1955	15
4470887.779	446290.3557	18
4470890.55	446290.6615	18
4470893.138	446290.9606	18
4470895.909	446291.4068	18
4470898.495	446291.8516	18
4470901.268	446292.4327	18
4470904.036	446293.3052	18
4470906.621	446294.0306	18
4470909.391	446295.038	18
4470912.157	446296.0508	18
4470914.739	446297.1971	18
4470917.508	446298.3502	18
4470920.272	446299.6435	18
4470922.853	446300.9356	18
4470925.62	446302.3693	18
4470928.201	446303.6613	18
4470930.964	446305.095	18
4470933.544	446306.5273	18
4470936.124	446307.965	18
4470938.704	446309.2517	18
4470941.284	446310.6894	18
4470943.681	446312.1204	18
4470945.89	446313.5501	18
4470948.099	446314.9798	18
4470950.494	446316.1302	18
4470952.521	446317.4183	18
4470954.549	446318.5606	18
4470956.39	446319.7071	18
4470958.231	446320.8535	18
4470960.075	446321.9999	5
4470962.467	446323.5712	5
4470964.124	446324.7164	5
4470966.332	446326.4266	5
4470968.539	446328.1423	5
4470970.377	446330.136	5
4470971.84	446332.2672	5
4470972.935	446334.6819	5
4470973.656	446336.9482	5
4470974.196	446339.3589	5
4470974.363	446341.7615	5
4470974.346	446344.0279	5
4470974.148	446346.1473	5
4470973.763	446348.125	5
4470973.192	446350.5278	5
4470972.064	446352.7808	5
4470970.938	446354.8936	5
4470969.447	446356.5828	5
4470967.588	446357.9834	5
4470965.729	446358.8174	5
4470963.504	446359.6541	5
4470961.465	446360.4868	5
4470959.607	446361.3207	5
4470957.75	446362.4407	5
4470956.259	446364.1246	5
4470955.134	446366.097	5
4470954.934	446368.3621	5
4470955.474	446370.3465	5
4470956.757	446372.0502	5
4470958.414	446373.1953	5
4470960.44	446374.057	5
4470962.475	446374.2172	5
4470964.698	446373.8068	5
4470966.741	446372.8338	5
4470968.417	446371.2862	5
4470969.724	446369.7414	5
4470970.661	446367.9079	5
"""


# =========================================================
# UTILIDADES GPS / UTM
# =========================================================
def nmea_dm_to_deg(dm: str, hemi: str, is_lat: bool) -> float:
    if is_lat:
        deg = int(dm[0:2])
        minutes = float(dm[2:])
    else:
        deg = int(dm[0:3])
        minutes = float(dm[3:])

    value = deg + minutes / 60.0
    if hemi in ("S", "W"):
        value *= -1.0
    return value


def parse_gga(line: str):
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


def utm_zone_from_lon(lon_deg: float) -> int:
    return int((lon_deg + 180.0) / 6.0) + 1


def latlon_to_utm_wgs84(lat_deg: float, lon_deg: float, force_zone=None):
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

    n = a / math.sqrt(1.0 - e2 * sin_lat * sin_lat)
    t = tan_lat * tan_lat
    c = ep2 * cos_lat * cos_lat
    aa = cos_lat * (lon - lon0)

    m = a * (
        (1 - e2 / 4 - 3 * e2**2 / 64 - 5 * e2**3 / 256) * lat
        - (3 * e2 / 8 + 3 * e2**2 / 32 + 45 * e2**3 / 1024) * math.sin(2 * lat)
        + (15 * e2**2 / 256 + 45 * e2**3 / 1024) * math.sin(4 * lat)
        - (35 * e2**3 / 3072) * math.sin(6 * lat)
    )

    easting = k0 * n * (
        aa
        + (1 - t + c) * aa**3 / 6
        + (5 - 18 * t + t**2 + 72 * c - 58 * ep2) * aa**5 / 120
    ) + 500000.0

    northing = k0 * (
        m + n * tan_lat * (
            aa**2 / 2
            + (5 - t + 9 * c + 4 * c**2) * aa**4 / 24
            + (61 - 58 * t + t**2 + 600 * c - 330 * ep2) * aa**6 / 720
        )
    )

    if hemi == "S":
        northing += 10000000.0

    return easting, northing, zone, hemi


def gps_reader(port, data_queue, stop_event):
    try:
        ser = serial.Serial(
            port=port,
            baudrate=BAUDRATE,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=TIMEOUT_S,
        )
    except serial.SerialException as exc:
        print(f"Error al abrir el puerto {port}: {exc}")
        return

    print(f"GPS conectado en {port}")
    print("Leyendo tramas GGA...")

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
                data_queue.put((time.time(),) + gga)
    finally:
        ser.close()
        print("Puerto serie cerrado.")


# =========================================================
# MAPA ELECTRÓNICO INSIA
# =========================================================
@dataclass
class TrackPoint:
    north: float
    east: float
    limit_kmh: float


@dataclass
class MatchInfo:
    segment_index: int
    projection_t: float
    proj_north: float
    proj_east: float
    distance_m: float
    limit_kmh: float


def parse_track(raw_text: str) -> List[TrackPoint]:
    pts = []
    for line in raw_text.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        north, east, limit_kmh = line.split()
        pts.append(TrackPoint(float(north), float(east), float(limit_kmh)))
    return pts


def segment_limit_kmh(p1: TrackPoint, p2: TrackPoint) -> float:
    if abs(p1.limit_kmh - p2.limit_kmh) < 1e-9:
        return p1.limit_kmh
    return p2.limit_kmh


def closest_point_on_segment(px, py, ax, ay, bx, by):
    abx = bx - ax
    aby = by - ay
    apx = px - ax
    apy = py - ay
    ab2 = abx * abx + aby * aby
    if ab2 <= 1e-12:
        return 0.0, ax, ay, math.hypot(px - ax, py - ay)
    t = (apx * abx + apy * aby) / ab2
    t = max(0.0, min(1.0, t))
    qx = ax + t * abx
    qy = ay + t * aby
    d = math.hypot(px - qx, py - qy)
    return t, qx, qy, d


class InsiaElectronicMap:
    def __init__(self, points: List[TrackPoint]):
        if len(points) < 2:
            raise ValueError("El mapa electrónico necesita al menos 2 puntos.")
        self.points = points
        self.num_segments = len(points) - 1

        east_values = [p.east for p in points]
        north_values = [p.north for p in points]
        self.min_e = min(east_values)
        self.max_e = max(east_values)
        self.min_n = min(north_values)
        self.max_n = max(north_values)

        self.total_length = 0.0
        self.cumulative = [0.0]
        for i in range(self.num_segments):
            p1 = points[i]
            p2 = points[i + 1]
            length = math.hypot(p2.east - p1.east, p2.north - p1.north)
            self.total_length += length
            self.cumulative.append(self.total_length)

    def nearest_match(self, north: float, east: float) -> MatchInfo:
        best = None
        best_dist = float("inf")

        for i in range(self.num_segments):
            p1 = self.points[i]
            p2 = self.points[i + 1]
            t, qe, qn, dist = closest_point_on_segment(
                east, north, p1.east, p1.north, p2.east, p2.north
            )
            if dist < best_dist:
                best_dist = dist
                best = MatchInfo(
                    segment_index=i,
                    projection_t=t,
                    proj_north=qn,
                    proj_east=qe,
                    distance_m=dist,
                    limit_kmh=segment_limit_kmh(p1, p2),
                )
        return best

    def progress_value(self, match: MatchInfo) -> float:
        p1 = self.points[match.segment_index]
        p2 = self.points[match.segment_index + 1]
        seg_len = math.hypot(p2.east - p1.east, p2.north - p1.north)
        return self.cumulative[match.segment_index] + match.projection_t * seg_len

    def tangent_vector(self, match: MatchInfo) -> Tuple[float, float]:
        p1 = self.points[match.segment_index]
        p2 = self.points[match.segment_index + 1]
        dx = p2.east - p1.east
        dy = p2.north - p1.north
        norm = math.hypot(dx, dy)
        if norm <= 1e-12:
            return 1.0, 0.0
        return dx / norm, dy / norm

    def bounds(self):
        return self.min_e, self.max_e, self.min_n, self.max_n


# =========================================================
# CÁLCULO DE VELOCIDAD / SENTIDO
# =========================================================
class MotionEstimator:
    def __init__(self):
        self.prev_time = None
        self.prev_e = None
        self.prev_n = None
        self.speed_kmh = 0.0
        self.prev_progress = None
        self.direction_sign = 0
        self.direction_text = "Sin determinar"

    def update_speed(self, now_s: float, east: float, north: float) -> float:
        if self.prev_time is None:
            self.prev_time = now_s
            self.prev_e = east
            self.prev_n = north
            return self.speed_kmh

        dt = now_s - self.prev_time
        if dt <= 1e-6:
            return self.speed_kmh

        dist = math.hypot(east - self.prev_e, north - self.prev_n)
        inst_kmh = (dist / dt) * 3.6
        self.speed_kmh = SPEED_ALPHA * inst_kmh + (1.0 - SPEED_ALPHA) * self.speed_kmh

        self.prev_time = now_s
        self.prev_e = east
        self.prev_n = north
        return self.speed_kmh

    def update_direction(self, progress_value: float, total_length: float):
        if self.prev_progress is None:
            self.prev_progress = progress_value
            return self.direction_text

        delta = progress_value - self.prev_progress

        if delta > total_length / 2.0:
            delta -= total_length
        elif delta < -total_length / 2.0:
            delta += total_length

        if abs(delta) > 0.15:
            self.direction_sign = 1 if delta > 0 else -1

        if self.direction_sign > 0:
            self.direction_text = "Sentido mapa (progresivo)"
        elif self.direction_sign < 0:
            self.direction_text = "Sentido contrario (antihorario/horario inverso)"
        else:
            self.direction_text = "Sin determinar"

        self.prev_progress = progress_value
        return self.direction_text


# =========================================================
# AVISO AL CONDUCTOR
# =========================================================
def classify_speed(speed_kmh: float, limit_kmh: float) -> str:
    if limit_kmh <= 0:
        return "unknown"
    low = limit_kmh * 0.90
    high = limit_kmh * 1.10

    if speed_kmh < low:
        return "ok"
    if speed_kmh <= high:
        return "warning"
    return "danger"


# =========================================================
# DIBUJO DEL MAPA VECTORIAL
# =========================================================
class ElectronicMapPanel:
    def __init__(self, parent, insia_map: InsiaElectronicMap):
        self.insia_map = insia_map
        self.width, self.height = MAP_CANVAS_SIZE
        self.margin = 30
        self.trail_xy = []

        self.frame = tk.Frame(parent, padx=8, pady=8)
        self.frame.pack(side="left", fill="both", expand=True)

        self.title = tk.Label(self.frame, text="Mapa electrónico INSIA", font=("Arial", 14, "bold"))
        self.title.pack(anchor="w", pady=(0, 6))

        self.canvas = tk.Canvas(
            self.frame,
            width=self.width,
            height=self.height,
            bg="white",
            highlightthickness=1,
            highlightbackground="#cccccc",
        )
        self.canvas.pack(fill="both", expand=True)

        self.status = tk.Label(self.frame, text="Mapa cargado.", anchor="w", justify="left", fg="green")
        self.status.pack(fill="x", pady=(6, 0))

        self._draw_base()

    def utm_to_canvas(self, east: float, north: float) -> Tuple[float, float]:
        min_e, max_e, min_n, max_n = self.insia_map.bounds()
        usable_w = self.width - 2 * self.margin
        usable_h = self.height - 2 * self.margin

        span_e = max(max_e - min_e, 1.0)
        span_n = max(max_n - min_n, 1.0)
        scale = min(usable_w / span_e, usable_h / span_n)

        x = self.margin + (east - min_e) * scale
        y = self.height - self.margin - (north - min_n) * scale
        return x, y

    def color_for_limit(self, limit_kmh: float) -> str:
        if limit_kmh == 5:
            return "#00bcd4"
        if limit_kmh == 10:
            return "#ff00cc"
        if limit_kmh == 15:
            return "#b59b00"
        if limit_kmh == 18:
            return "#5f3dc4"
        if limit_kmh == 20:
            return "#d4d000"
        return "#666666"

    def _draw_base(self):
        self.canvas.delete("all")

        # Cuadrícula ligera
        for i in range(0, self.width, 50):
            self.canvas.create_line(i, 0, i, self.height, fill="#f2f2f2")
        for j in range(0, self.height, 50):
            self.canvas.create_line(0, j, self.width, j, fill="#f2f2f2")

        # Ejes visuales
        self.canvas.create_text(60, 12, text="UTM East (m)", anchor="w", font=("Arial", 10, "bold"))
        self.canvas.create_text(12, 40, text="UTM North (m)", anchor="nw", angle=90, font=("Arial", 10, "bold"))

        # Trazado por tramos
        pts = self.insia_map.points
        for i in range(len(pts) - 1):
            p1 = pts[i]
            p2 = pts[i + 1]
            x1, y1 = self.utm_to_canvas(p1.east, p1.north)
            x2, y2 = self.utm_to_canvas(p2.east, p2.north)
            color = self.color_for_limit(segment_limit_kmh(p1, p2))
            self.canvas.create_line(x1, y1, x2, y2, fill=color, width=4, capstyle=tk.ROUND)

        # Leyenda
        legend = [(10, "#ff00cc"), (20, "#d4d000"), (15, "#b59b00"), (18, "#5f3dc4"), (5, "#00bcd4")]
        lx = self.width - 120
        ly = self.height - 140
        self.canvas.create_rectangle(lx - 10, ly - 10, lx + 95, ly + 110, outline="#cccccc", fill="white")
        self.canvas.create_text(lx + 18, ly - 20, text="Leyenda", font=("Arial", 10, "bold"), anchor="w")
        for i, (limit_kmh, color) in enumerate(legend):
            yy = ly + i * 22
            self.canvas.create_rectangle(lx, yy, lx + 16, yy + 16, fill=color, outline="")
            self.canvas.create_text(lx + 24, yy + 8, text=f"{limit_kmh} km/h", anchor="w", font=("Arial", 10))

    def draw_vehicle(self, east: float, north: float, matched: bool, status_text: str):
        self.canvas.delete("vehicle")
        self.canvas.delete("vehicle_trail")

        if not matched:
            self.status.config(text=status_text, fg="red")
            return

        x, y = self.utm_to_canvas(east, north)
        self.trail_xy.append((x, y))
        if len(self.trail_xy) > MAX_TRAIL_POINTS:
            self.trail_xy.pop(0)

        if len(self.trail_xy) >= 2:
            flat = []
            for px, py in self.trail_xy:
                flat.extend([px, py])
            self.canvas.create_line(*flat, fill="#e53935", width=2, tags="vehicle_trail")

        r = 7
        self.canvas.create_oval(x - r, y - r, x + r, y + r, fill="#1976d2", outline="white", width=2, tags="vehicle")
        self.canvas.create_text(x, y - 16, text="GPS", fill="#1976d2", font=("Arial", 10, "bold"), tags="vehicle")
        self.status.config(text=status_text, fg="green")


# =========================================================
# INTERFAZ DE ALERTA
# =========================================================
class DriverWarningPanel:
    def __init__(self, parent):
        self.frame = tk.Frame(parent, padx=10, pady=10, width=390)
        self.frame.pack(side="right", fill="y")
        self.frame.pack_propagate(False)

        self.title = tk.Label(self.frame, text="Sistema de aviso al conductor", font=("Arial", 16, "bold"))
        self.title.pack(pady=(0, 10))

        self.info_speed = tk.Label(self.frame, text="Velocidad actual: -- km/h", font=("Arial", 14, "bold"))
        self.info_speed.pack(fill="x", pady=(0, 8))

        self.info_limit = tk.Label(self.frame, text="Límite actual: -- km/h", font=("Arial", 13))
        self.info_limit.pack(fill="x")

        self.info_state = tk.Label(self.frame, text="Estado: esperando datos...", font=("Arial", 12), fg="blue", wraplength=360, justify="left")
        self.info_state.pack(fill="x", pady=(8, 12))

        self.info_dir = tk.Label(self.frame, text="Sentido: --", font=("Arial", 11), wraplength=360, justify="left")
        self.info_dir.pack(fill="x")

        self.info_dist = tk.Label(self.frame, text="Distancia a la pista: -- m", font=("Arial", 11))
        self.info_dist.pack(fill="x", pady=(4, 10))

        self.info_gps = tk.Label(self.frame, text="Fix / satélites / altitud: --", font=("Arial", 11), wraplength=360, justify="left")
        self.info_gps.pack(fill="x")

        self.info_geo = tk.Label(self.frame, text="Lat/Lon: --\nUTM: --", font=("Arial", 11), wraplength=360, justify="left")
        self.info_geo.pack(fill="x", pady=(8, 12))

        self.warning_canvas = tk.Canvas(
            self.frame,
            width=330,
            height=145,
            bg="white",
            highlightthickness=1,
            highlightbackground="#cccccc"
        )
        self.warning_canvas.pack(pady=(6, 10))

        self.note = tk.Label(
            self.frame,
            text=(
                "Criterio de aviso:\n"
                "• Verde: velocidad < límite - 10%\n"
                "• Amarillo: entre límite - 10% y límite + 10%\n"
                "• Rojo: velocidad > límite + 10%"
            ),
            justify="left",
            wraplength=360,
            fg="#444444"
        )
        self.note.pack(fill="x")

        self.draw_warning_gauge("unknown", 0.0)

    def draw_warning_gauge(self, level: str, speed_kmh: float):
        self.warning_canvas.delete("all")

        x0 = 20
        y0 = 25
        w = 90
        h = 42
        gap = 12

        colors_off = ["#dfe8df", "#efe8cf", "#f2d6d6"]
        colors_on = {
            "ok": ["#43a047", "#efe8cf", "#f2d6d6"],
            "warning": ["#43a047", "#fdd835", "#f2d6d6"],
            "danger": ["#43a047", "#fdd835", "#e53935"],
            "unknown": colors_off,
        }
        colors = colors_on.get(level, colors_off)

        labels = ["< límite -10%", "±10%", "> límite +10%"]

        for i in range(3):
            x = x0 + i * (w + gap)
            self.warning_canvas.create_rectangle(x, y0, x + w, y0 + h, fill=colors[i], outline="#999999")
            self.warning_canvas.create_text(x + w / 2, y0 + h + 16, text=labels[i], font=("Arial", 9))

        self.warning_canvas.create_text(165, 104, text=f"{speed_kmh:.1f} km/h", font=("Arial", 22, "bold"))
        self.warning_canvas.create_text(165, 126, text="Velocidad actual", font=("Arial", 10))

    def update_panel(
        self,
        speed_kmh: float,
        limit_kmh: Optional[float],
        level: str,
        direction_text: str,
        distance_to_track: Optional[float],
        lat: float,
        lon: float,
        easting: float,
        northing: float,
        zone: int,
        hemi: str,
        fix_q: int,
        sats: int,
        alt: float,
        matched: bool,
    ):
        self.info_speed.config(text=f"Velocidad actual: {speed_kmh:.2f} km/h")
        self.info_limit.config(text=f"Límite actual: {limit_kmh:.1f} km/h" if limit_kmh is not None else "Límite actual: --")

        if matched and limit_kmh is not None:
            if level == "ok":
                state = "Velocidad correcta."
                color = "#2e7d32"
            elif level == "warning":
                state = "Atención: velocidad cerca del límite."
                color = "#b28704"
            else:
                state = "ALERTA: velocidad excesiva."
                color = "#c62828"
        else:
            state = "Fuera de la pista o sin coincidencia fiable con el mapa."
            color = "#c62828"

        self.info_state.config(text=f"Estado: {state}", fg=color)
        self.info_dir.config(text=f"Sentido: {direction_text}")
        if distance_to_track is None:
            self.info_dist.config(text="Distancia a la pista: -- m")
        else:
            self.info_dist.config(text=f"Distancia a la pista: {distance_to_track:.2f} m")

        self.info_gps.config(text=f"Fix: {fix_q} | Satélites: {sats} | Altitud: {alt:.2f} m")
        self.info_geo.config(
            text=(
                f"Lat/Lon: {lat:.8f}, {lon:.8f}\n"
                f"UTM: E={easting:.3f}  N={northing:.3f}  Zona={zone}{hemi}"
            )
        )
        self.draw_warning_gauge(level, speed_kmh)


# =========================================================
# APLICACIÓN PRINCIPAL
# =========================================================
class Practice3App:
    def __init__(self, root, data_queue, stop_event):
        self.root = root
        self.data_queue = data_queue
        self.stop_event = stop_event
        self.root.title(WINDOW_TITLE)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.track_points = parse_track(INSIA_TRACK_RAW)
        self.insia_map = InsiaElectronicMap(self.track_points)
        self.motion = MotionEstimator()

        self.main_frame = tk.Frame(root)
        self.main_frame.pack(fill="both", expand=True)

        self.map_panel = ElectronicMapPanel(self.main_frame, self.insia_map)
        self.warning_panel = DriverWarningPanel(self.main_frame)

        self.update_loop()

    def process_sample(self, sample):
        timestamp_s, lat, lon, fix_q, sats, alt = sample

        if fix_q <= 0:
            self.warning_panel.info_state.config(
                text="Estado: trama recibida, pero sin posicionamiento válido.",
                fg="#b28704",
            )
            return

        easting, northing, zone, hemi = latlon_to_utm_wgs84(lat, lon, force_zone=30)

        speed_kmh = self.motion.update_speed(timestamp_s, easting, northing)

        match = self.insia_map.nearest_match(northing, easting)
        progress = self.insia_map.progress_value(match)
        direction_text = self.motion.update_direction(progress, self.insia_map.total_length)

        matched = match.distance_m <= MAX_DISTANCE_TO_TRACK_M
        limit_kmh = match.limit_kmh if matched else None
        level = classify_speed(speed_kmh, limit_kmh) if matched else "unknown"

        status_text = (
            f"Vehículo representado sobre el mapa. Distancia a pista: {match.distance_m:.2f} m"
            if matched else
            f"Posición fuera de la pista o demasiado alejada ({match.distance_m:.2f} m)."
        )
        self.map_panel.draw_vehicle(easting, northing, matched, status_text)

        self.warning_panel.update_panel(
            speed_kmh=speed_kmh,
            limit_kmh=limit_kmh,
            level=level,
            direction_text=direction_text,
            distance_to_track=match.distance_m,
            lat=lat,
            lon=lon,
            easting=easting,
            northing=northing,
            zone=zone,
            hemi=hemi,
            fix_q=fix_q,
            sats=sats,
            alt=alt,
            matched=matched,
        )

    def update_loop(self):
        try:
            while True:
                sample = self.data_queue.get_nowait()
                self.process_sample(sample)
        except queue.Empty:
            pass

        self.root.after(100, self.update_loop)

    def on_close(self):
        self.stop_event.set()
        self.root.destroy()


# =========================================================
# MODO DE PRUEBA SIN GPS REAL
# =========================================================
def fake_gps_sender(data_queue, stop_event, track_points: List[TrackPoint]):
    # Recorre la pista en ambos sentidos para comprobar el requisito horario/antihorario.
    idx = 0
    direction = 1

    while not stop_event.is_set():
        p = track_points[idx]
        # Aproximación local alrededor de UTM Madrid, suficiente para pruebas visuales
        lat, lon = utm_to_latlon_approx(p.east, p.north, zone=30, northern_hemisphere=True)
        data_queue.put((time.time(), lat, lon, 1, 10, 650.0))

        idx += direction
        if idx >= len(track_points) - 1:
            direction = -1
        elif idx <= 0:
            direction = 1

        time.sleep(1.0)


def utm_to_latlon_approx(easting: float, northing: float, zone: int = 30, northern_hemisphere: bool = True):
    # Conversión aproximada suficiente para generar datos de prueba coherentes
    # alrededor del INSIA. No se usa en el modo real con GPS.
    x = easting - 500000.0
    y = northing
    if not northern_hemisphere:
        y -= 10000000.0

    a = A_WGS84
    e2 = E2_WGS84
    e1 = (1 - math.sqrt(1 - e2)) / (1 + math.sqrt(1 - e2))
    k0 = K0

    lon0 = math.radians((zone - 1) * 6 - 180 + 3)

    m = y / k0
    mu = m / (a * (1 - e2 / 4 - 3 * e2 * e2 / 64 - 5 * e2**3 / 256))

    j1 = 3 * e1 / 2 - 27 * e1**3 / 32
    j2 = 21 * e1**2 / 16 - 55 * e1**4 / 32
    j3 = 151 * e1**3 / 96
    j4 = 1097 * e1**4 / 512

    fp = mu + j1 * math.sin(2 * mu) + j2 * math.sin(4 * mu) + j3 * math.sin(6 * mu) + j4 * math.sin(8 * mu)

    ep2 = e2 / (1 - e2)
    c1 = ep2 * math.cos(fp) ** 2
    t1 = math.tan(fp) ** 2
    n1 = a / math.sqrt(1 - e2 * math.sin(fp) ** 2)
    r1 = a * (1 - e2) / ((1 - e2 * math.sin(fp) ** 2) ** 1.5)
    d = x / (n1 * k0)

    lat = fp - (n1 * math.tan(fp) / r1) * (
        d * d / 2
        - (5 + 3 * t1 + 10 * c1 - 4 * c1 * c1 - 9 * ep2) * d**4 / 24
        + (61 + 90 * t1 + 298 * c1 + 45 * t1 * t1 - 252 * ep2 - 3 * c1 * c1) * d**6 / 720
    )

    lon = lon0 + (
        d
        - (1 + 2 * t1 + c1) * d**3 / 6
        + (5 - 2 * c1 + 28 * t1 - 3 * c1 * c1 + 8 * ep2 + 24 * t1 * t1) * d**5 / 120
    ) / math.cos(fp)

    return math.degrees(lat), math.degrees(lon)


# =========================================================
# MAIN
# =========================================================
def main():
    data_queue = queue.Queue()
    stop_event = threading.Event()

    track_points = parse_track(INSIA_TRACK_RAW)

    if USE_FAKE_GPS:
        gps_thread = threading.Thread(
            target=fake_gps_sender,
            args=(data_queue, stop_event, track_points),
            daemon=True,
        )
    else:
        gps_thread = threading.Thread(
            target=gps_reader,
            args=(PORT, data_queue, stop_event),
            daemon=True,
        )

    gps_thread.start()

    root = tk.Tk()
    app = Practice3App(root, data_queue, stop_event)

    try:
        root.mainloop()
    finally:
        stop_event.set()
        gps_thread.join(timeout=2)


if __name__ == "__main__":
    main()
