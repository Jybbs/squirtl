from pyboy       import PyBoy
from pyboy.utils import WindowEvent
import time

class Emulator:
    def __init__(self, rom_path):

        self.pyboy   = PyBoy(rom_path, window = "SDL2")
        self.actions = {
            'UP'     : (WindowEvent.PRESS_ARROW_UP,      WindowEvent.RELEASE_ARROW_UP),
            'DOWN'   : (WindowEvent.PRESS_ARROW_DOWN,    WindowEvent.RELEASE_ARROW_DOWN),
            'LEFT'   : (WindowEvent.PRESS_ARROW_LEFT,    WindowEvent.RELEASE_ARROW_LEFT),
            'RIGHT'  : (WindowEvent.PRESS_ARROW_RIGHT,   WindowEvent.RELEASE_ARROW_RIGHT),
            'A'      : (WindowEvent.PRESS_BUTTON_A,      WindowEvent.RELEASE_BUTTON_A),
            'B'      : (WindowEvent.PRESS_BUTTON_B,      WindowEvent.RELEASE_BUTTON_B),
            'START'  : (WindowEvent.PRESS_BUTTON_START,  WindowEvent.RELEASE_BUTTON_START),
            'SELECT' : (WindowEvent.PRESS_BUTTON_SELECT, WindowEvent.RELEASE_BUTTON_SELECT),
        }

    def step(self):
        self.pyboy.tick()

    def press_button(self, button):
        press_event, release_event = self.actions[button]
        self.pyboy.send_input(press_event)
        self.step()
        self.pyboy.send_input(release_event)
        self.step()

    def main_loop(self):
        try:
            while True:
                self.step()
                time.sleep(0.01)  # Adjust the sleep time as necessary
        except KeyboardInterrupt:
            self.close()

    def close(self):
        self.pyboy.stop()
