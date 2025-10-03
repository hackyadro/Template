from dash import Dash
import pandas as pd

from layout import Layout
from callbacks import register_callbacks


class NavigatorApp(Dash):
    def __init__(self, **obsolete):
        super().__init__(**obsolete)
        self.name = "Навигатор"
        self.layout = Layout()
        self.beacons = pd.read_csv('../standart.beacons', sep=';')
        register_callbacks(self)

    def run_app(self, debug=True):
        self.run(debug=debug)


if __name__ == '__main__':
    app = NavigatorApp()
    app.run(debug=False)
