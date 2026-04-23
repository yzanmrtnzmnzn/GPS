import math
import time
import queue
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Tuple

import serial
import tkinter as tk
from PIL import Image, ImageTk


# =========================================================
# CONFIGURACIÓN GENERAL
# =========================================================
PORT = "COM3"
BAUDRATE = 4800
TIMEOUT_S = 1

A_WGS84 = 6378137.0
E2_WGS84 = 0.00669437999013
K0 = 0.9996

WINDOW_TITLE = "Práctica 2 - Mapa electrónico de la carretera"
MAX_TRAIL_POINTS = 500

BASE_DIR = Path(__file__).resolve().parent
CAMPUS_MAP_IMAGE_PATH = BASE_DIR / "campus_sur_capture.png"
INSIA_IMAGE_PATH = BASE_DIR / "imagen_practica2.jpeg"


# =========================================================
# PUNTOS DE CONTROL
# =========================================================
# CAMPUS SUR
CAMPUS_CONTROL_POINTS = [
    {"name": "P1", "pixel": (500, 692), "utm": (446344.30, 4470862.04)},
    {"name": "P2", "pixel": (552, 236), "utm": (446602.80, 4471303.60)},
    {"name": "P3", "pixel": (852, 162), "utm": (446945.44, 4471246.59)},
]

# INSIA
INSIA_CONTROL_POINTS = [
    {"name": "P1", "pixel": (798, 818), "utm": (446344.30, 4470862.04)},
    {"name": "P2", "pixel": (1120, 240), "utm": (446602.80, 4471303.60)},
    {"name": "P3", "pixel": (1340, 450), "utm": (446945.44, 4471246.59)},
]


# =========================================================
# FUNCIONES DE PRÁCTICA 1
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


# =========================================================
# TRANSFORMACIÓN AFÍN UTM -> PIXEL
# =========================================================
def solve_3x3(a_matrix, b_vector):
    matrix = [
        a_matrix[0][:] + [b_vector[0]],
        a_matrix[1][:] + [b_vector[1]],
        a_matrix[2][:] + [b_vector[2]],
    ]

    for i in range(3):
        pivot = matrix[i][i]
        if abs(pivot) < 1e-12:
            for j in range(i + 1, 3):
                if abs(matrix[j][i]) > 1e-12:
                    matrix[i], matrix[j] = matrix[j], matrix[i]
                    pivot = matrix[i][i]
                    break

        if abs(pivot) < 1e-12:
            raise ValueError("No se puede resolver la georreferenciación: puntos mal elegidos.")

        for k in range(i, 4):
            matrix[i][k] /= pivot

        for j in range(3):
            if j == i:
                continue
            factor = matrix[j][i]
            for k in range(i, 4):
                matrix[j][k] -= factor * matrix[i][k]

    return [matrix[0][3], matrix[1][3], matrix[2][3]]


class AffineGeoReference:
    def __init__(self, control_points):
        if len(control_points) != 3:
            raise ValueError("Se necesitan exactamente 3 puntos de control.")

        a_matrix = []
        bx = []
        by = []

        for point in control_points:
            easting, northing = point["utm"]
            x_pixel, y_pixel = point["pixel"]
            a_matrix.append([easting, northing, 1.0])
            bx.append(x_pixel)
            by.append(y_pixel)

        self.a, self.b, self.c = solve_3x3(a_matrix, bx)
        self.d, self.e, self.f = solve_3x3(a_matrix, by)

    def utm_to_pixel(self, easting, northing):
        x_pixel = self.a * easting + self.b * northing + self.c
        y_pixel = self.d * easting + self.e * northing + self.f
        return x_pixel, y_pixel


# =========================================================
# ESTRUCTURAS DE MAPA
# =========================================================
@dataclass
class MapConfig:
    name: str
    image_path: Path
    control_points: Optional[List[dict]]
    max_display_size: Tuple[int, int]
    marker_color: str


