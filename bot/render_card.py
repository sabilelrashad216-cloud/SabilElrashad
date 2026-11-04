from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1350
ROOT = Path(__file__).resolve().parent


def font(name, size):
    paths = {
        'title': '/usr/share/fonts/truetype/noto/NotoKufiArabic-ExtraBold.ttf',
        'body': '/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf',
        'bodybold': '/usr/share/fonts/truetype/noto/NotoNaskhArabic-Bold.ttf',
        'small': '/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf',
    }
    return ImageFont.truetype(paths[name], size)


def wrap(draw, text, fnt, max_width):
    words = (text or '').split()
    lines, current = [], ''
    for word in words:
        trial = f'{current} {word}'.strip()
        if not current or draw.textbbox((0, 0), trial, font=fnt, direction='rtl')[2] <= max_width:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def draw_rtl(draw, text, fnt, xy, fill, anchor='ra'):
    draw.text(xy, text, font=fnt, fill=fill, anchor=anchor, direction='rtl', language='ar')


def render_card(kind, text, explanation='', source='', output=None, title=None):
    colors = {
        'quran': ((9, 45, 39), (231, 202, 126), (250, 246, 227), 'آية وتفسير'),
        'hadith': ((25, 43, 68), (205, 168, 88), (247, 243, 226), 'حديث وشرح'),
        'qa': ((45, 35, 58), (224, 180, 104), (250, 245, 231), 'سؤال وجواب'),
    }
    bg, gold, cream, default_title = colors.get(kind, colors['qa'])
    image = Image.new('RGB', (W, H), bg)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((28, 28, W-28, H-28), radius=28, outline=gold, width=5)
    draw.rounded_rectangle((52, 52, W-52, H-52), radius=20, outline=(140, 160, 145), width=2)
    draw_rtl(draw, 'سبيل الرشاد', font('title', 52), (W//2, 125), gold, 'ma')
    draw_rtl(draw, title or default_title, font('bodybold', 38), (W//2, 195), (190, 215, 190), 'ma')
    draw.line((150, 245, W-150, 245), fill=gold, width=3)

    y = 305
    body_size = 42 if len(text or '') < 260 else 36 if len(text or '') < 440 else 30
    body_font = font('bodybold', body_size)
    for line in wrap(draw, text, body_font, 870):
        draw_rtl(draw, line, body_font, (W-105, y), cream)
        y += body_size + 20
    y += 22
    if explanation:
        draw.line((150, y, W-150, y), fill=(140, 170, 145), width=2)
        y += 58
        draw_rtl(draw, 'التفسير والشرح', font('bodybold', 34), (W-105, y), gold)
        y += 55
        ex_size = 32 if len(explanation) < 420 else 27 if len(explanation) < 700 else 23
        while ex_size >= 16:
            ex_font = font('body', ex_size)
            ex_lines = wrap(draw, explanation, ex_font, 870)
            if y + len(ex_lines) * (ex_size + 12) <= H - 140:
                break
            ex_size -= 2
        ex_font = font('body', max(16, ex_size))
        for line in wrap(draw, explanation, ex_font, 870):
            draw_rtl(draw, line, ex_font, (W-105, y), (232, 238, 224))
            y += ex_size + 12
    if source:
        draw_rtl(draw, source, font('small', 23), (W//2, H-105), (190, 215, 190), 'ma')
    output = Path(output or (ROOT / 'generated_card.png'))
    image.save(output, quality=95)
    return str(output)


if __name__ == '__main__':
    render_card('quran', 'نص تجريبي', 'شرح تجريبي', 'سبيل الرشاد')
