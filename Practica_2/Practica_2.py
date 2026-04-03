import math
import time
import queue
import threading
import serial
import tkinter as tk
from PIL import Image, ImageTk


PORT = "COM3"
BAUDRATE = 4800
TIMEOUT_S = 1

A_WGS84 = 6378137.0
E2_WGS84 = 0.00669437999013
K0 = 0.9996


# =========================================================
# CONFIGURACIÓN DEL MAPA
# =========================================================
# Ruta de la imagen capturada de Google Earth
MAP_IMAGE_PATH = "campus_sur.png"

# Tamaño de la ventana/canvas
WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 700

# Número máximo de puntos de la trayectoria que se guardan en pantalla
MAX_TRAIL_POINTS = 500

# ---------------------------------------------------------
# GEOREFERENCIACIÓN
# ---------------------------------------------------------
# Debes cambiar estos 3 puntos por los reales de TU imagen.
#
# Cada punto es:
#   "pixel": (x_imagen, y_imagen)
#   "utm":   (Easting, Northing)
#
# Los 3 puntos NO deben estar alineados.
# Con esos 3 puntos se calcula una transformación afín:
#   x_pixel = a*E + b*N + c
#   y_pixel = d*E + e*N + f
#
# Ejemplo de estructura:
CONTROL_POINTS = [
    {"pixel": (900, 700), "utm": (446344.30, 4470862.04)},
    {"pixel": (950, 300), "utm": (446602.80, 4471303.60)},
    {"pixel": (1250, 280), "utm": (446945.44, 4471246.59)},
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

    val = deg + minutes / 60.0

    if hemi in ("S", "W"):
        val *= -1.0

    return val


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

    N = a / math.sqrt(1.0 - e2 * sin_lat * sin_lat)
    T = tan_lat * tan_lat
    C = ep2 * cos_lat * cos_lat
    A = cos_lat * (lon - lon0)

    M = a * (
        (1 - e2 / 4 - 3 * e2**2 / 64 - 5 * e2**3 / 256) * lat
        - (3 * e2 / 8 + 3 * e2**2 / 32 + 45 * e2**3 / 1024) * math.sin(2 * lat)
        + (15 * e2**2 / 256 + 45 * e2**3 / 1024) * math.sin(4 * lat)
        - (35 * e2**3 / 3072) * math.sin(6 * lat)
    )

    easting = k0 * N * (
        A
        + (1 - T + C) * A**3 / 6
        + (5 - 18 * T + T**2 + 72 * C - 58 * ep2) * A**5 / 120
    ) + 500000.0

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


# =========================================================
# TRANSFORMACIÓN UTM -> PIXEL
# =========================================================
def solve_3x3(A, b):
    """
    Resuelve un sistema 3x3 por eliminación de Gauss.
    """
    M = [A[0][:] + [b[0]], A[1][:] + [b[1]], A[2][:] + [b[2]]]

    for i in range(3):
        pivot = M[i][i]
        if abs(pivot) < 1e-12:
            for j in range(i + 1, 3):
                if abs(M[j][i]) > 1e-12:
                    M[i], M[j] = M[j], M[i]
                    pivot = M[i][i]
                    break
        if abs(pivot) < 1e-12:
            raise ValueError("No se puede resolver la georreferenciación: puntos mal elegidos.")

        for k in range(i, 4):
            M[i][k] /= pivot

        for j in range(3):
            if j == i:
                continue
            factor = M[j][i]
            for k in range(i, 4):
                M[j][k] -= factor * M[i][k]

    return [M[0][3], M[1][3], M[2][3]]


class AffineGeoReference:
    """
    Calcula:
        x = a*E + b*N + c
        y = d*E + e*N + f
    a partir de 3 puntos de control.
    """
    def __init__(self, control_points):
        if len(control_points) != 3:
            raise ValueError("Se necesitan exactamente 3 puntos de control.")

        A = []
        bx = []
        by = []

        for p in control_points:
            E, N = p["utm"]
            x, y = p["pixel"]
            A.append([E, N, 1.0])
            bx.append(x)
            by.append(y)

        self.a, self.b, self.c = solve_3x3(A, bx)
        self.d, self.e, self.f = solve_3x3(A, by)

    def utm_to_pixel(self, E, N):
        x = self.a * E + self.b * N + self.c
        y = self.d * E + self.e * N + self.f
        return x, y


# =========================================================
# INTERFAZ GRÁFICA
# =========================================================
class GPSMapApp:
    def __init__(self, root, data_queue, stop_event):
        self.root = root
        self.data_queue = data_queue
        self.stop_event = stop_event

        self.root.title("Práctica 2 - Navegación GPS sobre mapa georreferenciado")

        self.geo = AffineGeoReference(CONTROL_POINTS)

        self.main_frame = tk.Frame(root)
        self.main_frame.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(
            self.main_frame,
            width=WINDOW_WIDTH,
            height=WINDOW_HEIGHT,
            bg="white"
        )
        self.canvas.pack(side="left", fill="both", expand=True)

        self.info_frame = tk.Frame(self.main_frame, padx=10, pady=10)
        self.info_frame.pack(side="right", fill="y")

        self.info_title = tk.Label(
            self.info_frame,
            text="Datos GPS",
            font=("Arial", 16, "bold")
        )
        self.info_title.pack(pady=(0, 10))

        self.lbl_fix = tk.Label(self.info_frame, text="Fix: --", anchor="w", justify="left")
        self.lbl_fix.pack(fill="x")

        self.lbl_sats = tk.Label(self.info_frame, text="Satélites: --", anchor="w", justify="left")
        self.lbl_sats.pack(fill="x")

        self.lbl_alt = tk.Label(self.info_frame, text="Altitud: --", anchor="w", justify="left")
        self.lbl_alt.pack(fill="x")

        self.lbl_latlon = tk.Label(self.info_frame, text="Lat/Lon: --", anchor="w", justify="left")
        self.lbl_latlon.pack(fill="x", pady=(10, 0))

        self.lbl_utm = tk.Label(self.info_frame, text="UTM: --", anchor="w", justify="left")
        self.lbl_utm.pack(fill="x")

        self.lbl_pixel = tk.Label(self.info_frame, text="Pixel: --", anchor="w", justify="left")
        self.lbl_pixel.pack(fill="x", pady=(10, 0))

        self.lbl_status = tk.Label(
            self.info_frame,
            text="Estado: esperando datos...",
            fg="blue",
            anchor="w",
            justify="left"
        )
        self.lbl_status.pack(fill="x", pady=(20, 0))

        self.load_map_image()

        self.trail_pixels = []
        self.current_marker = None

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.update_loop()

    def load_map_image(self):
        try:
            self.map_image_pil = Image.open(MAP_IMAGE_PATH)
        except Exception as e:
            raise FileNotFoundError(
                f"No se pudo abrir la imagen '{MAP_IMAGE_PATH}'. Error: {e}"
            )

        self.img_width, self.img_height = self.map_image_pil.size
        self.map_image_tk = ImageTk.PhotoImage(self.map_image_pil)

        self.canvas.config(width=self.img_width, height=self.img_height)
        self.canvas.create_image(0, 0, anchor="nw", image=self.map_image_tk)

    def draw_trail(self):
        self.canvas.delete("trail")

        if len(self.trail_pixels) < 2:
            return

        flat_points = []
        for x, y in self.trail_pixels:
            flat_points.extend([x, y])

        self.canvas.create_line(
            *flat_points,
            fill="red",
            width=2,
            tags="trail"
        )

    def draw_current_position(self, x, y):
        self.canvas.delete("gps_point")

        r = 6
        self.canvas.create_oval(
            x - r, y - r, x + r, y + r,
            fill="blue",
            outline="white",
            width=2,
            tags="gps_point"
        )

        self.canvas.create_text(
            x,
            y - 15,
            text="GPS",
            fill="blue",
            font=("Arial", 10, "bold"),
            tags="gps_point"
        )

    def update_info(self, lat, lon, fix_q, sats, alt, E, N, zone, hemi, x, y):
        self.lbl_fix.config(text=f"Fix: {fix_q}")
        self.lbl_sats.config(text=f"Satélites: {sats}")
        self.lbl_alt.config(text=f"Altitud: {alt:.2f} m")
        self.lbl_latlon.config(text=f"Lat/Lon: {lat:.8f}, {lon:.8f}")
        self.lbl_utm.config(text=f"UTM: E={E:.3f}  N={N:.3f}  Zona={zone}{hemi}")
        self.lbl_pixel.config(text=f"Pixel: x={x:.1f}, y={y:.1f}")

    def update_loop(self):
        try:
            while True:
                lat, lon, fix_q, sats, alt = self.data_queue.get_nowait()

                E, N, zone, hemi = latlon_to_utm_wgs84(lat, lon, force_zone=None)
                x, y = self.geo.utm_to_pixel(E, N)

                self.update_info(lat, lon, fix_q, sats, alt, E, N, zone, hemi, x, y)

                if 0 <= x < self.img_width and 0 <= y < self.img_height:
                    self.lbl_status.config(
                        text="Estado: posición representada en el mapa",
                        fg="green"
                    )

                    self.trail_pixels.append((x, y))
                    if len(self.trail_pixels) > MAX_TRAIL_POINTS:
                        self.trail_pixels.pop(0)

                    self.draw_trail()
                    self.draw_current_position(x, y)
                else:
                    self.lbl_status.config(
                        text="Estado: posición fuera de la imagen georreferenciada",
                        fg="red"
                    )
        except queue.Empty:
            pass

        self.root.after(100, self.update_loop)

    def on_close(self):
        self.stop_event.set()
        self.root.destroy()


def main():
    data_queue = queue.Queue()
    stop_event = threading.Event()

    gps_thread = threading.Thread(
        target=gps_reader,
        args=(PORT, data_queue, stop_event),
        daemon=True
    )
    gps_thread.start()

    root = tk.Tk()
    app = GPSMapApp(root, data_queue, stop_event)

    try:
        root.mainloop()
    finally:
        stop_event.set()
        gps_thread.join(timeout=2)


if __name__ == "__main__":
    main()