class MapPanel:
    def __init__(self, parent, config: MapConfig, title_text: str):
        self.config = config
        self.title_text = title_text
        self.trail_pixels = []

        self.frame = tk.Frame(parent, padx=6, pady=6)
        self.frame.pack(side="left", fill="both", expand=True)

        self.title = tk.Label(self.frame, text=title_text, font=("Arial", 12, "bold"))
        self.title.pack(anchor="w", pady=(0, 6))

        self.canvas = tk.Canvas(self.frame, bg="white", highlightthickness=1, highlightbackground="#cccccc")
        self.canvas.pack(fill="both", expand=True)

        self.status = tk.Label(self.frame, text="", anchor="w", justify="left", wraplength=520)
        self.status.pack(fill="x", pady=(6, 0))

        self.original_image = Image.open(self.config.image_path)
        self.original_width, self.original_height = self.original_image.size
        self.display_image, self.scale = self._build_display_image(
            self.original_image,
            self.config.max_display_size
        )
        self.display_width, self.display_height = self.display_image.size
        self.tk_image = ImageTk.PhotoImage(self.display_image)

        self.canvas.config(width=self.display_width, height=self.display_height)
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_image, tags="base")

        self.geo = AffineGeoReference(self.config.control_points) if self.config.control_points else None
        self.draw_control_points()

        if self.geo is None:
            self.status.config(
                text="Imagen cargada, pero sin georreferenciación.",
                fg="#9a5f00",
            )
        else:
            self.status.config(text=f"Mapa georreferenciado listo: {self.config.name}.", fg="green")

    def _build_display_image(self, pil_image, max_size):
        max_w, max_h = max_size
        w, h = pil_image.size
        scale = min(max_w / w, max_h / h, 1.0)
        new_size = (max(1, int(w * scale)), max(1, int(h * scale)))
        if scale < 1.0:
            pil_image = pil_image.resize(new_size, Image.Resampling.LANCZOS)
        return pil_image, scale

    def draw_control_points(self):
        self.canvas.delete("control")
        if not self.config.control_points:
            return

        for point in self.config.control_points:
            x = point["pixel"][0] * self.scale
            y = point["pixel"][1] * self.scale
            r = 4
            self.canvas.create_oval(
                x - r, y - r, x + r, y + r,
                fill=self.config.marker_color,
                outline="white",
                width=2,
                tags="control",
            )
            self.canvas.create_text(
                x + 18, y - 12,
                text=point["name"],
                fill=self.config.marker_color,
                font=("Arial", 10, "bold"),
                tags="control",
            )

    def draw_position(self, easting, northing):
        if self.geo is None:
            return None

        x_raw, y_raw = self.geo.utm_to_pixel(easting, northing)
        inside = 0 <= x_raw < self.original_width and 0 <= y_raw < self.original_height

        self.canvas.delete("gps")
        self.canvas.delete("trail")

        if inside:
            self.trail_pixels.append((x_raw, y_raw))
            if len(self.trail_pixels) > MAX_TRAIL_POINTS:
                self.trail_pixels.pop(0)

            if len(self.trail_pixels) >= 2:
                flat_points = []
                for px, py in self.trail_pixels:
                    flat_points.extend([px * self.scale, py * self.scale])
                self.canvas.create_line(*flat_points, fill="red", width=2, tags="trail")

            x = x_raw * self.scale
            y = y_raw * self.scale
            r = 6
            self.canvas.create_oval(
                x - r, y - r, x + r, y + r,
                fill="blue",
                outline="white",
                width=2,
                tags="gps",
            )
            self.canvas.create_text(
                x,
                y - 14,
                text="GPS",
                fill="blue",
                font=("Arial", 10, "bold"),
                tags="gps",
            )
            self.status.config(text=f"Posición representada correctamente en {self.config.name}.", fg="green")
        else:
            self.status.config(text=f"La posición GPS cae fuera de la imagen {self.config.name}.", fg="red")

        return x_raw, y_raw, inside


