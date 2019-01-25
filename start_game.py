from sc2 import run_game, maps, Race, Difficulty
from sc2.player import Bot, Computer
from os import listdir

from bots.SentdeBotDL import SentdeBotDL

MAPS_PATH = "C:\Program Files (x86)\StarCraft II\Maps"
maps_list = listdir(MAPS_PATH)
print("Choose which map you would like to start on:")
for index, map in enumerate(maps_list):
    print("{0}. {1}".format(index, map))
selection = input()
selected_map = maps_list[int(selection)].split('.')[0]
print("Selection was {0}".format(selected_map))

run_game(maps.get(selected_map), [
    Bot(Race.Protoss, SentdeBotDL()),
    Computer(Race.Terran, Difficulty.Easy)
    ], realtime=False)