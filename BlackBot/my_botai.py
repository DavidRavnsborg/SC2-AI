from sc2 import Attribute, BotAI
from sc2.constants import *
from sc2.units import Units
from sc2.unit import Unit
from sc2.position import Point2, Point3
from pprint import pprint
from typing import Union


class MyBotAI(BotAI):
    debug = False
    prev_msg = ""
    actions = []
    iteration = 0
    prev_units = {}
    enemy_prev_units = {}  # previously seen but not now
    enemy_new_units = {}
    units_harm = []
    units_damage = []
    units_dps = 0
    units_hps = 0
    minerals_history = []
    vespene_history = []
    minerals_pf = 0
    vespene_pf = 0
    gas_priotity = False

    cached_main_ramp_top = None
    cached_pending = {}
    cached_minerals = None
    cached_enemies = None
    cached_enemy_race = None
    map_corners = []

    RESOURCE_SPREAD_THRESHOLD = 8
    HIT_HISTORY_LOOPS = 56  # 2.5 sec
    RESOURCE_HISTORY_LOOPS = 224  # 10 sec
    UNITS_HISTORY_LOOPS = 1000  # 45 sec

    async def do(self, action):
        self.actions.append(action)
        cost = self._game_data.calculate_ability_cost(action.ability)
        self.minerals -= cost.minerals
        self.vespene -= cost.vespene

    def check_resources(self):
        def process_resource(history, value):
            # save new data
            if not history:
                history.extend([self.state.game_loop, value, 0])
            else:
                delta = value - history[-2]
                if delta > 0:
                    history.extend([self.state.game_loop, value, delta])
                else:
                    history.extend([self.state.game_loop, value, 0])
            # erase old data
            if history and history[0] < self.state.game_loop - self.RESOURCE_HISTORY_LOOPS:
                del history[0:3]
            return sum(history[2::3]) / self.RESOURCE_HISTORY_LOOPS

        # average resource gathered per frame
        self.minerals_pf = process_resource(self.minerals_history, self.minerals)
        self.vespene_pf = process_resource(self.vespene_history, self.vespene)

    def frames_before_can_afford(self, typeid: UnitTypeId) -> Union[int, float]:
        unit = self._game_data.units[typeid.value]
        cost = self._game_data.calculate_ability_cost(unit.creation_ability)
        minerals = cost.minerals - self.minerals
        vespene = cost.vespene - self.vespene
        if minerals <= 0 and vespene <= 0:
            return 0

        if self.minerals_pf == 0:
            if minerals > 0:
                minerals_frames = 2000000000  # never
            else:
                minerals_frames = 0  # now
        else:
            minerals_frames = minerals / self.minerals_pf
        if self.vespene_pf == 0:
            if vespene > 0:
                vespene_frames = 2000000000
            else:
                vespene_frames = 0
        else:
            vespene_frames = vespene / self.vespene_pf
        return max(minerals_frames, vespene_frames)

    async def frames_to_target(self, unit: Unit, target: Point2) -> Union[int, float]:
        distance = await self._client.query_pathing(unit.position, target)
        if not distance:
            return 0
        return distance / unit.movement_speed * 15

    async def check_prev_units(self):
        # fields is_hit and hps are available via self.units
        new_units = {}
        for unit in self.state.units:  # all visible units
            unit.is_hit = False
            unit.hps = 0
            if unit.tag in self.prev_units:
                prev_unit = self.prev_units[unit.tag]
                if hasattr(prev_unit, 'hits'):
                    unit.hits = prev_unit.hits
                else:
                    unit.hits = []

                health_delta = unit.health - prev_unit.health + unit.shield - prev_unit.shield
                if health_delta < 0:
                    unit.is_hit = True
                    unit.hits.extend([self.state.game_loop, health_delta])
                    if unit.is_mine:
                        self.units_harm.extend([self.state.game_loop, health_delta])
                    else:
                        self.units_damage.extend([self.state.game_loop, health_delta])

                if unit.hits and unit.hits[0] < self.state.game_loop - self.HIT_HISTORY_LOOPS:
                    del unit.hits[0:2]  # remove old info about being hit
                unit.hps = -sum(unit.hits[1::2]) * 22.4 / self.HIT_HISTORY_LOOPS  # harm per second

                # cancel attacked buildings
                if unit.is_mine and unit.is_structure and not unit.is_ready and \
                        unit.health + unit.shield < unit.hps * 2:
                    await self.do(unit(AbilityId.CANCEL))
            new_units[unit.tag] = unit
        self.prev_units = new_units  # this way we forget dead

        while self.units_harm and self.units_harm[0] < self.state.game_loop - self.HIT_HISTORY_LOOPS:
            del self.units_harm[0:2]
        while self.units_damage and self.units_damage[0] < self.state.game_loop - self.HIT_HISTORY_LOOPS:
            del self.units_damage[0:2]
        self.units_hps = -sum(self.units_harm[1::2]) * 22.4 / self.HIT_HISTORY_LOOPS  # harm for all my units per second
        self.units_dps = -sum(self.units_damage[1::2]) * 22.4 / self.HIT_HISTORY_LOOPS  # total damage done per second

    def is_explored(self, pos: Union[Point2, Point3, Unit]) -> bool:
        """ Returns True if you have explored on a grid point. """
        assert isinstance(pos, (Point2, Point3, Unit))
        pos = pos.position.to2.rounded
        return self.state.visibility[pos] != 0

    def check_enemy_prev_units(self):
        for k, v in self.enemy_new_units.items():
            self.enemy_prev_units[k] = v
        self.enemy_new_units = {}
        for unit in self.cached_enemies.not_structure:
            self.enemy_new_units[unit.tag] = unit
            self.enemy_new_units[unit.tag].last_seen = self.state.game_loop
            if unit.tag in self.enemy_prev_units:  # dict contains only units not visible now
                del self.enemy_prev_units[unit.tag]
        # remove too old information
        for tag in list(self.enemy_prev_units.keys()):
            if self.enemy_prev_units[tag].last_seen < self.state.game_loop - self.UNITS_HISTORY_LOOPS or \
                    self.is_visible(self.enemy_prev_units[tag]):
                del self.enemy_prev_units[tag]

    async def debug_enemy_prev_units(self):
        for tag, unit in self.enemy_prev_units.items():
            self._client.debug_sphere_out(unit.position3d, unit.radius, Point3((255, 0, 0)))
        await self._client.send_debug()

    async def workers_init(self):
        for worker in self.workers:
            if worker.is_gathering:
                closest_mineral_patch = self.cached_minerals.closest_to(worker)
                await self.do(worker.gather(closest_mineral_patch))

    async def handle_workers(self, nexuses):
        def take_closest_to(target):
            return worker_pool.pop(self.workers.tags_in(list(worker_pool.keys())).closest_to(target).tag)

        async def fill_minerals():
            for nexus in nexuses:
                if nexus.surplus_harvesters < 0:
                    for x in range(0, -nexus.surplus_harvesters):
                        if worker_pool:
                            worker = take_closest_to(nexus)
                            mf = self.cached_minerals.closest_to(nexus)
                            await self.do(worker.gather(mf))

        async def fill_vespene():
            for geyser in self.geysers:
                if geyser.surplus_harvesters < 0:
                    for x in range(0, -geyser.surplus_harvesters):
                        if worker_pool:
                            worker = take_closest_to(geyser)
                            await self.do(worker.gather(geyser))

        if self.iteration == 0:
            await self.workers_init()

        worker_pool = {}  # this way we always add unique workers
        for worker in self.workers.idle:
            worker_pool[worker.tag] = worker
        for nexus in nexuses:
            surplus = nexus.surplus_harvesters
            if surplus > 0:
                workers = self.workers.closer_than(self.RESOURCE_SPREAD_THRESHOLD, nexus)
                for worker in workers:
                    if not worker.orders or (worker.is_gathering and
                                             self.cached_minerals.find_by_tag(worker.orders[0].target)):
                        worker_pool[worker.tag] = worker
                        surplus -= 1
                        if surplus == 0:
                            break
            elif surplus == 0:
                # balance minerals gathering
                workers = self.workers.closer_than(self.RESOURCE_SPREAD_THRESHOLD, nexus)
                workers_targets = {}
                for worker in workers:
                    if worker.is_gathering and self.cached_minerals.find_by_tag(worker.orders[0].target):
                        if worker.orders[0].target in workers_targets:
                            workers_targets[worker.orders[0].target].append(worker.tag)
                        else:
                            workers_targets[worker.orders[0].target] = [worker.tag]
                disbalanced_workers = []
                for mineral, workers in workers_targets.items():
                    if len(workers) > 2:
                        disbalanced_workers.append(self.workers.tags_in(workers)
                                                   .furthest_to(self.cached_minerals.find_by_tag(mineral)))
                if disbalanced_workers:
                    for mineral, workers in workers_targets.items():
                        if len(workers) < 2:
                            worker = disbalanced_workers.pop()
                            await self.do(worker.gather(self.cached_minerals.find_by_tag(mineral)))
                            if not disbalanced_workers:
                                break

        for geyser in self.geysers:
            surplus = geyser.surplus_harvesters
            if surplus > 0:
                workers = self.workers.closer_than(5, geyser)
                for worker in workers:
                    if not worker.orders or (worker.is_gathering and worker.orders[0].target == geyser.tag):
                        worker_pool[worker.tag] = worker
                        surplus -= 1
                        if surplus == 0:
                            break

        if not worker_pool:
            return

        if self.minerals > self.vespene or (self.gas_priotity and self.minerals + 400 > self.vespene):
            await fill_vespene()
            await fill_minerals()
        else:
            await fill_minerals()
            await fill_vespene()

    def can_feed(self, unit_type: UnitTypeId) -> bool:
        """ Checks if you have enough free supply to build the unit """
        return self.supply_left >= self._game_data.units[unit_type.value]._proto.food_required

    async def has_ability(self, ability, unit, ignore_resource_requirements=True) -> bool:
        abilities = await self.get_available_abilities(unit, ignore_resource_requirements=ignore_resource_requirements)
        return ability in abilities

    async def step(self):
        raise NotImplementedError

    async def double_build_bug_remove(self):
        for building in self.units.structure.filter(lambda b: len(b.orders) > 1):
            if self.state.game_loop % 2 == 0:
                await self.do(building(AbilityId.CANCEL_LAST))

