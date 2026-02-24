import hashlib, struct, random

def derivar_clave(password: str, longitud: int) -> bytes:

 '''Genera una clave de longitud arbitraria usando SHA-256 en modo

contador'''

 clave = b''

 contador = 0

 while len(clave) < longitud:

  bloque = hashlib.sha256(password.encode() + struct.pack('<I',contador)).digest()

  clave += bloque

  contador += 1

 return clave[:longitud]

def cifrar_xor(mensaje: bytes, password: str) -> bytes:

 clave = derivar_clave(password, len(mensaje))

 return bytes(m ^ k for m, k in zip(mensaje, clave))

def descifrar_xor(cifrado: bytes, password: str) -> bytes:

 return cifrar_xor(cifrado, password) # XOR es simétrico

def seleccionar_posiciones(rng_obj, total_bytes_imagen: int, n_bits: int) -> list:
  '''Selecciona n_bits índices únicos dentro del rango válido de la
  imagen usando un objeto rng dado'''
  if n_bits > total_bytes_imagen:
      raise ValueError(f"No se pueden seleccionar {n_bits} posiciones de una población de {total_bytes_imagen} bytes. Mensaje demasiado grande o imagen muy pequeña.")
  posiciones = rng_obj.sample(range(total_bytes_imagen), n_bits)
  return sorted(posiciones) # ordenar para escritura secuencial

def semilla_de_password(password: str) -> int:

  '''Convierte la contraseña en un entero para usar como semilla'''

  hash_bytes = hashlib.sha256(password.encode()).digest()

  return int.from_bytes(hash_bytes[:8], 'big')

