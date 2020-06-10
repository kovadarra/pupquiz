import webbrowser
from contextlib import suppress

import PySimpleGUI as sg

from .canvas import CANVAS_SZ, Canvas
from .config import *
from .session import (SES_WIN_POS, VOCAB_NAME, VOCAB_WORDS, Set, SetProvider,
                      calc_progress, get_vocabulary, save_session_json, ses,
                      update_vocab)


def weighted_pick(ls, rd):
    return ls[int(rd.random()**3.5*len(ls))]


def pick_elem(ls, rd):
    l = weighted_pick([l for l in [ls[1], ls[0], *ls[2:]] if l], rd)
    res = l.pop(rd.randrange(len(l)))
    i = next(i for i, v in enumerate(ls) if v is l)
    return i == 0, i, res


FORM_WIDTH = 28


class Quiz:
    def __init__(self, v: dict, sets: SetProvider):
        self.__v = v
        self.__sets = sets

        self.__words = v[VOCAB_WORDS]
        self.__nwords = sum(map(len, self.__words))

        # Step = movement to an adjacent bucket
        self.__nsteps = self.__nwords * (len(self.__words)-1)
        self.__nsets = len(sets)
        self.__steps_per_set = self.__nsteps / self.__nsets

    def __set_idx(self) -> int:
        return int(self.__cur_steps() / self.__steps_per_set)

    def __cur_set(self) -> Set:
        return self.__sets[self.__set_idx()]

    def __cur_img(self) -> str:
        cur_steps = self.__cur_steps()
        cur_set = self.__sets[int(cur_steps / self.__steps_per_set)]
        steps_per_img = self.__steps_per_set / len(cur_set)

        cur_img = int(cur_steps % self.__steps_per_set / steps_per_img)

        return cur_set, cur_img

    def __cur_steps(self):
        return sum(i*len(l) for i, l in enumerate(self.__words))

    def run(self):
        # Create layout; image on the left, quiz form on the right
        def buts(*args):
            return [sg.B(text, bind_return_key=key == '-OK-', key=key, pad=((0, 7), (10, 0))) for text, key in args]
        layout = [[sg.T(CFG_GREET, pad=((20, 0), (cfg['pad-top-status'], 0)), key='-RES-', size=(FORM_WIDTH, None))], [sg.T(key='-TXT-', pad=(0, (30, 10)), size=(FORM_WIDTH, None))]
                  ] + [[sg.In(key=0, focus=True, pad=(0, 0), size=(FORM_WIDTH, 100))]] + [buts(('', '-OK-'), (CFG_TRANSLATE, '-TRANSL-'), (CFG_RESET, '-RESET-'), (CFG_MENU, '-MENU-'))]

        # Create window
        self.__win = sg.Window(CFG_APPNAME_SES.format(self.__v[VOCAB_NAME]), [[sg.Image(size=CANVAS_SZ, background_color=cfg['color-background'], key='-CANVAS-'), sg.Column(
            layout, pad=((10, 0), 0))]], location=ses[SES_WIN_POS], finalize=True, font=cfg['font'], border_depth=0)
        self.__win.TKroot.focus_force()
        canvas = Canvas(self.__win['-CANVAS-'])

        no_advance = True
        while True:
            cur_set, cur_img = self.__cur_img()
            canvas.set_image(cur_set, cur_img, no_advance)
            no_advance = True
            new, l_idx, cur_word = pick_elem(self.__words, self.__sets.rd)
            self.__win['-OK-'].update(CFG_NEWWORD if new else CFG_GUESS)

            # Reset controls
            self.__win['-TRANSL-'].update(disabled=len(cur_word) != 2)
            self.__win['-TXT-'].update(cur_word[-1])
            col, bgcol = (cfg['color-text'], cfg['color-background']) if new else (
                cfg['color-input-text'], cfg['color-input-background'])
            for i in range(1):
                self.__win[i].update(cur_word[i] if new else '',
                                     text_color=col, background_color=bgcol, select=not new)
            self.__win[0].set_focus()

            # Retrieve input
            while True:
                event, values = self.__win.read(10)
                if event != sg.TIMEOUT_KEY:
                    if event == '-RESET-':
                        if not self.__sets.reset_progress():
                            continue
                    break
                ses[SES_WIN_POS] = list(self.__win.CurrentLocation())
                canvas.update()
            if event in (None, '-MENU-'):
                self.__words[l_idx].append(cur_word)
                break

            # 'Translate' button
            elif event == '-TRANSL-':
                self.__words[l_idx].append(cur_word)
                self.__win['-RES-'].update(CFG_TRANSLATE_OPENED,
                                           text_color=cfg['color-info-translation-opened'])
                webbrowser.open(cfg['translate-url'].format(cur_word[0]))

            # 'Got it!'/'Submit' button
            elif event == '-OK-':
                if new:
                    self.__words[1].append(cur_word)
                    self.__win['-RES-'].update(
                        CFG_ADDWORD, text_color=cfg['color-info-new-word'])
                else:
                    # Compare answer with solution
                    guess = list(values.values())
                    if all(map(lambda x: x[0] in [y.strip() for y in x[1].split(',')], zip(guess, cur_word[:-1]))):
                        self.__words[min(len(self.__words)-1,
                                         l_idx+1)].append(cur_word)
                        if all(not x for x in self.__words[:-1]):
                            break
                        self.__win['-RES-'].update(
                            CFG_CORRECT.format(calc_progress(self.__words)*100), text_color=cfg['color-info-correct'])
                        no_advance = False
                    else:
                        self.__words[1].append(cur_word)
                        self.__win['-RES-'].update(CFG_INCORRECT.format(', '.join(cur_word[:-1])),
                                                   text_color=cfg['color-info-incorrect'])

        # Submit progress to disk and quit
        self.__win.close()
        del self.__win
        update_vocab(self.__v)
        return event is '-MENU-'


def main_loop():
    while True:
        v, provider = get_vocabulary()
        if not v or not Quiz(v, provider).run():
            break
    save_session_json()
