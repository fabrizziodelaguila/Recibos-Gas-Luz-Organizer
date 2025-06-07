# 📄 Monitor de Recibos de Gas y Luz

Organiza automáticamente tus recibos PDF descargados de Calidda y Luz del Sur, moviéndolos y renombrándolos según el suministro y fecha.

---

## 🚀 Características

- Escucha cambios en la carpeta de descargas en tiempo real.
- Detecta recibos de gas y luz según contenido y número de suministro.
- Renombra y clasifica recibos en carpetas específicas por tipo y mes.
- Maneja archivos temporales y espera a que finalice la descarga.
- Usa `PyPDF2` y `pdfplumber` para extraer textos y fechas.

---

## ⚙️ Requisitos

- Python 3.8+
- Dependencias:

```bash
pip install watchdog PyPDF2 pdfplumber python-dotenv
