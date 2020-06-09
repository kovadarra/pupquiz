from base64 import b64encode
from io import BytesIO

from PIL import (Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter,
                 ImageFont, ImageMath, ImageOps)

from .config import cfg

sz = cfg['thumbnail-size']
sample = cfg['thumbnail-sample']
cborder = cfg['thumbnail-border-color']
worksz = sz*sample
work_xy = (worksz, worksz)
font = ImageFont.truetype(
    cfg['thumbnail-font-file'], cfg['thumbnail-font-size'] * sample)


def encode(im):
    with BytesIO() as buffer:
        im.save(buffer, 'PNG')
        return b64encode(buffer.getvalue())


def gen_def_thumb(on):
    im = Image.new('RGBA', work_xy)
    draw = ImageDraw.ImageDraw(im)
    mid = worksz/2
    pad = int(sz*0.1) if on else int(sz*0.175)
    width = cfg['thumbnail-placeholder-width']
    color = cfg['thumbnail-placeholder-color-hover'] if on else cfg['thumbnail-placeholder-color-default']
    arc_bounds = (pad, pad, worksz-pad, worksz-pad)
    for i in range(12):
        draw.arc(arc_bounds, i*30, i*30+15, color, width)
    lineoff = int(worksz/4+pad)
    draw.line((lineoff, mid, worksz - lineoff, mid), color, width)
    draw.line((mid, lineoff, mid, worksz - lineoff), color, width)
    return encode(im.resize((sz, sz), resample=Image.LANCZOS))


def get_def_thumbnail():
    return gen_def_thumb(True), gen_def_thumb(False)


def blur(im):
    bright = cfg['thumbnail-undone-brightness']
    satur = cfg['thumbnail-undone-saturation']
    bleed = (1-satur)/2
    satur, bleed = satur*bright, bleed*bright
    matrix = (satur, bleed, bleed, 0,
              bleed, satur, bleed, 0,
              bleed, bleed, satur, 0)
    return im.filter(ImageFilter.GaussianBlur(
        cfg['thumbnail-undone-blur-radius'])).convert('RGB', matrix)


# def make_thumbnails()


def make_thumbnail(path, label, progress):
    with open(path, 'rb') as f:

        # Alpha mask
        mask = Image.new('L', work_xy, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0) + work_xy, fill=255)

        # Progress effect
        im = Image.open(f)
        im = ImageOps.fit(im, work_xy,
                          centering=(0.5, 0.5)).convert('RGB')
        blurred = blur(im)

        im.putalpha(mask)
        draw.pieslice(((0, 0), work_xy), -90, -90+360*progress, 0)
        im.paste(blurred, (0, 0), mask)

        # Draw text
        draw = ImageDraw.ImageDraw(im)
        text = f'{label}\n{progress*100:.2f}%'
        textw, texth = draw.multiline_textsize(text, font=font, stroke_width=1)
        text_pos = (worksz/2-textw/2, worksz/2-texth/2)
        draw.multiline_text(text_pos, text, cfg['thumbnail-font-color'], font, align="center",
                            stroke_width=cfg['thumbnail-text-stroke-size']*sample, stroke_fill=cfg['thumbnail-text-stroke-color'])
        draw.ellipse(((0, 0, worksz, worksz)),
                     outline=cfg['thumbnail-border-color'], width=cfg['thumbnail-border-size']*sample)

        # Non-hover version
        off_sz = int(sz*0.95)
        off_pad = int((sz-off_sz) * 0.5)
        off_shrunk = im.resize((off_sz, off_sz), resample=Image.LANCZOS)
        off_shrunk = ImageEnhance.Brightness(off_shrunk).enhance(0.75)
        off = Image.new('RGBA', (sz, sz))
        off.paste(off_shrunk, (off_pad, off_pad))

        # Hover version
        on = im.resize((sz, sz), resample=Image.LANCZOS)

        return encode(on), encode(off)
