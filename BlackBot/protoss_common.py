from sc2 import run_game, maps, Race, Difficulty
from sc2.constants import *
from sc2.player import Bot, Computer
from sc2.position import Point2, Point3
from sc2.unit import Unit
from typing import Optional, Union
from my_botai import MyBotAI
from pprint import pprint
import random
import math


class ProtossCommon(MyBotAI):
    max_probes_count = 70
    defence_radius = 20
    scout = None
    forge_upgrades = [AbilityId.FORGERESEARCH_PROTOSSGROUNDWEAPONSLEVEL1,
                      AbilityId.FORGERESEARCH_PROTOSSSHIELDSLEVEL1,
                      AbilityId.FORGERESEARCH_PROTOSSGROUNDARMORLEVEL1,
                      AbilityId.FORGERESEARCH_PROTOSSGROUNDWEAPONSLEVEL2,
                      AbilityId.FORGERESEARCH_PROTOSSSHIELDSLEVEL2,
                      AbilityId.FORGERESEARCH_PROTOSSGROUNDARMORLEVEL2,
                      AbilityId.FORGERESEARCH_PROTOSSGROUNDWEAPONSLEVEL3,
                      AbilityId.FORGERESEARCH_PROTOSSSHIELDSLEVEL3,
                      AbilityId.FORGERESEARCH_PROTOSSGROUNDARMORLEVEL3]
    cybernetic_upgrades = [AbilityId.CYBERNETICSCORERESEARCH_PROTOSSAIRWEAPONSLEVEL1,
                           AbilityId.CYBERNETICSCORERESEARCH_PROTOSSAIRWEAPONSLEVEL2,
                           AbilityId.CYBERNETICSCORERESEARCH_PROTOSSAIRWEAPONSLEVEL3,
                           AbilityId.CYBERNETICSCORERESEARCH_PROTOSSAIRARMORLEVEL1,
                           AbilityId.CYBERNETICSCORERESEARCH_PROTOSSAIRARMORLEVEL2,
                           AbilityId.CYBERNETICSCORERESEARCH_PROTOSSAIRARMORLEVEL3]
    robobay_upgrades = [AbilityId.RESEARCH_EXTENDEDTHERMALLANCE,
                        AbilityId.RESEARCH_GRAVITICBOOSTER]
    unit_to_ability = {UnitTypeId.ZEALOT: AbilityId.WARPGATETRAIN_ZEALOT,
                       UnitTypeId.ADEPT: AbilityId.TRAINWARP_ADEPT,
                       UnitTypeId.SENTRY: AbilityId.WARPGATETRAIN_SENTRY,
                       UnitTypeId.STALKER: AbilityId.WARPGATETRAIN_STALKER}
    unit_producer = {UnitTypeId.ZEALOT: UnitTypeId.GATEWAY,
                     UnitTypeId.ADEPT: UnitTypeId.GATEWAY,
                     UnitTypeId.SENTRY: UnitTypeId.GATEWAY,
                     UnitTypeId.STALKER: UnitTypeId.GATEWAY,
                     UnitTypeId.PHOENIX: UnitTypeId.STARGATE}
    upgrade_researcher = {AbilityId.RESEARCH_WARPGATE: UnitTypeId.CYBERNETICSCORE,
                          AbilityId.RESEARCH_BLINK: UnitTypeId.TWILIGHTCOUNCIL}

    positions_for_pylons = []
    positions_for_buildings = []
    positions_for_batteries = []
    positions_for_cannons = []
    positions_for_nexuses = []
    last_gs_casted = 0

    async def find_position_for_defensive_pylon(self, npos: Point2):
        mins = self.cached_minerals.closer_than(10, npos)
        if mins.empty:
            return
        mc = mins.center
        vec = (mc - npos) / 2
        pos = mc + vec
        ppos = await self.find_placement(UnitTypeId.PYLON, pos, max_distance=2, placement_step=1)
        if ppos is None:
            vec = mc.direction_vector(npos)
            ppos = await self.find_placement(UnitTypeId.PYLON, Point2((mc.x + vec.x, mc.y + vec.y * 5)),
                                             max_distance=1, placement_step=1)
            if ppos is None:
                ppos = await self.find_placement(UnitTypeId.PYLON, Point2((mc.x + vec.x * 5, mc.y + vec.y)),
                                                 max_distance=1, placement_step=1)

        if ppos is None:
            return
        for pos in self.positions_for_pylons:
            if pos.is_same_as(ppos):
                return
        self.positions_for_pylons.insert(max(3, self.units(UnitTypeId.PYLON).amount), ppos)
        # using pylon because if I use cannon, it wouldn't find place because there is no power
        cpos = await self.find_placement(UnitTypeId.PYLON, mc, max_distance=2, placement_step=1)
        if cpos is not None:
            # shift position closer to nexus
            if cpos.manhattan_distance(npos) >= 8:
                cpos += cpos.direction_vector(npos)
            for pos in self.positions_for_cannons:
                if pos.is_same_as(cpos, dist=1.5):
                    return
            self.positions_for_cannons.append(cpos)

    async def debug_buildings_map(self):
        for pos in self.positions_for_pylons:
            self._client.debug_box_out(Point3((pos.x - 0.4, pos.y - 0.4, 9)), Point3((pos.x + 0.4, pos.y + 0.4, 12.2)))
        for pos in self.positions_for_buildings:
            self._client.debug_box_out(Point3((pos.x - 1.4, pos.y - 1.4, 9)), Point3((pos.x + 1.4, pos.y + 1.4, 12.2)))
        for pos in self.positions_for_batteries + self.positions_for_cannons:
            self._client.debug_box_out(Point3((pos.x - 0.9, pos.y - 0.9, 9)),
                                       Point3((pos.x + 0.9, pos.y + 0.9, 12.2)))
        for pos in self.positions_for_nexuses:
            self._client.debug_box_out(Point3((pos.x - 2.4, pos.y - 2.4, 9)),
                                       Point3((pos.x + 2.4, pos.y + 2.4, 12.2)))
        await self._client.send_debug()

    def is_less_than(self, unit: UnitTypeId, count) -> bool:
        if unit is UnitTypeId.GATEWAY:  # todo: better?
            return self.units(UnitTypeId.GATEWAY).ready.amount + \
                   self.units(UnitTypeId.WARPGATE).ready.amount + \
                   self.cached_already_pending(UnitTypeId.GATEWAY) + \
                   self.cached_already_pending(UnitTypeId.WARPGATE) < count
        return self.units(unit).ready.amount + self.cached_already_pending(unit) < count

    def can_train(self, unit: UnitTypeId, qty_needed: int) -> bool:
        return self.is_less_than(unit, qty_needed) and self.can_afford(unit) and self.can_feed(unit)

    def factory_can_train(self, unit: UnitTypeId, factory: Unit, qty_needed: int, check_queue=True) -> bool:
        return self.can_train(unit, qty_needed) and (not check_queue or factory.noqueue)

    async def train_if_can(self, unit: UnitTypeId, factory: Unit, qty_needed: int, check_queue=True) -> bool:
        if self.factory_can_train(unit, factory, qty_needed, check_queue):
            await self.do(factory.train(unit))
            return True
        return False

    async def take_probe(self, target, ignore=None) -> Optional[Unit]:
        if ignore:
            workers = self.workers.tags_not_in(ignore)
        else:
            workers = self.workers
        if self.scout is not None:
            workers = workers.tags_not_in([self.scout])

        workers = workers.filter(lambda worker: worker.is_idle or
                                                (len(worker.orders) == 1 and worker.orders[0].ability.id in [
                                                    AbilityId.MOVE, AbilityId.HARVEST_GATHER,
                                                    AbilityId.HOLDPOSITION])) or self.workers
        if workers.empty:
            return None
        for worker in workers.prefer_close_to(target):
            #dist = await self._client.query_pathing(worker.position, target.position)  # fails with assimilator
            #if dist is not None and dist >= worker.distance_to(target):  # bug? dist != 0 if worker can't reach target
            if random.random() > 0.01: # nothing works =((( todo: find something better
                return worker
        return workers.closest_to(target)

    # todo: check is safe
    async def get_build_position(self, building: UnitTypeId) -> Union[Point2, Unit, None]:
        pos_list = self.positions_for_buildings
        if building is UnitTypeId.PYLON:
            pos_list = self.positions_for_pylons
        elif building is UnitTypeId.SHIELDBATTERY:
            pos_list = self.positions_for_batteries
        elif building is UnitTypeId.PHOTONCANNON:
            pos_list = self.positions_for_cannons
        elif building is UnitTypeId.NEXUS:
            pos_list = self.positions_for_nexuses
        elif building is UnitTypeId.ASSIMILATOR:
            for nexus in self.units(UnitTypeId.NEXUS).sorted(lambda n: n.build_progress):
                pos_list = []
                for gas in self.state.vespene_geyser.closer_than(10, nexus):
                    if await self.can_place(building, gas.position):
                        pos_list.append(gas)

        for pos in pos_list:
            close_enemies = self.cached_enemies.closer_than(10, pos)
            if close_enemies.exists:
                if sum([enemy.ground_dps for enemy in close_enemies]) > 10:
                    continue
            if building is UnitTypeId.ASSIMILATOR or await self.can_place(building, pos):
                return pos
        return None

    async def take_probe_and_build(self, building: UnitTypeId) -> bool:
        pos = await self.get_build_position(building)
        if pos is None:
            return False
        worker = await self.take_probe(pos)
        if worker is None:
            return False
        await self.do(worker.build(building, pos))
        if building is UnitTypeId.ASSIMILATOR:
            await self.do(worker.stop(queue=True))  # or worker will wait until assim will be complete
        if building is UnitTypeId.NEXUS:
            await self.find_position_for_defensive_pylon(pos)
        return True

    async def build_if_can(self, building: UnitTypeId, qty_needed: int) -> bool:
        if self.can_afford(building) and self.is_less_than(building, qty_needed):
            return await self.take_probe_and_build(building)
        return False

    def workers_needed(self) -> int:
        # 1 worker hides in each assimilator
        cnt = -self.workers.amount
        for nexus in self.units(UnitTypeId.NEXUS):
            if nexus.is_ready:
                cnt += nexus.ideal_harvesters
            else:
                cnt += 16
        for assim in self.units(UnitTypeId.ASSIMILATOR):
            if assim.is_ready:
                cnt += assim.ideal_harvesters - 1
            else:
                cnt += 2
        return cnt - 1  # IDK why it always build +1

    async def get_free_warpgate(self) -> Optional[Unit]:
        for wg in self.units(UnitTypeId.WARPGATE).ready:
            if await self.has_ability(AbilityId.WARPGATETRAIN_ZEALOT, wg, ignore_resource_requirements=False):
                return wg
        return None

    async def morph_warpgates(self):
        for gw in self.units(UnitTypeId.GATEWAY).ready.noqueue:
            if await self.has_ability(AbilityId.MORPH_WARPGATE, gw):
                await self.do(gw(AbilityId.MORPH_WARPGATE))

    async def build_using_gateway(self, unit: UnitTypeId) -> Optional[Unit]:  # return producer
        async def warp_in(unit):
            pos = await self.find_placement(self.unit_to_ability[unit],
                                            pylon.position.random_on_distance(1.5),
                                            random_alternative=True, max_distance=5, placement_step=1)
            if pos is not None:
                await self.do(wg.warp_in(unit, pos))
                return True
            return False

        gws = self.units(UnitTypeId.GATEWAY).ready.noqueue
        if gws.exists and await self.train_if_can(unit, gws.first, 100):
            return gws.first

        wg = await self.get_free_warpgate()
        if wg is not None:
            warpers = self.units.of_type([UnitTypeId.WARPGATE, UnitTypeId.NEXUS])
            target = self.enemy_start_locations[0]
            if self.cached_enemies:
                target = self.cached_enemies.closest_to(self.start_location)
            for pylon in self.units(UnitTypeId.PYLON).ready.prefer_close_to(target):
                if warpers.closer_than(5, pylon).exists:  # this pylon is ok for fast warp
                    # random here because find_placement don't check already warping units
                    if await warp_in(unit):
                        return wg
            # try on slow pylons
            for pylon in self.units(UnitTypeId.PYLON).ready.prefer_close_to(self.start_location):
                if await warp_in(unit):
                    return wg
        return None
