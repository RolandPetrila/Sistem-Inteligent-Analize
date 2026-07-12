"""
Genereaza iconita profesionala RIS (Roland Intelligence System).
Foloseste Pillow pentru calitate maxima.

Design:
- Fundal: gradient diagonal dark navy (#0a0a1e → #161b3a)
- Colturi rotunjite (card look)
- 3 bare de analiza cu trend ascendent (bar chart)
- Trend line sparkline alba peste bare
- Cerc accent violet (indicator AI) dreapta-sus
- Glow subtil pe elemente

Output:
- ris_icon.ico       (multi-size: 16/32/48/64/128/256)
- frontend/public/icons/icon-192.png  (PWA)
- frontend/public/icons/icon-512.png  (PWA splash)

Ruleaza: python tools/create_icon.py
"""

from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFilter
except ImportError:
    print("[EROARE] Pillow nu e instalat. Ruleaza: pip install Pillow")
    raise

PROJECT_DIR = Path(__file__).parent.parent
ICON_ICO    = PROJECT_DIR / "ris_icon.ico"
ICONS_DIR   = PROJECT_DIR / "frontend" / "public" / "icons"


def lerp_color(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def draw_ris_icon(size: int) -> Image.Image:
    # ── Fundal gradient diagonal ────────────────────────────────────────────
    C_BG_A = (10, 10, 30)
    C_BG_B = (26, 27, 62)
    C_BG_C = (18, 20, 48)

    base = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    for y in range(size):
        for x in range(size):
            t = (x + y) / (2 * (size - 1))
            if t < 0.5:
                col = lerp_color(C_BG_A, C_BG_B, t * 2)
            else:
                col = lerp_color(C_BG_B, C_BG_C, (t - 0.5) * 2)
            base.putpixel((x, y), (*col, 255))

    # ── Colturi rotunjite (mask) ────────────────────────────────────────────
    radius = max(3, size // 7)
    mask   = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, size - 1, size - 1], radius=radius, fill=255
    )
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    img.paste(base, mask=mask)
    draw = ImageDraw.Draw(img)

    # ── Zona chart ──────────────────────────────────────────────────────────
    m       = size * 0.13          # margin
    cl      = m + size * 0.04     # chart left
    cr      = size - m - size * 0.06   # chart right
    cb      = size - m - size * 0.06   # chart bottom
    ct      = m + size * 0.10     # chart top

    # 3 bare, trend ascendent
    heights = [0.40, 0.63, 0.87]
    C_BARS  = [
        (67,  97, 238),   # #4361ee albastru
        (76, 201, 240),   # #4cc9f0 cyan
        (72,  52, 212),   # #4834d4 indigo
    ]

    bar_count  = 3
    bar_gap_r  = 0.18     # gap ca fractie din latime totala
    total_w    = cr - cl
    gap_total  = total_w * bar_gap_r * (bar_count - 1)
    bar_w      = (total_w - gap_total) / bar_count

    bar_tops = []
    for i, (h, c) in enumerate(zip(heights, C_BARS)):
        x0 = cl + i * (bar_w + total_w * bar_gap_r)
        x1 = x0 + bar_w
        bh = (cb - ct) * h
        y0 = cb - bh
        y1 = cb

        r = max(1, int(bar_w * 0.22))

        # Glow (layer semi-transparent)
        gx = bar_w * 0.18
        draw.rounded_rectangle(
            [x0 - gx, y0, x1 + gx, y1],
            radius=r + 1, fill=(*c, 35)
        )
        # Bara principala
        draw.rounded_rectangle([x0, y0, x1, y1], radius=r, fill=(*c, 255))

        # Highlight pe marginea stanga-sus
        hi_w = max(1, int(bar_w * 0.12))
        hi_c = lerp_color(c, (255, 255, 255), 0.35)
        draw.rounded_rectangle(
            [x0, y0, x0 + hi_w, y1],
            radius=r, fill=(*hi_c, 180)
        )

        bar_tops.append((int((x0 + x1) / 2), int(y0)))

    # ── Trend line sparkline ────────────────────────────────────────────────
    C_LINE  = (255, 255, 255)
    lw      = max(1, size // 26)
    dot_r   = max(1, size // 22)

    for i in range(len(bar_tops) - 1):
        draw.line([bar_tops[i], bar_tops[i + 1]],
                  fill=(*C_LINE, 200), width=lw)
    for px, py in bar_tops:
        draw.ellipse(
            [px - dot_r, py - dot_r, px + dot_r, py + dot_r],
            fill=(*C_LINE, 255)
        )

    # ── Accent AI (cerc violet, dreapta-sus) ────────────────────────────────
    C_AI   = (114,  9, 183)   # #7209b7
    C_AI_L = (167, 90, 255)

    ai_r  = max(3, size // 9)
    ai_cx = int(size * 0.80)
    ai_cy = int(size * 0.20)

    # Glow exterior (straturi concentrice)
    for extra in range(ai_r + 5, ai_r, -1):
        a = int(55 * (1 - (extra - ai_r) / 5))
        draw.ellipse(
            [ai_cx - extra, ai_cy - extra, ai_cx + extra, ai_cy + extra],
            fill=(*C_AI, a)
        )
    # Cerc principal
    draw.ellipse(
        [ai_cx - ai_r, ai_cy - ai_r, ai_cx + ai_r, ai_cy + ai_r],
        fill=(*C_AI, 255)
    )
    # Highlight intern
    hi_r = max(1, int(ai_r * 0.55))
    draw.ellipse(
        [ai_cx - hi_r, ai_cy - hi_r - 1, ai_cx + hi_r * 0.3, ai_cy + hi_r * 0.3],
        fill=(*C_AI_L, 120)
    )
    # Punct central alb
    inner_r = max(1, ai_r // 3)
    draw.ellipse(
        [ai_cx - inner_r, ai_cy - inner_r, ai_cx + inner_r, ai_cy + inner_r],
        fill=(255, 255, 255, 255)
    )

    # ── Linie subtire jos (baza chart) ─────────────────────────────────────
    base_y = int(cb) + max(1, size // 64)
    draw.line([(int(cl), base_y), (int(cr), base_y)],
              fill=(255, 255, 255, 45), width=max(1, size // 80))

    return img


def main():
    print("[RIS Icon Generator] Pillow OK — generare iconite...")

    sizes   = [16, 32, 48, 64, 128, 256]
    images  = []
    for s in sizes:
        img = draw_ris_icon(s)
        images.append(img)
        print(f"  [{s:>3}x{s:<3}] generat")

    # ── ICO multi-size — salveaza fiecare dimensiune ca RGBA PNG in ICO ──────
    # Pillow ICO: primul Image trebuie sa fie cel mai mare pentru multi-size corect
    images_desc = list(reversed(images))   # 256 → 16
    images_desc[0].save(
        ICON_ICO,
        format="ICO",
        append_images=images_desc[1:],
    )
    # Verifica ca toate dimensiunile sunt prezente
    check = Image.open(ICON_ICO)
    saved_sizes = check.info.get("sizes", {check.size})
    print(f"[OK] {ICON_ICO} — sizes: {sorted(saved_sizes)}")

    # ── PNG-uri PWA ─────────────────────────────────────────────────────────
    ICONS_DIR.mkdir(parents=True, exist_ok=True)
    for pwa_size in [192, 512]:
        out = ICONS_DIR / f"icon-{pwa_size}.png"
        draw_ris_icon(pwa_size).save(out, format="PNG")
        print(f"[OK] {out}")

    print("\n[DONE] Toate iconitele au fost generate.")


if __name__ == "__main__":
    main()