# =========================================================
# INTERFAZ GRÁFICA
# =========================================================
class GPSMapApp:
    def __init__(self, root, data_queue, stop_event):
        self.root = root
        self.data_queue = data_queue
        self.stop_event = stop_event

        self.root.title(WINDOW_TITLE)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.main_frame = tk.Frame(root)
        self.main_frame.pack(fill="both", expand=True)

        self.maps_frame = tk.Frame(self.main_frame)
        self.maps_frame.pack(side="left", fill="both", expand=True)

        self.campus_panel = MapPanel(
            self.maps_frame,
            MapConfig(
                name="Campus Sur",
                image_path=CAMPUS_MAP_IMAGE_PATH,
                control_points=CAMPUS_CONTROL_POINTS,
                max_display_size=(820, 720),
                marker_color="#0d4f8b",
            ),
            title_text="Campus Sur (mapa georreferenciado)",
        )

        self.insia_panel = MapPanel(
            self.maps_frame,
            MapConfig(
                name="INSIA",
                image_path=INSIA_IMAGE_PATH,
                control_points=INSIA_CONTROL_POINTS,
                max_display_size=(520, 380),
                marker_color="#0d4f8b",
            ),
            title_text="INSIA (mapa georreferenciado)",
        )

        self.info_frame = tk.Frame(self.main_frame, padx=12, pady=12, width=330)
        self.info_frame.pack(side="right", fill="y")
        self.info_frame.pack_propagate(False)

        self.info_title = tk.Label(self.info_frame, text="Datos GPS", font=("Arial", 16, "bold"))
        self.info_title.pack(pady=(0, 12))

        self.lbl_fix = tk.Label(self.info_frame, text="Fix: --", anchor="w", justify="left")
        self.lbl_fix.pack(fill="x")

        self.lbl_sats = tk.Label(self.info_frame, text="Satélites: --", anchor="w", justify="left")
        self.lbl_sats.pack(fill="x")

        self.lbl_alt = tk.Label(self.info_frame, text="Altitud: --", anchor="w", justify="left")
        self.lbl_alt.pack(fill="x")

        self.lbl_latlon = tk.Label(self.info_frame, text="Lat/Lon: --", anchor="w", justify="left", wraplength=300)
        self.lbl_latlon.pack(fill="x", pady=(10, 0))

        self.lbl_utm = tk.Label(self.info_frame, text="UTM: --", anchor="w", justify="left", wraplength=300)
        self.lbl_utm.pack(fill="x")

        self.lbl_pixel_campus = tk.Label(self.info_frame, text="Pixel Campus: --", anchor="w", justify="left")
        self.lbl_pixel_campus.pack(fill="x", pady=(10, 0))

        self.lbl_pixel_insia = tk.Label(self.info_frame, text="Pixel INSIA: --", anchor="w", justify="left", wraplength=300)
        self.lbl_pixel_insia.pack(fill="x")

        self.lbl_status = tk.Label(
            self.info_frame,
            text="Estado: esperando datos...",
            fg="blue",
            anchor="w",
            justify="left",
            wraplength=300,
        )
        self.lbl_status.pack(fill="x", pady=(18, 0))

        self.lbl_notes = tk.Label(
            self.info_frame,
            text=(
                "Configuración actual:\n"
                "• Campus Sur está georreferenciado.\n"
                "• INSIA está georreferenciado con sus propios puntos.\n"
            ),
            anchor="w",
            justify="left",
            wraplength=300,
            fg="#444444",
        )
        self.lbl_notes.pack(fill="x", pady=(18, 0))

        self.update_loop()

    def update_info(self, lat, lon, fix_q, sats, alt, easting, northing, zone, hemi, campus_result, insia_result):
        self.lbl_fix.config(text=f"Fix: {fix_q}")
        self.lbl_sats.config(text=f"Satélites: {sats}")
        self.lbl_alt.config(text=f"Altitud: {alt:.2f} m")
        self.lbl_latlon.config(text=f"Lat/Lon: {lat:.8f}, {lon:.8f}")
        self.lbl_utm.config(text=f"UTM: E={easting:.3f}  N={northing:.3f}  Zona={zone}{hemi}")

        if campus_result is None:
            self.lbl_pixel_campus.config(text="Pixel Campus: --")
        else:
            x, y, inside = campus_result
            suffix = "(dentro)" if inside else "(fuera)"
            self.lbl_pixel_campus.config(text=f"Pixel Campus: x={x:.1f}, y={y:.1f} {suffix}")

        if insia_result is None:
            self.lbl_pixel_insia.config(text="Pixel INSIA: --")
        else:
            x, y, inside = insia_result
            suffix = "(dentro)" if inside else "(fuera)"
            self.lbl_pixel_insia.config(text=f"Pixel INSIA: x={x:.1f}, y={y:.1f} {suffix}")

    def update_loop(self):
        try:
            while True:
                lat, lon, fix_q, sats, alt = self.data_queue.get_nowait()

                if fix_q <= 0:
                    self.lbl_status.config(
                        text="Estado: trama recibida, pero sin posicionamiento válido.",
                        fg="#c27d00",
                    )
                    continue

                easting, northing, zone, hemi = latlon_to_utm_wgs84(lat, lon, force_zone=30)

                campus_result = self.campus_panel.draw_position(easting, northing)
                insia_result = self.insia_panel.draw_position(easting, northing)

                self.update_info(
                    lat, lon, fix_q, sats, alt, easting, northing, zone, hemi,
                    campus_result, insia_result,
                )

                self.lbl_status.config(
                    text="Estado: posición actualizada en todos los mapas georreferenciados.",
                    fg="green",
                )
        except queue.Empty:
            pass

        self.root.after(100, self.update_loop)

    def on_close(self):
        self.stop_event.set()
        self.root.destroy()


