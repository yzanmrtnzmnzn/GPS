import time
import serial
from serial.tools import list_ports


BAUDRATE = 4800
TIMEOUT_S = 1
SCAN_SECONDS_PER_PORT = 2.0  # tiempo máximo "escuchando" cada puerto


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
            # puerto ocupado o no accesible
            continue

    raise RuntimeError("No se encontró ningún puerto que emita tramas NMEA.")


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

    print("Leyendo NMEA (Ctrl+C para parar)...\n")
    try:
        while True:
            line = ser.readline().decode(errors="ignore").strip()
            if line:
                print(line)
    finally:
        ser.close()


if __name__ == "__main__":
    main()