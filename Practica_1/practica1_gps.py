import serial
import utm

# CONFIGURACIÓN DEL PUERTO
PORT = "COM3"        # Cambia por tu puerto (COM3, COM4, etc.)
BAUDRATE = 4800

ser = serial.Serial(
    port=PORT,
    baudrate=BAUDRATE,
    bytesize=serial.EIGHTBITS,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    timeout=1
)

print("Leyendo datos GPS...\n")


def convertir_lat_lon(valor, direccion):
    """
    Convierte coordenadas NMEA (ddmm.mmmm) a grados decimales
    """
    grados = int(valor[:2])
    minutos = float(valor[2:])

    decimal = grados + minutos / 60

    if direccion in ["S", "W"]:
        decimal *= -1

    return decimal


while True:

    linea = ser.readline().decode(errors="ignore").strip()

    if linea.startswith("$GPGGA"):

        datos = linea.split(",")

        if len(datos) > 5:

            lat_raw = datos[2]
            lat_dir = datos[3]

            lon_raw = datos[4]
            lon_dir = datos[5]

            if lat_raw and lon_raw:

                lat = convertir_lat_lon(lat_raw, lat_dir)
                lon = convertir_lat_lon(lon_raw, lon_dir)

                # Convertir a UTM
                utm_coord = utm.from_latlon(lat, lon)

                print("Latitud:", lat)
                print("Longitud:", lon)

                print("UTM Este:", utm_coord[0])
                print("UTM Norte:", utm_coord[1])
                print("Zona:", utm_coord[2], utm_coord[3])

                print("-------------------------")
                