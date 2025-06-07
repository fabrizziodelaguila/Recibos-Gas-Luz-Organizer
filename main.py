import os
import shutil
import time
import re
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import pdfplumber
from dotenv import load_dotenv

# --- Configuración y utilidades ---

load_dotenv()
carpeta_origen = os.getenv("CARPETA_ORIGEN")
dest_gas = os.getenv("DEST_GAS")
dest_luz = os.getenv("DEST_LUZ")
suministros_gas = [s.strip() for s in os.getenv("SUMINISTROS_GAS", "").split(",") if s.strip()]
suministro_luz = os.getenv("SUMINISTRO_LUZ")

MESES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto",
    "Septiembre", "Octubre", "Noviembre", "Diciembre"
]

def extraer_texto_pdf(ruta_pdf):
    try:
        with pdfplumber.open(ruta_pdf) as pdf:
            return "".join(page.extract_text() or "" for page in pdf.pages)
    except Exception as e:
        print(f"❌ Error leyendo PDF: {e}")
        return ""

def extraer_fecha(texto, patron, formato):
    match = re.search(patron, texto)
    if match:
        try:
            return datetime.strptime(match.group(0), formato)
        except:
            pass
    return None

def obtener_mes_anterior(mes):
    return MESES[mes - 2 if mes > 1 else 11]

def mover_archivo(origen, destino):
    print(f"📦 Moviendo archivo a: {destino}")
    shutil.move(origen, destino)

# --- Manejo de eventos ---

class Handler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory or not event.src_path.lower().endswith((".pdf", ".tmp")):
            print("⚠️ Archivo ignorado (no es PDF ni .tmp)")
            return

        archivo = os.path.basename(event.src_path)
        print(f"📥 Nuevo archivo detectado: {archivo}")

        if archivo.endswith(".tmp"):
            print("⏳ Archivo temporal, esperando descarga...")
            time.sleep(5)
            self.buscar_y_procesar([f"{suministro_luz}.pdf", "EstadoCuenta.pdf"])
        else:
            self.procesar_pdf(event.src_path)

    def buscar_y_procesar(self, nombres):
        for nombre in nombres:
            ruta = os.path.join(carpeta_origen, nombre)
            if os.path.exists(ruta):
                self.procesar_pdf(ruta)
                return
        print("❌ No se encontró archivo esperado tras la espera.")

    def procesar_pdf(self, ruta):
        texto = extraer_texto_pdf(ruta)
        archivo = os.path.basename(ruta)

        # Recibo de luz
        if archivo in [f"{suministro_luz}.pdf", "EstadoCuenta.pdf"]:
            fecha = extraer_fecha(texto, r"\d{2}-[A-Za-z]{3}-\d{4}", "%d-%b-%Y")
            if fecha:
                mes_anterior = obtener_mes_anterior(fecha.month)
                nuevo_nombre = f"Recibo de luz - {suministro_luz} ({mes_anterior}).pdf"
                mover_archivo(ruta, os.path.join(dest_luz, nuevo_nombre))
            else:
                print("❌ No se pudo extraer fecha de luz.")
            return

        # Recibo de gas
        if "gas natural" in texto.lower():
            fecha = extraer_fecha(texto, r"\d{2}/\d{2}/\d{4}", "%d/%m/%Y")
            if fecha:
                mes_anterior = obtener_mes_anterior(fecha.month)
                for suministro in suministros_gas:
                    if suministro in texto:
                        nuevo_nombre = f"Recibo de gas - {suministro} ({mes_anterior}).pdf"
                        mover_archivo(ruta, os.path.join(dest_gas, nuevo_nombre))
                        return
                print("❌ No se encontró suministro de gas en el texto.")
            else:
                print("❌ No se pudo extraer fecha de gas.")
            return

        print("❌ No se pudo identificar tipo o fecha en el archivo.")

# --- Main ---

if __name__ == "__main__":
    print("🔍 Monitoreando carpeta para nuevos recibos...")
    observer = Observer()
    observer.schedule(Handler(), carpeta_origen, recursive=False)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()