# Definiciones de funciones para manejar archivos BMP (asumidas de Práctica 1)
def leer_bmp(filepath):
    with open(filepath, 'rb') as f:
        header = f.read(54)  # Cabecera estándar de BMP
        # Asumimos que la cabecera es de 54 bytes y que los datos de píxeles comienzan después
        # Podríamos parsear la cabecera para obtener offset, width, height, etc.
        # Para simplificar, leemos directamente los píxeles después de la cabecera
        f.seek(18) # width
        width = struct.unpack('<I', f.read(4))[0]
        f.seek(22) # height
        height = struct.unpack('<I', f.read(4))[0]
        f.seek(10) # pixel data offset
        offset = struct.unpack('<I', f.read(4))[0]
        f.seek(0)
        header = f.read(offset)
        pixels = f.read() # Resto del archivo son los píxeles
        
        # Calcular el tamaño de fila real para BMPs que es múltiplo de 4 bytes
        row_size = ((width * 3 + 3) // 4) * 4 # 3 bytes por píxel (BGR)

    return header, pixels, width, height, row_size

def guardar_bmp(filepath, header, pixels):
    with open(filepath, 'wb') as f:
        f.write(header)
        f.write(pixels)

def embed_secure(src_path, dst_path, mensaje, password):

  header, pixels, width, height, row_size = leer_bmp(src_path) # de Práctica 1

  msg_bytes = mensaje.encode('utf-8')

  msg_cifrado= cifrar_xor(msg_bytes, password)

  # Construir datos: 4 bytes de longitud + mensaje cifrado

  datos = struct.pack('<I', len(msg_bytes)) + msg_cifrado

  # Construir flujo de bits

  bits = []

  for byte in datos:

    for i in range(7, -1, -1):

      bits.append((byte >> i) & 1)

  n_bits_to_embed = len(bits) # This is the actual number of bits to embed

  if n_bits_to_embed > len(pixels):

    raise ValueError('Mensaje demasiado grande')

  # Seleccionar posiciones con semilla derivada de la contraseña
  rng = random.Random(semilla_de_password(password))
  # Generar TODAS las posiciones posibles para la imagen, para asegurar consistencia con la extracción
  all_generated_positions = seleccionar_posiciones(rng, len(pixels), len(pixels))
  
  # Usar solo las posiciones realmente necesarias para la incrustación
  posiciones_para_incrustar = all_generated_positions[:n_bits_to_embed]

  # Incrustar

  pixels_mod = bytearray(pixels)

  for pos_idx in range(n_bits_to_embed):
    pos = posiciones_para_incrustar[pos_idx]
    bit = bits[pos_idx]
    pixels_mod[pos] = (pixels_mod[pos] & 0xFE) | bit

  guardar_bmp(dst_path, header, pixels_mod)

  print(f'[OK] {len(msg_bytes)} bytes cifrados e incrustados en {dst_path}')

def extract_secure(stego_path, password):

  _, pixels, _, _, _ = leer_bmp(stego_path)

  # Inicializar el generador de números aleatorios con la semilla de la contraseña
  rng = random.Random(semilla_de_password(password))

  # Asumimos que la longitud del mensaje siempre está en los primeros 32 bits incrustados
  # Para ello, necesitamos muestrear un número suficiente de posiciones para obtener la longitud
  # y luego el mensaje. La forma más segura es muestrear el máximo posible y luego cortar.
  max_bits_to_hide = len(pixels) # Máximo número de bits que se pueden ocultar (1 bit por byte)
  if max_bits_to_hide < 32:
      raise ValueError("La imagen es demasiado pequeña para ocultar cualquier longitud de mensaje.")

  # Generar TODAS las posiciones aleatorias posibles que se podrían haber usado para el mensaje
  # Esto se hace una vez para mantener la integridad de la secuencia aleatoria
  all_sampled_indices_sorted = seleccionar_posiciones(rng, len(pixels), max_bits_to_hide)

  # --- Paso 1: Extraer la longitud (primeros 32 bits) ---
  len_bits = []
  for i in range(32):
      pos = all_sampled_indices_sorted[i]
      len_bits.append(pixels[pos] & 1)

  # Reconstruir los 4 bytes de la longitud
  len_bytes = bytearray()
  for i in range(0, 32, 8):
      byte = 0
      for bit_idx in range(i, i+8):
          byte = (byte << 1) | len_bits[bit_idx]
      len_bytes.append(byte)
  
  msg_len = struct.unpack('<I', bytes(len_bytes))[0]

  # --- Paso 2: Extraer el mensaje cifrado completo ---
  total_bits_actual = 32 + msg_len * 8

  # Asegurarse de que la longitud del mensaje extraído no exceda lo que se muestreó inicialmente
  if total_bits_actual > max_bits_to_hide:
      raise ValueError("La longitud del mensaje extraído implica más bits de los que se muestrearon inicialmente o de los que caben en la imagen.")

  # Obtener las posiciones reales para todo el mensaje (longitud + contenido) de la lista ya generada
  actual_message_positions_sorted = all_sampled_indices_sorted[:total_bits_actual]
  
  # Extraer TODOS los bits de las posiciones reales
  all_extracted_bits = []
  for i in range(total_bits_actual):
      pos = actual_message_positions_sorted[i]
      all_extracted_bits.append(pixels[pos] & 1)

  # Excluir los 32 bits de longitud del inicio antes de reconstruir el cifrado
  cifrado_bits_only = all_extracted_bits[32:]

  # Reconstruir bytes cifrados a partir de cifrado_bits_only
  cifrado = bytearray()
  for i in range(0, len(cifrado_bits_only), 8):
      byte = 0
      for bit in cifrado_bits_only[i:i+8]:
          byte = (byte << 1) | bit
      cifrado.append(byte)

  # Descifrar
  return descifrar_xor(bytes(cifrado), password).decode('utf-8')

CLAVE = 'Telemática@2025'

MENSAJE = 'Datos confidenciales de la red 10.0.1.0/24'

embed_secure('kiss.bmp', 'stego_seguro.bmp', MENSAJE, CLAVE)

# Extracción con clave correcta

resultado = extract_secure('stego_seguro.bmp', CLAVE)

print(f'Clave correcta → "{resultado}"')

assert resultado == MENSAJE

# Extracción con clave incorrecta (debe producir basura)

try:

  basura = extract_secure('stego_seguro.bmp', 'claveWrong')

  print(f'Clave incorrecta → "{basura[:30]}..." (texto ilegible esperado)')

except Exception as e:

  print(f'Clave incorrecta → Error: {e}')

def chi_cuadrado_lsb(filepath):

  _, pixels, _, _, _ = leer_bmp(filepath)

  ceros = sum(1 for b in pixels if (b & 1) == 0)

  unos = len(pixels) - ceros

  esperado = len(pixels) / 2

  chi2 = ((ceros - esperado)**2 + (unos - esperado)**2) / esperado

  print(f'LSBs=0: {ceros} | LSBs=1: {unos} | χ²= {chi2:.4f}')

  print(' → Valor χ² cercano a 0: distribución uniforme (sin sospecha de LSB secuencial)')

  return chi2

print('=== Imagen original ===')

chi_cuadrado_lsb('kiss.bmp')

print('=== Stego LSB secuencial (Práctica 1) ===')

chi_cuadrado_lsb('estego512_2.bmp')

print('=== Stego LSB aleatorio (Práctica 2) ===')

chi_cuadrado_lsb('stego_seguro.bmp')