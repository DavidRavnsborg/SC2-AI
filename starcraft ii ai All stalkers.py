import sc2
from sc2 import run_game, maps, Race, Difficulty
from sc2.player import Bot, Computer
from sc2.constants import *
mapname = "(2)LostandFoundLE"
#mapname = input ()

class SentdeBot(sc2.BotAI):
    def __init__(self):
        self.ITERATIONS_PER_MINUTE = 165
        self.MAX_WORKERS = 50

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
                
    async def build_pylons(self):
        if self.supply_left < 6 and not self.already_pending(PYLON):
            nexuses = self.units(NEXUS).ready
            if nexuses.exists:
                if self.can_afford(PYLON):
                    await self.build(PYLON, near=nexuses.first)
   
    async def expand(self):
        if self.units(NEXUS).amount < min(8, 0.5*self.getMinitues()) and self.can_afford(NEXUS):
            await self.expand_now()
            
    async def build_assimilator(self):
        for nexus in self.units(NEXUS).ready:
            vaspenes = self.state.vespene_geyser.closer_than(9.0, nexus)
            for vaspene in vaspenes:
                if not self.can_afford(ASSIMILATOR):
                    break
                worker = self.select_build_worker(vaspene.position)
                if worker is None:
                    break
                if not self.units(ASSIMILATOR).closer_than(1.0, vaspene).exists:
                    await self.do(worker.build(ASSIMILATOR, vaspene))
   
    async def offensive_force_buildings(self):
        if self.units(PYLON).ready.exists:
            pylon = self.units(PYLON).ready.random

            if self.units(GATEWAY).ready.exists and not self.units(CYBERNETICSCORE):
                if self.can_afford(CYBERNETICSCORE) and not self.already_pending(CYBERNETICSCORE):
                    await self.build(CYBERNETICSCORE, near=pylon)

            elif len(self.units(GATEWAY)) < (self.getMinitues()/10):
                if self.can_afford(GATEWAY) and not self.already_pending(GATEWAY):
                    await self.build(GATEWAY, near=pylon)
                    
            if self.units(FLEETBEACON).ready.exists:
                if self.can_afford(FORGE) and len(self.units(FORGE)) == 0:
                    await self.build(FORGE, near=pylon)

            if self.units(STARGATE).ready.exists:
                    if self.can_afford(FLEETBEACON) and not self.already_pending(FLEETBEACON) and len(self.units (FLEETBEACON))== 0:
                        await self.build(FLEETBEACON, near=pylon)
                        
            if self.units(CYBERNETICSCORE).ready.exists:
                if self.can_afford(STARGATE) and not self.already_pending(STARGATE)and len(self.units (NEXUS))  +0:
                        await self.build(STARGATE, near=pylon)
#
#            if self.units(CYBERNETICSCORE).ready.exists:
##                if len(self.units(STARGATE)) < (self.getMinitues()/3):
##                    if self.can_afford(STARGATE) and not self.already_pending(STARGATE):
##                        await self.build(STARGATE, near=pylon)
##             
#                
                if self.can_afford(TWILIGHTCOUNCIL) and not self.already_pending(TWILIGHTCOUNCIL)and len(self.units (TWILIGHTCOUNCIL))== 0:
                    await self.build(TWILIGHTCOUNCIL, near=pylon)
                                
                                
                for lab in self.units(CYBERNETICSCORE).ready:
                    abilities = await self.get_available_abilities(lab)
                    if RESEARCH_WARPGATE in abilities and \
                       self.can_afford(RESEARCH_WARPGATE):
                       await self.do(lab(RESEARCH_WARPGATE))
                          
#                for lab in self.units(FORGE).ready:
                for lab in self.units(CYBERNETICSCORE).ready:
                    abilities = await self.get_available_abilities(lab)
                    if FORGERESEARCH_PROTOSSSHIELDSLEVEL1 in abilities and \
                       self.can_afford(FORGERESEARCH_PROTOSSSHIELDSLEVEL1):
                       await self.do(lab(FORGERESEARCH_PROTOSSSHIELDSLEVEL1)) 
#                if self.units(CYBERNETICSCORE).ready.exists:
#                    building = self.units(CYBERNETICSCORE).ready.first
#                    abilities = await self.get_available_abilities(building)
#                    if WARPGATE in abilities:
#                        if self.can_afford(WARPGATERESEARCH) and building.noqueue:
#                            await self.do(building(WARPGATERESEARCH))
                if self.units(CARRIER).ready.exists:          
                    for lab in self.units(CYBERNETICSCORE).ready.noqueue:
                        abilities = await self.get_available_abilities(lab)
                        for ability in abilities:
                            if self.can_afford(lab(ability)):
                                await self.do(lab(ability))
            
            if self.units(STALKER).ready.exists:
                for lab in self.units(FORGE).ready.noqueue:
                    abilities = await self.get_available_abilities(lab)
                    for ability in abilities:
                        if self.can_afford(lab(ability)):
                            await self.do(lab(ability))
#                
                if self.can_afford(TEMPLARARCHIVE) and not self.already_pending(TEMPLARARCHIVE)and len(self.units (TEMPLARARCHIVE))== 0:
                    await self.build(TEMPLARARCHIVE, near=pylon)
