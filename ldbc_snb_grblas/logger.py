from ldbc_snb_grblas.timer import Timer


class Logger:
    def __init__(self):
        self.timer = Timer()

    def _print(self, message):
        time = self.timer.get_delta()
        print(f"{message};{time}")

    def loading_finished(self):
        self._print("LOADED")

    def calculation_finished(self):
        self._print("CALCULATED")

    def print_finished(self):
        self._print("PRINTED")

    def get_total_time(self):
        self.timer.get_total_time()