# =========================================================
# PRUEBAS
# =========================================================
def test_control_points():
    campus_geo = AffineGeoReference(CAMPUS_CONTROL_POINTS)
    insia_geo = AffineGeoReference(INSIA_CONTROL_POINTS)

    print("=== TEST CAMPUS ===")
    for p in CAMPUS_CONTROL_POINTS:
        x, y = campus_geo.utm_to_pixel(*p["utm"])
        print(p["name"], "esperado:", p["pixel"], "calculado:", (round(x, 2), round(y, 2)))

    print("\n=== TEST INSIA ===")
    for p in INSIA_CONTROL_POINTS:
        x, y = insia_geo.utm_to_pixel(*p["utm"])
        print(p["name"], "esperado:", p["pixel"], "calculado:", (round(x, 2), round(y, 2)))


def fake_gps_sender(data_queue, stop_event):
    test_points = [
        (40.386625, -3.632161),  # cerca de P1
        (40.390619, -3.629153),  # cerca de P2
        (40.390128, -3.625111),  # cerca de P3
    ]

    i = 0
    while not stop_event.is_set():
        lat, lon = test_points[i % len(test_points)]
        data_queue.put((lat, lon, 1, 8, 650.0))
        i += 1
        time.sleep(1)


# =========================================================
# PROGRAMA PRINCIPAL
# =========================================================
def main():
    USE_FAKE_GPS = False
    data_queue = queue.Queue()
    stop_event = threading.Event()

    if USE_FAKE_GPS:
        gps_thread = threading.Thread(
            target=fake_gps_sender,
            args=(data_queue, stop_event),
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
    GPSMapApp(root, data_queue, stop_event)

    try:
        root.mainloop()
    finally:
        stop_event.set()
        gps_thread.join(timeout=2)


if __name__ == "__main__":
    # test_control_points()
    main()