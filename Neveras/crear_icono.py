#!/usr/bin/env python3
"""
Genera el icono neveras.ico en la misma carpeta.
Se ejecuta automáticamente desde INICIAR_NEVERAS.bat
"""
import os, struct, zlib

def make_ico():
    """Genera un ICO 32x32 con diseño de nevera/hielo en colores del dashboard."""
    
    # Crear imagen 32x32 RGBA
    size = 32
    img = []
    
    for y in range(size):
        row = []
        for x in range(size):
            # Fondo transparente
            r, g, b, a = 0, 0, 0, 0
            
            # Nevera body (rectángulo redondeado azul oscuro)
            if 4 <= x <= 27 and 2 <= y <= 30:
                r, g, b, a = 17, 19, 24, 255  # --s1 color
            
            # Borde de la nevera (verde acento)
            if (x == 4 or x == 27) and 2 <= y <= 30:
                r, g, b, a = 0, 229, 160, 255
            if (y == 2 or y == 30) and 4 <= x <= 27:
                r, g, b, a = 0, 229, 160, 255
            
            # División entre congelador y nevera
            if 11 <= y <= 12 and 4 <= x <= 27:
                r, g, b, a = 0, 229, 160, 255
            
            # Manija congelador
            if 6 <= y <= 9 and 23 <= x <= 25:
                r, g, b, a = 0, 229, 160, 255
            
            # Manija nevera
            if 17 <= y <= 24 and 23 <= x <= 25:
                r, g, b, a = 0, 229, 160, 255
            
            # Cristal congelador (azul hielo)
            if 4 <= y <= 10 and 6 <= x <= 20:
                r, g, b, a = 61, 139, 255, 180
            
            # Floco de nieve simplificado (cruces blancas)
            cx, cy = 13, 7
            if (x == cx and cy-2 <= y <= cy+2) or (y == cy and cx-2 <= x <= cx+2):
                r, g, b, a = 255, 255, 255, 255
            
            row.append((r, g, b, a))
        img.append(row)
    
    # Convertir a bytes PNG-like (raw BGRA para ICO)
    raw = b''
    for row in reversed(img):  # ICO es bottom-up
        for (r, g, b, a) in row:
            raw += bytes([b, g, r, a])
    
    # BMP header para ICO (BITMAPINFOHEADER)
    width, height = size, size
    bpp = 32
    
    # BITMAPINFOHEADER (40 bytes)
    biSize = 40
    biWidth = width
    biHeight = height * 2  # *2 porque incluye máscara AND
    biPlanes = 1
    biBitCount = bpp
    biCompression = 0
    biSizeImage = width * height * 4
    biXPelsPerMeter = 0
    biYPelsPerMeter = 0
    biClrUsed = 0
    biClrImportant = 0
    
    dib = struct.pack('<IiIHHIIiiII',
        biSize, biWidth, biHeight, biPlanes, biBitCount,
        biCompression, biSizeImage,
        biXPelsPerMeter, biYPelsPerMeter,
        biClrUsed, biClrImportant)
    
    dib += raw
    
    # AND mask (all zeros = fully visible)
    mask_row_size = ((width + 31) // 32) * 4
    dib += b'\x00' * (mask_row_size * height)
    
    # ICO header
    # ICONDIR
    ico_header = struct.pack('<HHH', 0, 1, 1)  # reserved, type=1(ICO), count=1
    
    # ICONDIRENTRY
    img_offset = 6 + 16  # sizeof ICONDIR + sizeof ICONDIRENTRY
    entry = struct.pack('<BBBBHHII',
        width,   # width
        height,  # height
        0,       # color count (0 = more than 256)
        0,       # reserved
        1,       # planes
        bpp,     # bit count
        len(dib),# size of image data
        img_offset  # offset
    )
    
    ico_data = ico_header + entry + dib
    
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'neveras.ico')
    with open(out_path, 'wb') as f:
        f.write(ico_data)
    print(f"Icono creado: {out_path}")

if __name__ == '__main__':
    make_ico()