#                
#                if self.units(CYBERNETICSCORE).ready.exists:
#                    if self.can_afford(WARPGATERESEARCH) and not self.already_pending(WARPGATERESEARCH) :
#                        await self.build(WARPGATERESEARCH)
#                        
#                if self.units(TEMPLARARCHIVE).ready.exists:
#                    if self.can_afford(PSISTORMTECH) and not self.already_pending(PSISTORMTECH) :
#                        await self.build(PSISTORMTECH)
#                        
          
               
#                #test for robo facility v#
            elif len(self.units(ROBOTICSFACILITY)) < (self.getMinitues()/5):
                    if self.can_afford(ROBOTICSFACILITY) and not self.already_pending(ROBOTICSFACILITY):
                        await self.build(ROBOTICSFACILITY, near=pylon)
#    #test for robo facility ^
    
    async def build_offensive_force(self):
        for gw in self.units(GATEWAY).ready.noqueue:
            if not self.units(ZEALOT).amount  > self.units(STALKER).amount  > self.units(TEMPEST).amount and not self.units(STALKER).amount  > self.units(IMMORTAL).amount> self.units(CARRIER).amount: 

                if self.can_afford(STALKER) and self.supply_left > 0:
                    await self.do(gw.train(STALKER))
                    
#                if self.can_afford(ADEPT) and self.supply_left > 0:
#                    await self.do(gw.train(ADEPT))
                    
#                if self.can_afford(ZEALOT) and self.supply_left > 0:
#                    await self.do(gw.train(ZEALOT))

        for sg in self.units(STARGATE).ready.noqueue:
            if len(self.units(CARRIER)) < (self.getMinitues()*3.5):
                if self.can_afford(CARRIER) and self.supply_left > 0:
                    await self.do(sg.train(CARRIER))
                
#        for sg in self.units(STARGATE).ready.noqueue:
#            if self.can_afford(TEMPEST) and self.supply_left > 0:
#                await self.do(sg.train(TEMPEST))
        
        
#        for sg in self.units(STARGATE).ready.noqueue:
#            if self.can_afford(VOIDRAY) and self.supply_left > 0:
#                await self.do(sg.train(VOIDRAY))
                
        #IMMORTAL BUILD TEST v
        for rf in self.units(ROBOTICSFACILITY).ready.noqueue:
            if self.can_afford(IMMORTAL) and self.supply_left > 0:
                await self.do(rf.train(IMMORTAL))
    #IMORTAL BUILD TEST ^
    
    async def build_defense(self):
        nexuses = self.units(NEXUS)
        if len(nexuses) >= 3 and self.can_afford(PHOTONCANNON) and len(self.units (PHOTONCANNON)) < 2: 
            await self.build(PHOTONCANNON, near = nexuses.first)
            
#        if len(nexuses) >= 3 and self.can_afford(SHIELDBATTERY) and len(self.units (SHIELDBATTERY)) < 4: 
#            await self.build(SHIELDBATTERY, near = nexuses.first)
            
    async def build_battery(self):
        for nexus in self.units(NEXUS).ready:
            battery = self.state.nexus.Further_than(9.0, nexus)
            for battery in battery:
                if not self.can_afford(SHIELDBATTERY) and len(self.units (SHIELDBATTERY)) < 4:
                 await self.build(SHIELDBATTERY, near = nexuses.first)
    
    def find_target(self, state):
        if len(self.known_enemy_units) > 0:
            return random.choice(self.known_enemy_units)
        elif len(self.known_enemy_structures) > 0:
            return random.choice(self.known_enemy_structures)
        else:
            return self.enemy_start_locations[0]
   
    async def attack(self):
        # {UNIT: [n to fight, n to defend]}
#        aggressive_units = {STALKER: [15, 5],
#                            VOIDRAY: [8, 8],
#                            IMMORTAL: [8, 8],
#                            ZEALOT: [8,3]}
#
#        for UNIT in aggressive_units:
#            if self.units(UNIT).amount > aggressive_units[UNIT][0] and self.units(UNIT).amount > aggressive_units[UNIT][1]:
#                for s in self.units(UNIT).idle:
#                    await self.do(s.attack(self.find_target(self.state)))
#
#            elif self.units(UNIT).amount > aggressive_units[UNIT][1]:
#                if len(self.known_enemy_units) > 0:
#                    for s in self.units(UNIT).idle:
#                        await self.do(s.attack(random.choice(self.known_enemy_units)))
        unit_balance = { "Attack": 35, "Defend": 0}

        fighter_units = self.units.__sub__(self.units(PROBE)).not_structure()

        if fighter_units.amount > unit_balance["Attack"]:
            print("Fighter unit count {0}".format(fighter_units.amount))
            for s in fighter_units:
                await self.do(s.attack(self.find_target(self.state)))

        elif fighter_units.amount > unit_balance["Defend"]:
            if len(self.known_enemy_units) > 0:
                for s in fighter_units:
                    await self.do(s.attack(random.choice(self.known_enemy_units)))
                    
    def getMinitues (self):
        return self.iteration / self.ITERATIONS_PER_MINUTE
        
        
    
    





run_game(maps.get(mapname), [
    Bot(Race.Protoss, SentdeBot()),
    Computer(Race.Terran, Difficulty.VeryHard)
], realtime=False)
    
