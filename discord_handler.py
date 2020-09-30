from typing import List

from canvas_handler import CanvasHandler


class DiscordHandler:
    """Class for Discord bot to maintain list of active CanvasHandlers

    Attributes
    ----------
    canvas_handlers : `List[CanvasHandlers]`
        List for CanvasHandler for guilds
    """
    def __init__(self):
        self._canvas_handlers = []   # [c_handler1, ... ]

    @property
    def canvas_handlers(self) -> List[CanvasHandler]:
        return self._canvas_handlers
