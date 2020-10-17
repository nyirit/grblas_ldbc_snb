from time import perf_counter


class Timer:
    def __init__(self):
        """Initializes the timer."""
        self._last_check = self._time_start = perf_counter()

    def get_total_time(self):
        """Returns the total time since creation (in seconds)"""
        return perf_counter() - self._time_start

    def get_delta(self):
        """Returns time since last access (in seconds) and stores current access time"""
        now = perf_counter()

        result = now - self._last_check
        self._last_check = now

        return result
