from random import random, randrange

from .config import cfg
from .vocab_pick import calc_progress


class WordIterator:
    def __init__(self, words: list):
        self.__words = words
        self.__add_after_iter = None

    def __iter__(self):
        return self

    def add_word(self, index: int, value):
        self.__add_after_iter = (index, value)

    def __next__(self):
        ws = self.__words
        if not any(ws[:-1]):
            i, res = self.__add_after_iter
            self.__add_after_iter = None
            if i < len(self.__words):
                return i == 1, i, res
            raise StopIteration

        # Get non-empty buckets, position new word bucket at nwi
        nwi = cfg['new-words-index']
        ws = [l for l in ws[1:nwi+1] + [ws[0]] + ws[nwi+1:] if l]

        # Pick a random word, favor lower indices
        l = ws[int(random() ** cfg['critical-word-weight'] * len(ws))]
        img_idx = randrange(len(l))
        i = next(i for i, l_ in enumerate(self.__words) if l_ is l)

        if self.__add_after_iter:
            index, value = self.__add_after_iter
            self.__add_after_iter = None
            self.__words[min(len(self.__words)-1, index)].append(value)

        # Calculate progress before popping the word
        return i == 0, i, calc_progress(self.__words), l.pop(img_idx)
