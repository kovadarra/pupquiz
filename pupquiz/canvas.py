import re
from contextlib import suppress
from sys import maxsize
from time import time_ns

from PIL import Image

from .config import cfg
from .session import Set
from .thumbnail import encode

CANVAS_SZ = (cfg['image-max-width'], cfg['image-max-height'])
ppausegif = re.compile(cfg['patt-gif-loop-pause']).search
pausegifdur = cfg['gif-pause-duration'] * 1_000_000_000


def im_resize(im: Image.Image):
    w, h = im.size
    wscale = min((1, CANVAS_SZ[0] / w))
    hscale = min((1, CANVAS_SZ[1] / h))
    scale = min((wscale, hscale))
    sz = (int(w*scale), int(h*scale))
    return im.resize(sz)


class Canvas:
    def __init__(self, sgimg):
        self.__sgimg = sgimg
        self.__set = []

    def set_image(self, set_: Set, img_idx: int, no_advance):
        if self.__set != set_:
            self.__set, self.__img_idx = set_, 0
        elif self.__img_idx > img_idx:
            self.__img_idx = img_idx
        elif self.__img_idx < img_idx and not no_advance:
            self.__img_idx = img_idx
        else:
            return
        path = set_[self.__img_idx]
        self.__time = time_ns()
        self.__frame_idx = 0
        self.__frames = []
        with Image.open(path, 'r') as im:
            with suppress(EOFError):
                while True:
                    self.__frames.append((encode(im_resize(
                        im)), im.info['duration'] * 1_000_000 if 'duration' in im.info else maxsize))
                    im.seek(len(self.__frames))
        if ppausegif(path):
            last_frame = self.__frames[-1]
            self.__frames[-1] = (last_frame[0],
                                 last_frame[1] + pausegifdur)
        self.__sgimg(data=self.__frames[0][0], size=CANVAS_SZ)

    def update(self):
        time_ = time_ns()
        frame_time = time_ - self.__time
        if self.__frames[self.__frame_idx][1] < frame_time:
            self.__frame_idx = (self.__frame_idx + 1) % len(self.__frames)
            self.__time = time_
            self.__sgimg(
                data=self.__frames[self.__frame_idx][0], size=CANVAS_SZ)
