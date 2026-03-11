#!/usr/bin/env python3
"""
Storm the House – entry point.

Run with:
    python -m storm_the_house
    python -m storm_the_house.main
"""

from storm_the_house.core.game import Game
from storm_the_house.scenes.main_menu import MainMenuScene


def main():
    """Initialise the game engine and enter the main loop."""
    game = Game()
    game.set_scene(MainMenuScene())
    game.run()


if __name__ == "__main__":
    main()
