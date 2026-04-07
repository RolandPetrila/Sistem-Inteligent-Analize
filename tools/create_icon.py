"""
Genereaza ris_icon.ico — iconita RIS in pure Python (zero dependinte).
Creeaza un ICO 32x32 cu litera "R" pe fundal albastru inchis (#1a1a2e).
Ruleaza: python tools/create_icon.py
"""
import os
import struct

# Culori tema RIS (BGRA format pentru ICO)
BG_COLOR = (0x2e, 0x1a, 0x1a, 0xFF)   # #1a1a2e fundal
FG_COLOR = (0xFF, 0xFF, 0xFF, 0xFF)    # alb pentru litera R
ACC_COLOR = (0xFF, 0x88, 0x44, 0xFF)   # accent portocaliu/violet


def _draw_letter_R(pixels, size=32):
    """Deseneaza litera 'R' pe o grila de pixeli."""
    # Coordonate relative la 32x32
    # Bara verticala stanga
    for y in range(6, 26):
        for x in range(7, 11):
            pixels[y][x] = FG_COLOR

    # Bara orizontala sus
    for y in range(6, 10):
        for x in range(7, 22):
            pixels[y][x] = FG_COLOR

    # Semicerc dreapta (top)
    for y in range(10, 18):
        for x in range(18, 22):
            pixels[y][x] = FG_COLOR
    for y in range(14, 18):
        for x in range(11, 22):
            pixels[y][x] = FG_COLOR

    # Picior diagonal (bottom right)
    for i in range(9):
        x = 18 + i
        y = 18 + i
        if x < 30 and y < 30:
            pixels[y][x] = FG_COLOR
            if x + 1 < 30:
                pixels[y][x + 1] = FG_COLOR
            if y + 1 < 30:
                pixels[y + 1][x] = FG_COLOR


def create_ris_icon(output_path: str, size: int = 32):
    """Genereaza fisier ICO cu un singur frame 32x32."""
    # Initializeaza grila de pixeli cu culoarea de fundal
    pixels = [[BG_COLOR] * size for _ in range(size)]

    # Deseneaza un cerc/rotunjit de fundal (optional, simplu: dreptunghi)
    # Adauga border radius (3px colt rotunjit simulat)
    for corner_y, corner_x in [(0, 0), (0, 1), (1, 0), (0, size-1), (0, size-2), (1, size-1),
                                (size-1, 0), (size-2, 0), (size-1, 1),
                                (size-1, size-1), (size-2, size-1), (size-1, size-2)]:
        if 0 <= corner_y < size and 0 <= corner_x < size:
            pixels[corner_y][corner_x] = (0, 0, 0, 0)  # transparent

    # Deseneaza litera R
    _draw_letter_R(pixels, size)

    # Construieste BMP DIB (BITMAPINFOHEADER) fara fisier header (ICO format)
    # Header: BITMAPINFOHEADER (40 bytes)
    width = size
    height = size * 2  # ICO: height dublu (XOR + AND mask)
    planes = 1
    bit_count = 32  # BGRA
    compression = 0
    image_size = width * size * 4  # bytes pentru XOR mask
    bmi = struct.pack('<IiiHHIIiiII',
                      40,           # biSize
                      width,        # biWidth
                      height,       # biHeight (dublu pt ICO)
                      planes,       # biPlanes
                      bit_count,    # biBitCount
                      compression,  # biCompression
                      image_size,   # biSizeImage
                      0, 0,         # biXPelsPerMeter, biYPelsPerMeter
                      0, 0)         # biClrUsed, biClrImportant

    # XOR mask — pixeli BGRA (bottom-up, deci randuri inversate)
    xor_data = bytearray()
    for y in range(size - 1, -1, -1):  # bottom-up
        for x in range(size):
            r, g, b, a = pixels[y][x]
            xor_data.extend([b, g, r, a])  # BGRA

    # AND mask — 0 = opac, 1 = transparent (1bpp, aliniat la 4 bytes)
    row_bytes = ((size + 31) // 32) * 4  # aliniat la DWORD
    and_data = bytearray()
    for y in range(size - 1, -1, -1):
        row = bytearray(row_bytes)
        for x in range(size):
            if pixels[y][x][3] == 0:  # transparent
                byte_idx = x // 8
                bit_idx = 7 - (x % 8)
                row[byte_idx] |= (1 << bit_idx)
        and_data.extend(row)

    image_data = bytes(bmi) + bytes(xor_data) + bytes(and_data)

    # ICO Header (6 bytes) + Directory Entry (16 bytes)
    # ICONDIR
    ico_header = struct.pack('<HHH',
                             0,   # idReserved = 0
                             1,   # idType = 1 (ICO)
                             1)   # idCount = 1 (un singur frame)

    # ICONDIRENTRY
    data_offset = 6 + 16  # dupa header + 1 entry
    entry = struct.pack('<BBBBHHII',
                        size,   # bWidth
                        size,   # bHeight
                        0,      # bColorCount = 0 (32bpp)
                        0,      # bReserved
                        1,      # wPlanes
                        32,     # wBitCount
                        len(image_data),  # dwBytesInRes
                        data_offset)      # dwImageOffset

    ico_bytes = ico_header + entry + image_data

    with open(output_path, 'wb') as f:
        f.write(ico_bytes)

    print(f"[OK] Iconita creata: {output_path} ({len(ico_bytes)} bytes)")


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    output = os.path.join(project_dir, "ris_icon.ico")
    create_ris_icon(output)
