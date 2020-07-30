import ctypes
import gc
import glob
import json
import os
import pickle
import re
from itertools import chain, groupby, islice
from operator import itemgetter
from random import Random
from sys import maxsize
from typing import Dict, Iterator, List, Optional, Tuple

import PySimpleGUI as sg

from .config import (CFG_APPNAME, CFG_CONFIRM_DELETE, CFG_CONFIRM_RESET,
                     CFG_PATH, CFG_SELECT_INFO, cfg, data_path)
from .graphics import encode, get_def_thumbnail, make_thumbnail

SES_SET_DIRS = ''
SES_LAST_DIR = 'last-dir'
SES_VOCABS = 'vocabs'
SES_WIN_POS = 'win-pos'
SES_CFG_DATE = 'config-date'
SES_ADD_V_HOVER = 'add-v-hover'
SES_ADD_V_DEF = 'add-v-def'
SES_SELECT_GUIDE_HEIGHT = 'sel-guide-h'

VOCAB_NAME = 'name'
VOCAB_PATH = 'path'
VOCAB_WORDS = 'words'
VOCAB_ICON_ON = 'icon-on'
VOCAB_ICON_OFF = 'icon-off'
VOCAB_DATE = 'date'
VOCAB_GALLERY = 'gallery'
VOCAB_CONFIG = 'config'

NVOCABS = 9

setmatch = re.compile(cfg['patt-set']).match
worditer = re.compile(cfg['patt-vocab-word']).finditer
word_subdiv = re.compile(cfg['patt-vocab-word-subdivider']).split
contentsearch = re.compile(cfg['patt-vocab-file']).search
vconfigsearch = re.compile(cfg['patt-vocab-config']).search

# Set is a collection of pictures with continuity
Set = List[str]


class SetProvider:
    def __init__(self, v):
        self.__v = v
        self.__sets = {
            **get_sets(os.path.dirname(v[VOCAB_PATH])), **common_sets}
        self.__keys = Random(v[VOCAB_NAME]).sample(
            [*self.__sets], len(self.__sets))

        # Remove references to outdated sets (gallery info comes from disk)
        self.__gallery = v[VOCAB_GALLERY] = [
            *({*v[VOCAB_GALLERY]} & {*self.__keys})]

        # Order keys so that unlocked are first, then locked
        self.__keys = sorted(
            self.__keys, key=lambda x: x not in self.__gallery)

    def reset_progress(self) -> bool:
        'Clears gallery, moves words to the first bucket. Calls update_vocab.'
        if sg.popup_ok_cancel(CFG_CONFIRM_RESET.format(self.__v[VOCAB_NAME]), title=CFG_APPNAME) != 'OK':
            return False
        self.__keys.extend(self.__gallery)
        self.__gallery.clear()
        for l in self.__v[VOCAB_WORDS]:
            l *= 0
        update_vocab(self.__v)
        return True

    def get_image(self, step: float) -> Tuple[List[str], int]:
        'Returns set and image index associated with given index value between [0,1).'
        s, i = divmod(len(self.__sets)*step, 1)
        key = self.__keys[int(s)]
        s = self.__sets[key]
        return [f'{key}{v}' for v in s], int(i*len(s))


def new_vocab() -> dict:
    return {VOCAB_WORDS: [[], [], [], [], [], []], VOCAB_GALLERY: []}


try:
    with open(data_path('session'), 'rb') as f:
        ses = pickle.load(f)
except FileNotFoundError:
    ses = {SES_LAST_DIR: '', SES_CFG_DATE: 0, SES_SELECT_GUIDE_HEIGHT: None, SES_WIN_POS: (None, None),
           SES_VOCABS: [new_vocab() for _ in range(NVOCABS)]}


def get_icon(idx: int, on: bool = False):
    key = 'icon-on' if on else 'icon-off'
    d = ses[SES_VOCABS][idx]
    return d[key] if key in d else def_on if on else def_off


def get_sets(*paths) -> Dict[str, List[str]]:
    it = map(lambda m: (m['set'], m['img']), filter(None, map(setmatch, chain.from_iterable(
        glob.iglob(os.path.join(path, '**/**'), recursive=True) for path in paths))))
    return {set_: sorted(list({i[1] for i in imgs})) for set_, imgs in groupby(it, itemgetter(0))}


def calc_progress(words):
    nwords = sum(map(len, words))
    nsteps = nwords * (len(words)-2)
    return sum(i*len(l) for i, l in enumerate(words[2:], start=1)) / nsteps


