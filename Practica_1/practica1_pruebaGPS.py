import serial

# CONFIGURACIÓN DEL PUERTO
PORT = "COM3"   # Cambiar por el puerto donde esté el GPS
BAUDRATE = 4800

ser = serial.Serial(
    port=PORT,
    baudrate=BAUDRATE,
    bytesize=serial.EIGHTBITS,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    timeout=1
)

print("Conectado al puerto serie. Esperando datos del GPS...\n")

while True:
    linea = ser.readline()
    print(linea)