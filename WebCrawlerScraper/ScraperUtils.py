from enum import Enum


class PhrasesMode(Enum):
    AND = 1,
    OR = 2


class Link:
    def __init__(self, link="", base="", depth=0):
        self.link = link
        self.base = base
        self.depth = depth

    def get(self):
        return [self.link, self.base, self.depth]
