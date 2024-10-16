from apeiron.globals.general import *
from abc import ABC, abstractmethod


class Object(ABC):
    def __init__(self, name='Object', obj=None):
        self.name = name
        self.obj = obj  # Blender object
        self.intro = None
        self.outro = None

    @abstractmethod
    def set_intro(self, intro: Interval):
        self.intro = intro
