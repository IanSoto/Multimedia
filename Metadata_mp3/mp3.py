from mutagen.id3 import ID3, TIT2, TALB, TPE1, APIC
import os

def modificar_metadatos_mpeg(archivo_path, titulo, artista, album, portada_path):
    if not os.path.exists(archivo_path):
        print(f"❌ Error: El archivo '{archivo_path}' no existe en la carpeta.")
        return

    print(f"--- Procesando archivo MPEG: {archivo_path} ---")
    
    try:
        tags = ID3(archivo_path)
    except Exception:
        print("  > El archivo no tiene etiquetas previas. Creando nuevas...")
        tags = ID3()

    tags["TIT2"] = TIT2(encoding=3, text=titulo)
    tags["TPE1"] = TPE1(encoding=3, text=artista)
    tags["TALB"] = TALB(encoding=3, text=album)

    try:
        with open(portada_path, 'rb') as img:
            tags["APIC"] = APIC(
                encoding=3,
                mime='image/png',
                type=3,
                desc=u'Cover',
                data=img.read()
            )
    except FileNotFoundError:
        print(f"  > No se encontró la imagen: {portada_path}")

    tags.save(archivo_path, v2_version=3)
    print(f"✅ ¡Proceso completado para {archivo_path}!")

modificar_metadatos_mpeg(
    archivo_path="La celula que explota.mp3", 
    titulo="Amor",
    artista="Soda estereo",
    album="Senderos de traición",
    portada_path="corazon.png"
)