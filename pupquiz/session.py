import glob
import os
import re
from itertools import chain, groupby, islice
from operator import itemgetter
from random import Random
from typing import Dict, Iterator, List, Optional, Tuple

import PySimpleGUI as sg

import ujson

from .config import (CFG_APPNAME, CFG_CONFIRM_DELETE, CFG_CONFIRM_RESET,
                     CFG_PATH, CFG_SELECT_INFO, cfg, data_path)
from .thumbnail import encode, get_def_thumbnail, make_thumbnail

SES_SET_DIRS = ''
SES_LAST_DIR = 'last-dir'
SES_VOCABS = 'vocabs'
SES_WIN_POS = 'win-pos'
VOCAB_GALLERY = 'gallery'
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

NVOCABS = 9

setmatch = re.compile(cfg['patt-set']).match
worditer = re.compile(cfg['patt-vocab-word']).finditer
word_subdiv = re.compile(cfg['patt-vocab-word-subdivider']).split
contentsearch = re.compile(cfg['patt-vocab-file']).search

# Set is a collection of pictures with continuity
Set = List[str]


def new_vocab() -> dict:
    return {VOCAB_WORDS: [[], [], [], [], [], []], VOCAB_GALLERY: []}


try:
    with open(data_path('session.json'), 'r') as f:
        ses = ujson.load(f)
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
    return sum(i*len(l) for i, l in enumerate(words)) / (sum(map(len, words))*(len(words)-1))


def save_session_json():
    with open(data_path('session.json'), 'w') as f:
        ujson.dump(ses, f)


def update_thumbnail(v: dict):
    img = next(islice(common_sets.items(), ses[SES_VOCABS].index(v), None))

    v[VOCAB_ICON_ON], v[VOCAB_ICON_OFF] = make_thumbnail(
        os.path.join(img[0], img[1][0]), v[VOCAB_NAME], calc_progress(v[VOCAB_WORDS]))


def update_vocab(v: dict):
    'Submits progress to disk and generates thumbnail reflecting done progress'

    with open(v[VOCAB_PATH], 'r', encoding='U8') as f:
        data = contentsearch(f.read())

    # Form a set of word-translation pairs
    def div(x): return filter(None, word_subdiv(x))
    words = {(x[0].strip(), x[1].strip()) for x in chain.from_iterable(
        map(list, zip(div(m['q']), div(m['a']))) for m in worditer(data['contents']))}

    # Clean buckets of old words, set words be only new words
    for bucket in v[VOCAB_WORDS][1:]:
        bucket = {tuple(x) for x in bucket} & words
        words -= bucket

    v[VOCAB_WORDS][0] = words = [*words]
    v[VOCAB_DATE] = os.path.getmtime(v[VOCAB_PATH])
    v[VOCAB_NAME] = data['title']
    update_thumbnail(v)


def remove_vocab(vidx: int, win: sg.Window):
    v = ses[SES_VOCABS][vidx]
    if VOCAB_ICON_ON in v:
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
        if VOCAB_ICON_ON in v:
            update_thumbnail(v)
def_on, def_off = ses[SES_ADD_V_HOVER], ses[SES_ADD_V_DEF]


