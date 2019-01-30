import sc2
from sc2 import run_game, maps, Race, Difficulty
from sc2.player import Bot, Computer
from sc2.constants import *



mapname = "(2)LostandFoundLE"

class BlackBot(sc2.BotAI):
    def select_target(self):
        target = self.known_enemy_structures
        if target.exists:
            return target.random.position

        target = self.known_enemy_units
        if target.exists:
            return target.random.position

        if min([u.position.distance_to(self.enemy_start_locations[0]) for u in self.units]) < 5:
            return self.enemy_start_locations[0].position

        return self.state.mineral_field.random.position

    async def on_step(self, iteration):
        cc = (self.units(COMMANDCENTER) | self.units(ORBITALCOMMAND))
        if not cc.exists:
            target = self.known_enemy_structures.random_or(self.enemy_start_locations[0]).position
            for unit in self.workers | self.units((MARINE)):
                await self.do(unit.attack(target))
            return
        else:
            cc = cc.first
#    async def expand(self):
#        if self.units(cc).amount < min(14, 0.6*self.getMinitues()) and self.can_afford(cc):
#            await self.expand_now()
#        def getMinitues (self):
#            return self.iteration / self.ITERATIONS_PER_MINUTE

        
        if iteration % 50 == 0 and self.units(SCV).amount > 21:
            if  self.can_afford(COMMANDCENTER):
                await self.expand_now()
                await self.distribute_workers()
            
        if iteration % 50 == 0 and self.units(MARINE).amount > 2:
            target = self.select_target()
            forces = self.units(MARINE)
            if (iteration//50) % 10 == 0:
                for unit in forces:
                    await self.do(unit.attack(target))
            else:
                for unit in forces.idle:
                    await self.do(unit.attack(target))

        if self.can_afford(SCV) and self.workers.amount < 22 and cc.noqueue:
            await self.do(cc.train(SCV))


        # if self.units(BARRACKS).exists and self.can_afford(MARINE):
        #     for br in self.units(BARRACKS):
        #         if br.noqueue:
        #             if not self.can_afford(MARINE):
        #                 break
        #             await self.do(br.train(MARINE))
                    #  if sp.add_on_tag == 0:
#        if self.units(BARRACKS).exists and self.can_afford(MARINE):
#            for br in self.units(BARRACKS):
#                if br.has_add_on and br.noqueue:
#                    if not self.can_afford(MARINE):
#                        break
#                    await self.do(br.train(MARINE))
                    
#                    
#         if self.units(BARRACKSREACTOR).exists and self.can_afford(MARINE):
#            for br in self.units(BARRACKSREACTOR):
#                if br.has_add_on and br.noqueue:
#                    if not self.can_afford(MARINE):

        elif self.supply_left < 3:
            if self.can_afford(SUPPLYDEPOT):
                await self.build(SUPPLYDEPOT, near=cc.position.towards(self.game_info.map_center, 2)) 

        if self.units(SUPPLYDEPOT).exists:
            if not self.units(BARRACKS).exists :
                if self.can_afford(BARRACKS):
                    await self.build(BARRACKS, near=cc.position.towards(self.game_info.map_center, 8))
                    
        if self.units(BARRACKS).ready.exists:
#                if self.can_afford(BARRACKS) and not self.already_pending(BARRACKS) and len(self.units (BARRACKS)) < 8:
                if self.can_afford(BARRACKS) and len(self.units (BARRACKS)) < 4:
                    await self.build(BARRACKS, near=cc.position.towards(self.game_info.map_center, 100).random_on_distance(8))
      
        if self.units(BARRACKS).ready.exists:
                if self.can_afford(ENGINEERINGBAY) and not self.already_pending(ENGINEERINGBAY) and len(self.units (ENGINEERINGBAY))== 0:
                    await self.build(ENGINEERINGBAY, near=cc.position.towards(self.game_info.map_center, 100).random_on_distance(8))
        
#        if self.units(BARRACKS).ready.exists:
#                if self.can_afford(ENGINEERINGBAY) and len(self.units (ENGINEERINGBAY)) > 2: 
#                    await self.build(ENGINEERINGBAY, near=cc.position.towards(self.game_info.map_center, 100).random_on_distance(8))
        
#        if self.units(ENGINEERINGBAY).ready.exists:
#                    abilities = await self.get_available_abilities(units)
#                    if ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL1 in abilities and \
#                       self.can_afford(ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL1):
#                       await self.do(lab(ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL1))
#      
    
#                if br.noqueue:
#        if self.units(ENGINEERINGBAY).ready.exists and \
#             self.can_afford(RESEARCH_TERRANINFANTRYARMORSLEVEL1):
#                await self.do(lab(ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORSLEVEL1))
        if self.units(ENGINEERINGBAY).ready.exists:
            building = self.units(ENGINEERINGBAY).ready.first
            abilities = await self.get_available_abilities(building)
            if AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL1 in abilities:
                if self.can_afford(ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL1) and building.noqueue:
                    await self.do(building(ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL1))
                    
                
        if self.units(ENGINEERINGBAY).ready.exists:
            building = self.units(ENGINEERINGBAY).ready.first
            abilities = await self.get_available_abilities(building)
            if AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL1 in abilities:
                if self.can_afford(ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL1) and building.noqueue:
                    await self.do(building(ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL1))
                
             

        elif self.units(BARRACKS).exists and self.units(REFINERY).amount < 2:
                if self.can_afford(REFINERY):
                    vgs = self.state.vespene_geyser.closer_than(20.0, cc)
                    for vg in vgs:
                        if self.units(REFINERY).closer_than(1.0, vg).exists:
                            break

                        worker = self.select_build_worker(vg.position)
                        if worker is None:
                            break

                        await self.do(worker.build(REFINERY, vg))
                        break

#            if self.units(SUPPLYDEPOT).ready.exists:
#                b = self.units (BARRACKS)
#                if self.can_afford(BARRACKS):
#                        await self.build(BARRACKS, near=cc.position.towards(self.game_info.map_center, 8))
#                elif b.ready.exists and self.units(BARRACKS).amount < 3:
#                    if self.can_afford(BARRACKS) and self.units(BARRACKS).amount < 3:
#                        await self.build(BARRACKS, near=cc.position.towards(self.game_info.map_center, 30).random_on_distance(8))

#        for sp in self.units(STARPORT).ready:
#            if sp.add_on_tag == 0:
#                await self.do(sp.build(STARPORTTECHLAB))
#                
        for br in self.units(BARRACKS).ready:
            if br.noqueue:
                # await self.chat_send("has_add_on {0}".format(br.has_add_on))
                if br.add_on_tag == 0:
                    await self.do(br.build(BARRACKSREACTOR))
                else:
                    # await self.chat_send("Inside add_on_tag == 1")
                    await self.do(br.train(MARINE))
                    await self.do(br.train(MARINE))
                
        if self.units(STARPORT).ready.exists:
            if self.can_afford(FUSIONCORE) and not self.units(FUSIONCORE).exists:
                await self.build(FUSIONCORE, near=cc.position.towards(self.game_info.map_center, 8))

        for a in self.units(REFINERY):
            if a.assigned_harvesters < a.ideal_harvesters:
                w = self.workers.closer_than(20, a)
                if w.exists:
                    await self.do(w.random.gather(a))

        for scv in self.units(SCV).idle:
            await self.do(scv.gather(self.state.mineral_field.closest_to(cc)))
            
#    async def research(self):
#            for csc in self.units(ENGINEERINGBAY).ready:
#                if self.minerals >= 100 and self.vespene >= 100 and not self.TIW_started:
#                    await self.do(csc(ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORSLEVEL1))
#                    self.TIW_started = True

#
#         

run_game(maps.get(mapname), [
    Bot(Race.Terran, BlackBot()),
    Computer(Race.Random, Difficulty.VeryHard)
], realtime=False)
