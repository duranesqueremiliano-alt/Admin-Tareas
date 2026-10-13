"""
Instala las librerías que necesita la app (customtkinter).
Ejecútalo una sola vez:  python instalar_dependencias.py
"""
import subprocess
import sys
from pathlib import Path

requisitos = Path(__file__).with_name("requirements.txt")
print(f"Usando Python: {sys.executable}")
resultado = subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(requisitos)])
if resultado.returncode == 0:
    print("\nListo. Ya puedes abrir la app con:  python appprin.py")
else:
    print("\nNo se pudo instalar. Revisa tu conexión a internet e inténtalo de nuevo.")
