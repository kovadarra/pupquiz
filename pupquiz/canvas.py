import re
from contextlib import suppress
from queue import Empty, PriorityQueue, Queue
from sys import maxsize
from threading import Thread
from time import time_ns

from .config import cfg
from .graphics import Image, ImageDraw, ImageOps, blur, encode
from .vocab_pick import Set

CANVAS_SZ = (cfg['image-max-width'], cfg['image-max-height'])
CC_CNV_GAP = 10
CC_BORDER = 10
P_PAUSE_GIF = re.compile(cfg['patt-gif-loop-pause']).search
PAUSE_GIF_DUR = cfg['gif-pause-duration'] * 1_000_000_000


def im_resize(im: Image.Image, w: int, h: int) -> Image.Image:
    imw, imh = im.size
    wscale = min((1, w / imw))
    hscale = min((1, h / imh))
    scale = min((wscale, hscale))
    sz = (int(imw * scale), int(imh * scale))
    return im.resize(sz)


class Canvas:
    def __init__(self, win):
        self.__sgimgs = (win['-IM1-'], win['-IM2-'], win['-IM3-'])
        self.__ccwidth = win.size[0] - CANVAS_SZ[0] + CC_BORDER
        self.__ccmargin = (
            win.size[1] - win['-CCARD-'].Widget.winfo_height()) // 2 - CC_BORDER
        self.__set = []
        self.__frames = None
        self.__imq = PriorityQueue()
        self.__nimgs = 0
        self.__imid = 0

    def __im_prepare(self, im: Image.Image):
        '''
        Prepares given frame for presentation as the window background image.

        Because background images aren't actually supported, the image is split into tiles instead.
        '''
        cw, ch = CANVAS_SZ
        ww, wh = cw + self.__ccwidth + CC_CNV_GAP, ch
        bg = blur(ImageOps.fit(im, (ww, wh), centering=(0, 0.5)), False)

        # Paste canvas (clear image)
        cnv = im_resize(im, cw, ch)
        cx = int((cw - cnv.size[0]) / 2)
        cy = int((ch - cnv.size[1]) / 2)
        bg.paste(cnv, (cx, cy))

        # Draw rounded edge of command card
        d: ImageDraw = ImageDraw.Draw(bg)
        ccx, ccy = ww - self.__ccwidth, self.__ccmargin
        rc = [ccx, ccy + CC_BORDER, ccx +
              CC_BORDER, wh - self.__ccmargin - CC_BORDER - 1]
        d.rectangle(rc, cfg['color-background'])
        d.pieslice([ccx, rc[1] - CC_BORDER, ccx + CC_BORDER * 2,
                    rc[1] + CC_BORDER], 180, 270, cfg['color-background'])
        d.pieslice([ccx, rc[3] - CC_BORDER, ccx + CC_BORDER * 2,
                    rc[3] + CC_BORDER], 90, 180, cfg['color-background'])

        # Return image data
        return encode(bg.crop((0, 0, rc[2], wh))), encode(bg.crop(
            (rc[2], 0, ww, self.__ccmargin))), encode(bg.crop((rc[2], wh - self.__ccmargin, ww, wh)))

    def __set_frame(self):
        '''
        Presents the currently active frame. Only call from main thread.
        '''
        immain, imtopr, imbotr = self.__sgimgs
        data = self.__frames[self.__frame_idx][0]
        szcnv = (CANVAS_SZ[0] + CC_CNV_GAP + CC_BORDER, CANVAS_SZ[1])
        szmrg = (self.__ccwidth - CC_BORDER, self.__ccmargin)
        immain(data=data[0], size=szcnv)
        imtopr(data=data[1], size=szmrg)
        imbotr(data=data[2], size=szmrg)

    def __build_frames(self, path, imid):
        '''
        Produces a set of background image frames representing given image.
        '''
        frames = []
        with Image.open(path, 'r') as im:
            with suppress(EOFError):
                while True:
                    frames.append([self.__im_prepare(
                        im), im.info['duration'] * 1_000_000 if 'duration' in im.info else 0])
                    im.seek(len(frames))
        if P_PAUSE_GIF(path):
            frames[-1][1] += PAUSE_GIF_DUR
        self.__imq.put((imid, frames))

    def set_image(self, set_: Set, img_idx: int):
        '''
        Submit a new image for presentation. Will be prepared on another thread.
        '''
        if self.__set != set_:
            self.__set, self.__img_idx = set_, img_idx
        elif self.__img_idx > img_idx:
            self.__img_idx = img_idx
        elif self.__img_idx < img_idx:
            self.__img_idx = img_idx
        else:
            return  # Same
        self.__nimgs += 1
        Thread(target=Canvas.__build_frames, args=(
            self, set_[self.__img_idx], -self.__nimgs), daemon=True).start()

    def update(self):
        '''
        Updates the presented image, if necessary. Call frequently from program main loop.

        Returns, in milliseconds, the time to wait for next update() call.
        '''
        with suppress(Empty):
            imid, frames = self.__imq.get(not self.__frames)
            if self.__imid > imid:  # Only consider newer images
                self.__imid, self.__frames = imid, frames
                self.__time = time_ns()
                self.__frame_idx = 0
        time_ = time_ns()
        frame_time = time_ - self.__time
        if self.__frames[self.__frame_idx][1] <= frame_time:
            nframes = len(self.__frames)
            self.__frame_idx = (self.__frame_idx + 1) % nframes
            if nframes == 1:
                self.__frames[self.__frame_idx][1] = maxsize
            self.__time = time_
            self.__set_frame()
            frame_time = time_ns() - self.__time
            # return self.__frames[self.__frame_idx][1] / 1_000_000
        return max(
            0, (self.__frames[self.__frame_idx][1] - frame_time) / 1_000_000)
