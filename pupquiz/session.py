import gc
import os
import re
import threading
import webbrowser
from tempfile import TemporaryDirectory

from gtts import gTTS
from playsound import playsound

from .canvas import CANVAS_SZ, Canvas
from .config import *
from .vocab_pick import (SES_WIN_POS, VOCAB_CONFIG, VOCAB_NAME, VOCAB_WORDS,
                         SetProvider, get_vocabulary, save_session, ses, sg, update_vocab)
from .word_iterator import WordIterator


FORM_WIDTH = 28

class TTSJob(threading.Thread):
    def __init__(self, word: str):
        threading.Thread.__init__(self)
        self.__w = word
    def run(self):
        with TemporaryDirectory() as d:
            path = os.path.join(d, 'tts.mp3')
            try:
                gTTS(self.__w, lang=cfg['spoken-lang']).save(path)
                playsound(path)
            except BaseException:
                pass


class Quiz:
    def __init__(self, v: dict, sets: SetProvider):
        self.__v = v
        self.__sets = sets
        self.__words = v[VOCAB_WORDS]

    def run(self):
        # Create command card layout
        def buts(*args):
            return [sg.B(text, bind_return_key=key == '-OK-', key=key,
                         pad=((0, 7), (10, 0))) for text, key in args]

        if tow := cfg['type-out-words']:
            cc_layout = [[sg.T(CFG_GREET, key='-RES-', size=(FORM_WIDTH, None))], [sg.T(key='-TXT-', pad=(0, (30, 10)), size=(FORM_WIDTH, None))]
                         ] + [[sg.In(key=0, focus=True, size=(FORM_WIDTH, 100))]] + [buts(('', '-OK-'), (CFG_TRANSLATE, '-TRANSL-'), (CFG_RESET, '-RESET-'), (CFG_MENU, '-MENU-'))]
        else:
            # TODO: fix
            cc_layout = [[sg.T(CFG_GREET, key='-RES-', size=(FORM_WIDTH, None))], [sg.T(key='-TXT-', pad=(0, (30, 10)), size=(FORM_WIDTH, None))]
                         ] + [[sg.In(key=0, readonly=True, size=(FORM_WIDTH, 100))]] + [buts(('', '-OK-'), (CFG_TRANSLATE, '-TRANSL-'), (CFG_RESET, '-RESET-'), (CFG_MENU, '-MENU-'))]

        # Full layout including image tiles
        layout = [[sg.Image(size=CANVAS_SZ, key='-IM1-'), sg.Column([[sg.Image(size=(0, 0), key='-IM2-')], [sg.Col(cc_layout, key='-CCARD-', pad=(10, 10), size=(300, 200))], [
            sg.Image(size=(0, 0), key='-IM3-')]])]]

        # Create window
        win = sg.Window(CFG_APPNAME_SES.format(self.__v[VOCAB_NAME]), layout, location=ses[SES_WIN_POS],
                        finalize=True, font=cfg['font'], border_depth=0, margins=(0, 0), element_padding=(0, 0))
        win.hide()
        hidden = True
        canvas = Canvas(win)

        it = WordIterator(self.__words)
        for new, bucket, progress, word in it:
            win['-OK-'].update(CFG_NEWWORD if new else CFG_GUESS)

            # Set image
            set_, img = self.__sets.get_image(progress)
            canvas.set_image(set_, img)

            # Speak new words
            if new and cfg['spoken-lang']:
                if m := re.search(cfg['patt-word-spoken-part'], word[0]):
                    TTSJob(m[0]).start()

            # Reset controls
            win['-TRANSL-'].update(disabled=len(word) != 2)
            win['-TXT-'].update(word[-1])
            col, bgcol = (cfg['color-text'], cfg['color-background']) if new else (
                cfg['color-input-text'], cfg['color-input-background'])
            for i in range(1):
                win[i].update(word[i] if new else '',
                              text_color=col, background_color=bgcol, select=not new)
            win[0].set_focus()

            # Unhide window, if hidden
            frame_time = min(1000, canvas.update())
            if hidden:
                win.un_hide()
                win.TKroot.focus_force()
                hidden = False

            # Retrieve input
            while True:
                event, values = win.read(timeout=frame_time)
                if event != sg.TIMEOUT_KEY:
                    if event == '-RESET-':
                        if not self.__sets.reset_progress():
                            continue
                    break
                ses[SES_WIN_POS] = list(win.CurrentLocation())
                frame_time = min(1000, canvas.update())
            if event in (None, '-MENU-'):
                self.__words[bucket].append(word)
                break

            # 'Translate' button
            elif event == '-TRANSL-':
                self.__words[bucket].append(word)
                win['-RES-'].update(CFG_TRANSLATE_OPENED,
                                    text_color=cfg['color-info-translation-opened'])
                webbrowser.open(cfg['translate-url'].format(word[0]))

            elif event == '-OK-':

                # 'Got it!' button
                if new:
                    it.add_word(1, word)
                    win['-RES-'].update(CFG_ADDWORD,
                                        text_color=cfg['color-info-new-word'])

                # 'Submit' button
                else:
                    # Compare answer with solution
                    guess = list(values.values())
                    if all(map(lambda x: x[0] in [
                           y.strip() for y in x[1].split(',')], zip(guess, word[:-1]))):
                        it.add_word(bucket + 1, word)
                        win['-RES-'].update(CFG_CORRECT,
                                            text_color=cfg['color-info-correct'])
                    else:
                        it.add_word(1, word)
                        win['-RES-'].update(CFG_INCORRECT.format(
                            ', '.join(word[:-1])), text_color=cfg['color-info-incorrect'])

        # Submit progress to disk and quit
        win.close()
        layout = None
        cc_layout = None
        win = None
        gc.collect()
        update_vocab(self.__v)
        return isinstance(event, str) and event == '-MENU-'


def main_loop():
    while True:
        v, provider = get_vocabulary()
        if not v:
            break

        # Support overriding config on a per-vocab basis
        vconfig = {**v[VOCAB_CONFIG]}
        for k in vconfig:
            original = cfg[k]
            cfg[k] = vconfig[k]
            vconfig[k] = original

        if not Quiz(v, provider).run():
            break

        # Restore common config
        cfg.update(vconfig)

    save_session()
