import json
import sc2
from sc2 import run_game, maps, Race, Difficulty
from sc2.player import Bot, Computer
from sc2.constants import *
from bot import MyBot
mapname = "(2)LostandFoundLE"

class BlackBot(sc2.AI):
    def __init__(self):
        self.ITERATIONS_PER_MINUTE = 165
        self.MAX_WORKERS = 50
        # Remember seen enemy units and previous state of friendly units
        self.remember_enemy_units()
        self.remember_friendly_units()
    async def on_step(self, iteration):# what to do every step
         self.iteration = iteration   
         await self.distribute_workers()  # in sc2/bot_ai.py
         await self.build_workers()  # workers bc obviously
         await self.build_pylons()  # pylons are protoss supply buildings
         await self.expand()   # expand to a new resource area.
         await self.build_assimilator()  # getting gas
         await self.offensive_force_buildings()
         await self.build_offensive_force()
         await self.build_defense()
         await self.attack()
    async def build_workers(self):
        # nexus = command center
       if (len(self.units(NEXUS)) * 16) > len(self.units(PROBE)) and len(self.units(PROBE)) < self.MAX_WORKERS:
        for nexus in self.units(NEXUS).ready.noqueue:
            if self.can_afford(PROBE):
                await self.do(nexus.train(PROBE))


    run_game(maps.get(mapname), [
    Bot(Race.Terran, MyBot()),
    Computer(Race.Terran, Difficulty.VeryHard)
], realtime=False)
