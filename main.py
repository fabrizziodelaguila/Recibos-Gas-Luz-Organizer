import os
import shutil
import time
import re
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import logging
from PyPDF2 import PdfReader
import pdfplumber
from dotenv import load_dotenv

logging.basicConfig(level=logging.ERROR)

load_dotenv()

carpeta_origen = os.getenv("CARPETA_ORIGEN")
dest_gas = os.getenv("DEST_GAS")
dest_luz = os.getenv("DEST_LUZ")

suministros_gas = {}
suministros_gas_str = os.getenv("SUMINISTROS_GAS", "")
for s in suministros_gas_str.split(","):
    s = s.strip()
    if s:
        suministros_gas[s] = s

suministro_luz = os.getenv("SUMINISTRO_LUZ")

meses = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}

def extraer_texto_pdf(ruta_pdf):
    try:
        reader = PdfReader(ruta_pdf)
        texto = ""
        for page in reader.pages:
            texto += page.extract_text() or ""
        return texto
    except Exception as e:
        print(f"❌ Error leyendo PDF con PyPDF2: {e}")
        return ""

def extraer_texto_pdf_pdfplumber(ruta_pdf):
    try:
        with pdfplumber.open(ruta_pdf) as pdf:
            texto = ""
            for page in pdf.pages:
                texto += page.extract_text() or ""
        return texto
    except Exception as e:
        print(f"❌ Error leyendo PDF con pdfplumber: {e}")
        return ""

def extraer_fecha(texto):
    match = re.search(r"(\d{2})/(\d{2})/(\d{4})", texto)
    if match:
        try:
            return datetime.strptime(match.group(0), "%d/%m/%Y")
        except:
            pass
    return None

def extraer_fecha_luz(texto):
    match = re.search(r"\d{2}-[A-Za-z]{3}-\d{4}", texto)
    if match:
        try:
            return datetime.strptime(match.group(0), "%d-%b-%Y")
        except:
            pass
    return None

def obtener_mes_anterior(mes):
    mes_anterior = mes - 1 if mes > 1 else 12
    return meses[mes_anterior]

class Handler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return

        archivo = os.path.basename(event.src_path)
        ruta = event.src_path
        print(f"📥 Nuevo archivo detectado: {ruta}")
        print(f"🔍 Nombre del archivo detectado: {archivo}")

        if archivo.endswith(".tmp"):
            print("⏳ Archivo temporal detectado, esperando que se complete la descarga...")
            time.sleep(5)

            archivos_a_buscar = [f"{suministro_luz}.pdf", "EstadoCuenta.pdf"]
            encontrado = False
            for nombre_pdf in archivos_a_buscar:
                posible_pdf = os.path.join(carpeta_origen, nombre_pdf)
                if os.path.exists(posible_pdf):
                    print(f"📄 Archivo {nombre_pdf} detectado tras esperar.")
                    self.procesar_pdf(posible_pdf)
                    encontrado = True
                    break

            if not encontrado:
                print(f"❌ No se encontró ni '{suministro_luz}.pdf' ni 'EstadoCuenta.pdf' después de esperar.")
            return

        if archivo.lower().endswith(".pdf"):
            self.procesar_pdf(ruta)
        else:
            print("⚠️ Archivo ignorado (no es PDF).")

    def procesar_pdf(self, ruta):
        archivo = os.path.basename(ruta)

        if archivo in [f"{suministro_luz}.pdf", "EstadoCuenta.pdf"]:
            texto = extraer_texto_pdf_pdfplumber(ruta)
        else:
            texto = extraer_texto_pdf(ruta)

        if archivo in [f"{suministro_luz}.pdf", "EstadoCuenta.pdf"]:
            print(f"✅ Archivo coincide con '{archivo}'")
            fecha = extraer_fecha_luz(texto)
            if fecha:
                mes_anterior = obtener_mes_anterior(fecha.month)
                nuevo_nombre = f"Recibo de luz - {suministro_luz} ({mes_anterior}).pdf"
                destino = os.path.join(dest_luz, nuevo_nombre)
                print(f"📦 Moviendo recibo de luz a: {destino}")
                shutil.move(ruta, destino)
            else:
                print(f"❌ No se pudo extraer fecha del recibo de luz: {ruta}")
            return
        else:
            print(f"❌ Archivo no coincide con '{suministro_luz}.pdf' ni 'EstadoCuenta.pdf'. Es: '{archivo}'")

        if "gas natural" in texto.lower():
            fecha = extraer_fecha(texto)
            if not fecha:
                print(f"❌ No se pudo extraer fecha del recibo de gas: {ruta}")
                return

            mes_anterior = obtener_mes_anterior(fecha.month)
            for suministro in suministros_gas:
                if suministro in texto:
                    nuevo_nombre = f"Recibo de gas - {suministro} ({mes_anterior}).pdf"
                    destino = os.path.join(dest_gas, nuevo_nombre)
                    print(f"📦 Moviendo recibo de gas a: {destino}")
                    shutil.move(ruta, destino)
                    return

            print(f"❌ No se encontró ningún suministro conocido en: {ruta}")
            return

        print(f"❌ No se pudo identificar tipo o fecha en: {ruta}")

if __name__ == "__main__":
    print("🔍 Monitoreando carpeta para nuevos recibos...")
    event_handler = Handler()
    observer = Observer()
    observer.schedule(event_handler, carpeta_origen, recursive=False)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
