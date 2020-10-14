from typing import List

from canvas_handler import CanvasHandler
from piazza_handler import PiazzaHandler


class DiscordHandler:
    """
    Class for Discord bot to maintain list of active CanvasHandlers

    Attributes
    ----------
    canvas_handlers : `List[CanvasHandlers]`
        List for CanvasHandler for guilds
    piazza_handler : `PiazzaHandler`
        PiazzaHandler for guild.
    """

    def __init__(self):
        self._canvas_handlers = []   # [c_handler1, ... ]
        self._piazza_handler = None

    @property
    def canvas_handlers(self) -> List[CanvasHandler]:
        return self._canvas_handlers

    @property
    def piazza_handler(self) -> PiazzaHandler:
        return self._piazza_handler

    @piazza_handler.setter
    def piazza_handler(self, piazza):
        self._piazza_handler = piazza