#    async def gg_check(self) -> bool:
#        if self.units.structure.amount == 1:
#            last_building = self.units.structure.first
#            if last_building.health + last_building.shield < last_building.hps * 2:
#                await self.chat_send("(gg)")
#                await self._client.leave()
#                return True
#        return False

    async def cache_once_per_game(self):
        self.cached_main_ramp_top = self.main_base_ramp.top_center
        self.cached_enemy_race = self.enemy_race  # todo: race detection for random
        x, y, w, h = self._game_info.playable_area
        self.map_corners = [Point2((x, y)), Point2((x, y + h)), Point2((x + w, y + h)), Point2((x + w, y))]

    async def cache_every_frame(self):
        self.cached_pending = {}
        for unit in self.units:
            for order in unit.orders:
                if order.ability in self.cached_pending:
                    self.cached_pending[order.ability] += 1
                else:
                    self.cached_pending[order.ability] = 1
        self.cached_minerals = self.state.mineral_field
        self.cached_enemies = self.known_enemy_units

    def cached_already_pending(self, unit_type: UnitTypeId):
        ability = self._game_data.units[unit_type.value].creation_ability
        amount = self.units(unit_type).not_ready.amount
        if ability in self.cached_pending:
            amount += self.cached_pending[ability]
        return amount

    async def on_step(self, iteration):
        self.actions = []
        self.iteration = iteration
        if iteration == 0:
            await self.cache_once_per_game()
            self._client.game_step = 3
        await self.cache_every_frame()

        self.check_resources()
        await self.check_prev_units()
        self.check_enemy_prev_units()
        # await self.debug_enemy_prev_units()
#        if await self.gg_check():
#            return
        # await self.double_build_bug_remove()

        await self.step()

        if self.actions:
            await self._client.actions(self.actions, game_data=self._game_data)  # todo: check on success?

    def dbg(self, msg):
        if self.debug and self.prev_msg != msg.__str__():
            print(self.state.game_loop.__str__() + ": " + msg.__str__())
            self.prev_msg = msg.__str__()
