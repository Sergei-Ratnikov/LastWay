# main.py
import pygame
from game_engine import GameEngine
from world.location_manager import LocationManager

def main():
    location_manager = LocationManager()
    start_location = location_manager.get_start_location()
    engine = GameEngine(start_location)
    result = engine.run()

if __name__ == "__main__":
    main()