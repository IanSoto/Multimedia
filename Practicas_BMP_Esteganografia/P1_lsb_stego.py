import struct
def leer_bmp(filepath):
 '''Retorna (header_bytes, pixels, width, height, row_size)'''
 with open(filepath, 'rb') as f:
    data = f.read()
    offset = struct.unpack_from('<I', data, 10)[0]
    width = struct.unpack_from('<i', data, 18)[0]
    height = struct.unpack_from('<i', data, 22)[0]
    row_size = (width * 3 + 3) & ~3
    header = bytearray(data[:offset])
    pixels = bytearray(data[offset:])
 return header, pixels, width, height, row_size

def guardar_bmp(filepath, header, pixels):
    with open(filepath, 'wb') as f:
     f.write(header)
     f.write(pixels)

def embed_lsb(src_path, dst_path, mensaje):
  header, pixels, width, height, row_size = leer_bmp(src_path)
  msg_bytes = mensaje.encode('utf-8')
  msg_len = len(msg_bytes)
 # Convertir longitud (4 bytes) + mensaje a flujo de bits
  datos= struct.pack('<I', msg_len) + msg_bytes
  bits = []
  for byte in datos:
     for i in range(7, -1, -1): # MSB primero
        bits.append((byte >> i) & 1)
 # Verificar capacidad
        capacidad = (len(pixels) * 3) // 3 * 3 # múltiplos de 3 (B,G,R porpíxel)

# Simplificado: usar bytes secuenciales (saltando padding no es necesarioaquí)
        if len(bits) > len(pixels):
         raise ValueError('Mensaje demasiado largo para esta imagen')
 # Incrustar bits en LSB de cada byte de canal
        pixels_mod = bytearray(pixels)
        for idx, bit in enumerate(bits):
            pixels_mod[idx] = (pixels_mod[idx] & 0xFE) | bit # limpiar LSB e insertar bit
        guardar_bmp(dst_path, header, pixels_mod)
        print(f'[OK] Mensaje de {msg_len} bytes incrustado en {dst_path}')

def extract_lsb(stego_path):
    _, pixels, _, _, _ = leer_bmp(stego_path)

    # 1. Leer primeros 32 bits para obtener la longitud del mensaje
    len_bits = [pixels[i] & 1 for i in range(32)]

    # Reconstruir los 4 bytes del mensaje a partir de los bits extraídos
    msg_len_bytes = bytearray(4)
    for byte_idx in range(4):
        current_byte = 0
        for bit_offset in range(8):
            current_byte = (current_byte << 1) | len_bits[byte_idx * 8 + bit_offset]
        msg_len_bytes[byte_idx] = current_byte

    # Desempaquetar la longitud del mensaje (little-endian, '<I')
    msg_len = struct.unpack('<I', msg_len_bytes)[0]

    # 2. Calcular cuántos bits totales debemos leer (32 de longitud + mensaje)
    total_bits = 32 + msg_len * 8
    msg_bits = [pixels[i] & 1 for i in range(32, total_bits)]

    # 3. Reconstruir los bytes a partir de los bits extraídos
    msg_bytes = bytearray()
    for i in range(0, len(msg_bits), 8):
        byte = 0
        for bit in msg_bits[i:i+8]:
            byte = (byte << 1) | bit
        msg_bytes.append(byte)

    return msg_bytes.decode('utf-8')
msj_max= "x"*98300
embed_lsb('kiss512_1.bmp', 'estego512_2.bmp', msj_max)
recuperado = extract_lsb('estego512_1.bmp') 
print(f'Mensaje recuperado: {recuperado}')
assert recuperado == msj_max, '¡Error en la extracción!'
print('Prueba exitosa.')

import math
def calcular_psnr(original_path, stego_path):
 _, pix_orig, w, h, rs = leer_bmp(original_path)
 _, pix_steg, _, _, _ = leer_bmp(stego_path)
 mse = sum((a - b)**2 for a, b in zip(pix_orig, pix_steg)) / (w * h * 3)
 if mse == 0:
    return float('inf')
 psnr = 10 * math.log10(255**2 / mse)
 print(f'MSE: {mse:.6f}')
 print(f'PSNR: {psnr:.2f} dB (>40 dB: cambio imperceptible)')
 return psnr
calcular_psnr('kiss512_1.bmp', 'estego512_2.bmp')