class SetProvider:
    '''
    Returns, in a pre-determined order, lists of image paths associated with a vocabulary.

    Can be iterated over. Advancing the iterator marks the previous set as unlocked.
    '''

    def __init__(self, v):
        self.__v = v
        self.__sets = {
            **get_sets(os.path.dirname(v[VOCAB_PATH])), **common_sets}
        self.__rd = Random(ses[SES_VOCABS].index(v))
        self.keys = self.__rd.sample([*self.__sets], len(self.__sets))

        # Remove references to outdated sets (gallery info comes from disk)
        self.__gallery = v[VOCAB_GALLERY] = [*({*v[VOCAB_GALLERY]} & {*self.keys})]

        # Order keys so that unlocked are first, then locked
        self.keys = sorted(self.keys, key=lambda x: x not in self.__gallery)

    @property
    def rd(self):
        'A random device seeded by vocabulary index'
        return self.__rd

    def unlocked(self, item: Optional[str] = None):
        if item is None:
            return self.__gallery
        self.__gallery.append(item)

    def reset_progress(self) -> bool:
        'Clears gallery, moves words to the first bucket. Calls update_vocab.'
        if sg.popup_ok_cancel(CFG_CONFIRM_RESET.format(self.__v[VOCAB_NAME]), title=CFG_APPNAME) != 'OK':
            return False
        self.keys.extend(self.__gallery)
        self.__gallery.clear()
        for l in self.__v[VOCAB_WORDS]:
            l *= 0
        update_vocab(self.__v)
        return True

    def __getitem__(self, key_: int) -> Set:
        key = self.keys[key_]
        return [f'{key}{v}' for v in self.__sets[key]]

    def __len__(self) -> int:
        'Returns the amount of sets in total (locked+unlocked)'
        return self.__sets.__len__()


def get_vocabulary(event: Optional[int] = None) -> Tuple[dict, SetProvider]:
    'Presents vocabulary selection screen and returns chosen vocab + its sets'

    if event is not None:
        v = ses[SES_VOCABS][event]
        return v, SetProvider(v)

    # First row: info + guide, second-to-fourth rows: vocabulary slots (3 per row)
    guidesz = (cfg['select-info-guide-width'], cfg['select-info-guide-height'])
    layout = [[sg.Image(key='-INFO-GUIDE-', background_color=cfg['color-select-info-guide'], size=guidesz, pad=((0, 10), (0, 10))),
               sg.T(CFG_SELECT_INFO, pad=(0, (0, 10)), auto_size_text=True, key='-INFO-')]] +\
        [[sg.B(key=j, pad=(10, 10), image_data=get_icon(j), button_color=(
            None, cfg['color-background'])) for j in range(i*3, i*3+3)] for i in range(3)]

    win_loc = ses[SES_WIN_POS]
    win = sg.Window(CFG_APPNAME, layout, finalize=True, location=win_loc,
                    margins=(40, 40), font=cfg['font'])

    # Bind mouse enter, leave, and right-click events to each vocabulary slot
    for i in range(9):
        v = ses[SES_VOCABS][i]
        if VOCAB_PATH in v and os.path.getmtime(v[VOCAB_PATH]) > v[VOCAB_DATE]:
            update_vocab(v)
        win[i].bind('<Enter>', '+ENTER+')
        win[i].bind('<Leave>', '+LEAVE+')
        win[i].bind('<Button-3>', '+RCLICK+')

    # Window event loop
    while True:
        while True:
            event, values = win.read(timeout=500)
            if event is None:
                win.close()
                del win
                return None, None
            ses[SES_WIN_POS] = list(win.CurrentLocation())
            if event != sg.TIMEOUT_EVENT:
                break

        if type(event) == int:
            v = ses[SES_VOCABS][event]
            if VOCAB_ICON_ON in v:
                if all(not x for x in v[VOCAB_WORDS][:-1]):
                    remove_vocab(event, win)
                    continue
                win.close()
                del win
                return v, SetProvider(v)

            path = sg.PopupGetFile('', ses[SES_LAST_DIR] or '', file_types=cfg['vocab-file-types'],
                                   no_window=True, initial_folder=ses[SES_LAST_DIR])
            if path:
                ses[SES_LAST_DIR] = os.path.dirname(path)
                v[VOCAB_PATH] = path
                update_vocab(v)
                win[event].update(image_data=get_icon(event, False))
        elif type(event) == tuple:
            vidx, ev = event
            if ev == '+RCLICK+':
                remove_vocab(vidx, win)
            elif ev == '+ENTER+':
                win[vidx](image_data=get_icon(vidx, True))
            elif ev == '+LEAVE+':
                win[vidx](image_data=get_icon(vidx, False))
