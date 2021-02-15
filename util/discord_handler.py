from typing import List

from util.canvas_handler import CanvasHandler
from util.piazza_handler import PiazzaHandler


class DiscordHandler:
    """
    Class for Discord bot to maintain list of active handlers

    Attributes
    ----------
    canvas_handlers : `List[CanvasHandlers]`
        List for CanvasHandler for guilds
    piazza_handler : `PiazzaHandler`
        PiazzaHandler for guild.
    """

    def __init__(self):
        self._canvas_handlers = []  # [c_handler1, ... ]
        self._piazza_handler = None

    @property
    def canvas_handlers(self) -> List[CanvasHandler]:
        return self._canvas_handlers

    @canvas_handlers.setter
    def canvas_handlers(self, handlers: List[CanvasHandler]):
        self._canvas_handlers = handlers

    @property
    def piazza_handler(self) -> PiazzaHandler:
        return self._piazza_handler

    @piazza_handler.setter
    def piazza_handler(self, piazza: PiazzaHandler) -> None:
        self._piazza_handler = piazza