def save_session():
    with open(data_path('session'), 'wb') as f:
        pickle.dump(ses, f)


def update_thumbnail(v: dict):
    progress = calc_progress(v[VOCAB_WORDS])
    set_, img = SetProvider(v).get_image(progress)
    v[VOCAB_ICON_ON], v[VOCAB_ICON_OFF] = make_thumbnail(
        set_[img], v[VOCAB_NAME], progress)


def is_slot_used(s: dict):
    return VOCAB_ICON_ON in s


def update_vocab(v: dict):
    'Submits progress to disk and generates thumbnail reflecting done progress'

    with open(v[VOCAB_PATH], 'r', encoding='U8') as f:
        m = contentsearch(f.read())
        contents, title = m['contents'], m['title']
        mconfig = vconfigsearch(contents)

    # Form a set of word-translation pairs
    def div(x): return filter(None, word_subdiv(x))
    words = {(x[0].strip(), x[1].strip()) for x in chain.from_iterable(
        map(list, zip(div(m['q']), div(m['a']))) for m in worditer(contents))}

    # Clean buckets of old words, set words be only new words
    for bucket in v[VOCAB_WORDS][1:]:
        as_set = {tuple(x) for x in bucket} & words
        words -= as_set
        bucket[:] = [*as_set]

    v[VOCAB_WORDS][0] = [*words]
    v[VOCAB_DATE] = os.path.getmtime(v[VOCAB_PATH])
    v[VOCAB_NAME] = title
    v[VOCAB_CONFIG] = json.loads(mconfig[1]) if mconfig else {}
    update_thumbnail(v)


def remove_vocab(vidx: int, win: sg.Window):
    v = ses[SES_VOCABS][vidx]
    if is_slot_used(v):
        if sg.popup_ok_cancel(CFG_CONFIRM_DELETE.format(v[VOCAB_NAME]), title=CFG_APPNAME, keep_on_top=True) == 'OK':
            ses[SES_VOCABS][vidx] = new_vocab()
            win[vidx].update(image_data=get_icon(vidx, False))


# Get common sets
common_sets = get_sets(*cfg['common-sets'])
if len(common_sets) < NVOCABS:
    raise RuntimeError('Not enough sets to represent all the vocabularies')


# Has user made changes to config file?
if ses[SES_CFG_DATE] < os.path.getmtime(CFG_PATH):
    ses[SES_WIN_POS] = (None, None)
    ses[SES_SELECT_GUIDE_HEIGHT] = None
    ses[SES_CFG_DATE] = os.path.getmtime(CFG_PATH)
    ses[SES_ADD_V_HOVER], ses[SES_ADD_V_DEF] = get_def_thumbnail()
    for v in map(ses[SES_VOCABS].__getitem__, range(9)):
        if is_slot_used(v):
            update_thumbnail(v)
def_on, def_off = ses[SES_ADD_V_HOVER], ses[SES_ADD_V_DEF]


