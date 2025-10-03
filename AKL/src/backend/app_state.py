from enum import Enum
from datetime import datetime, timedelta

max_board_turn_on_delta = timedelta(seconds=10)


class AppStates(Enum):
    WRITE_WAY = 0
    WAITING = 1


class GlobalState():
    _self = None
    _is_init = False

    _last_board_updated = datetime.strptime("1990:01:01", r"%Y:%m:%d")

    def __new__(cls):
        if cls._self == None:
            cls._self = super().__new__(cls)
        return cls._self

    def __init__(self):
        if not self._is_init:
            self._cur_state = AppStates.WAITING

    def get_state(self) -> AppStates:
        return self._cur_state

    def set_state(self, state: AppStates):
        self._cur_state = state

    def save_last_updated(self):
        self._last_board_updated = datetime.now()

    def last_updated_delta(self):
        return datetime.now() - self._last_board_updated
    
    def is_board_turn_on(self):
        return self.last_updated_delta() < max_board_turn_on_delta