def get_vocabulary(event: Optional[int] = None) -> Tuple[dict, SetProvider]:
    'Presents vocabulary selection screen and returns chosen vocab + its sets'

    if event is not None:
        v = ses[SES_VOCABS][event]
        return v, SetProvider(v)

    # First row: info + guide, second-to-fourth rows: vocabulary slots (3 per row)
    guidesz = (cfg['select-info-guide-width'], cfg['select-info-guide-height'])
    layout = [[sg.Image(key='-INFO-GUIDE-', background_color=cfg['color-select-info-guide'], size=guidesz, pad=((0, 10), (40, 10))),
               sg.T(CFG_SELECT_INFO, pad=(0, (40, 10)), auto_size_text=True, key='-INFO-')]] +\
        [[sg.B(key=j, pad=(10, 10), image_data=get_icon(j), button_color=(
            None, cfg['color-background'])) for j in range(i*3, i*3+3)] for i in range(3)] +\
        [[sg.B(image_filename=cfg['image-folder-off'], pad=(0, 0), key='-DIR-',
               button_color=(None, cfg['color-background']))]]

    win_loc = ses[SES_WIN_POS]
    win = sg.Window(CFG_APPNAME, layout, finalize=True, location=win_loc,
                    margins=(40, 0), font=cfg['font'], return_keyboard_events=True)

    # Initialize mouse events
    but_locs = []
    halfsz = cfg['thumbnail-size'] / 2
    winx, winy = win.TKroot.winfo_rootx() - halfsz, win.TKroot.winfo_rooty() - halfsz
    for i in range(9):
        w = win[i].Widget
        but_locs.append((w.winfo_rootx() - winx, w.winfo_rooty() - winy))
        v = ses[SES_VOCABS][i]
        if VOCAB_PATH in v and os.path.getmtime(v[VOCAB_PATH]) > v[VOCAB_DATE]:
            update_vocab(v)
        win[i].bind('<Enter>', '+ENTER+')
        win[i].bind('<Leave>', '+LEAVE+')
        win[i].bind('<Button-1>', '+LCLICK+')
        win[i].bind('<Button-3>', '+RCLICK+')
        win[i].bind('<ButtonRelease-1>', '+LRELEASE+')
        win[i].bind('<B1-Motion>', '+B1MOT+')
    dir_ = win['-DIR-']
    dir_.Widget.bind('<Enter>', lambda e: dir_(
        image_filename=cfg['image-folder-on']))
    dir_.Widget.bind('<Leave>', lambda e: dir_(
        image_filename=cfg['image-folder-off']))
    dir_.Widget.bind('<Button-1>', lambda e: ctypes.windll.shell32.ShellExecuteW(
        None, u'open', u'explorer.exe', u'/n,/select, ' + CFG_PATH, None, 1))

    # Window event loop
    cur_drag_bi, did_drag, need_save = None, False, False
    while True:
        while True:
            event, values = win.read(timeout=500)
            if event is None:
                if need_save:
                    save_session()
                win.close()
                layout = None
                win = None
                gc.collect()
                return None, None
            ses[SES_WIN_POS] = list(win.CurrentLocation())
            if event != sg.TIMEOUT_EVENT:
                break

        # Vocabulary hotkey?
        if type(event) == str:
            vidx = cfg['select-hotkeys'].find(event)
            if vidx != -1:
                event = vidx

        # Thumbnail select?
        if type(event) == int:
            if did_drag:
                event = (event, '+LRELEASE+')
            else:
                v = ses[SES_VOCABS][event]
                if is_slot_used(v):
                    if all(not x for x in v[VOCAB_WORDS][:-1]):
                        remove_vocab(event, win)
                        continue
                    win.close()
                    layout = None
                    win = None
                    gc.collect()
                    return v, SetProvider(v)

                path = sg.PopupGetFile('', ses[SES_LAST_DIR] or '', file_types=cfg['vocab-file-types'],
                                       no_window=True, initial_folder=ses[SES_LAST_DIR])
                win.TKroot.focus_force()
                if path:
                    ses[SES_LAST_DIR] = os.path.dirname(path)
                    v[VOCAB_PATH] = path
                    update_vocab(v)
                    win[event].update(image_data=get_icon(event, False))

        # Mouse event?
        if type(event) == tuple:
            vidx, ev = event
            if ev == '+LCLICK+':
                cur_drag_bi = vidx
            elif ev == '+LRELEASE+':
                if cur_drag_bi != vidx:
                    vs = ses[SES_VOCABS]
                    vs[cur_drag_bi], vs[vidx] = vs[vidx], vs[cur_drag_bi]
                    need_save = True
                cur_drag_bi, did_drag = None, False
            elif ev == '+RCLICK+':
                remove_vocab(vidx, win)
            elif ev == '+ENTER+':
                win[vidx](image_data=get_icon(vidx, True))
            elif ev == '+LEAVE+':
                win[vidx](image_data=get_icon(vidx, False))
            elif ev == '+B1MOT+' and is_slot_used(ses[SES_VOCABS][vidx]):
                r = win.TKroot
                px, py = r.winfo_pointerx() - r.winfo_rootx(), r.winfo_pointery() - r.winfo_rooty()
                minr = maxsize
                for bi, (bx, by) in enumerate(but_locs):
                    dx, dy = bx - px, by - py
                    if (r := dx**2 + dy**2) < minr:
                        minr = r
                        new_drag_bi = bi
                if new_drag_bi != cur_drag_bi:
                    did_drag = True
                    if cur_drag_bi != vidx:
                        win[cur_drag_bi](
                            image_data=get_icon(cur_drag_bi, False))
                    cur_drag_bi = new_drag_bi
                    if cur_drag_bi != vidx:
                        win[cur_drag_bi](image_data=get_icon(vidx, True))
                        win[vidx](image_data=get_icon(cur_drag_bi, False))
                    else:
                        win[vidx](image_data=get_icon(vidx, True))
