from sc2 import Race, Attribute
from sc2.constants import *
from sc2.player import Bot, Computer
from sc2.position import Point2, Point3
from sc2.unit import Unit
from sc2.units import Units
from protoss_common import ProtossCommon
from typing import Union, Optional
from time import sleep
import random
import math
from pprint import pprint


def grid_to_point2(a: Point2):
    return Point2((a.x + 0.5, a.y - 0.5))


def sign(num):
    if num == 0:
        return 0
    return 1 if num > 0 else -1


def points_in_circum(r, v=Point2((0, 0)), n=12):
    return [Point2((math.cos(2 * math.pi / n * x) * r, math.sin(2 * math.pi / n * x) * r)) + v for x in range(0, n + 1)]


class ProtossBot(ProtossCommon):
    # class variable shared by all instances! todo: rewrite, only constants should be here
    guard_pos = None
    guardian = None
    rush_detected = False
    wroker_rush_detected = False
    raid_detected = False
    worker_rush_defence_radius = 10
    normal_defence_radius = 30
    large_defence_radius = 70
    defence_radius = normal_defence_radius
    builder = None
    scout = None
    army = None
    fleet = None
    fleet_retreat = False
    army_attack_amount = 8
    rush_army_attack_amount = 12
    stop_workers_build = 0
    reserve_minerals = 0
    reserve_vespene = 0
    base_scout_points = []

    main_build_order = [UnitTypeId.NEXUS, UnitTypeId.PYLON, UnitTypeId.GATEWAY, UnitTypeId.ASSIMILATOR,
                        UnitTypeId.NEXUS, UnitTypeId.CYBERNETICSCORE, UnitTypeId.ASSIMILATOR, UnitTypeId.PYLON,
                        UnitTypeId.STALKER, "boost", AbilityId.RESEARCH_WARPGATE, UnitTypeId.SHIELDBATTERY,
                        UnitTypeId.TWILIGHTCOUNCIL, UnitTypeId.STALKER, AbilityId.RESEARCH_BLINK, UnitTypeId.GATEWAY,
                        UnitTypeId.STALKER, UnitTypeId.GATEWAY, UnitTypeId.PYLON, UnitTypeId.STALKER, UnitTypeId.PYLON,
                        UnitTypeId.ASSIMILATOR, UnitTypeId.ROBOTICSFACILITY, UnitTypeId.NEXUS]
    anti_worker_rush_build_order = [UnitTypeId.NEXUS, UnitTypeId.PYLON, UnitTypeId.GATEWAY, UnitTypeId.ZEALOT,
                                    UnitTypeId.GATEWAY, UnitTypeId.PYLON, UnitTypeId.ZEALOT, UnitTypeId.ZEALOT,
                                    UnitTypeId.ZEALOT, UnitTypeId.CYBERNETICSCORE]
    """anti_proxy_build_order = [UnitTypeId.NEXUS, UnitTypeId.PYLON, "scout", UnitTypeId.GATEWAY,
                              UnitTypeId.ASSIMILATOR, UnitTypeId.ASSIMILATOR, UnitTypeId.GATEWAY, UnitTypeId.PYLON,
                              UnitTypeId.CYBERNETICSCORE, AbilityId.RESEARCH_WARPGATE, UnitTypeId.GATEWAY,
                              UnitTypeId.STALKER, "boost", UnitTypeId.STALKER, UnitTypeId.PYLON,
                              UnitTypeId.STALKER, UnitTypeId.STALKER, UnitTypeId.STALKER, UnitTypeId.SHIELDBATTERY,
                              UnitTypeId.STALKER, UnitTypeId.FORGE, UnitTypeId.STALKER, UnitTypeId.STALKER,
                              UnitTypeId.PYLON, UnitTypeId.PHOTONCANNON, UnitTypeId.STALKER, UnitTypeId.STALKER,
                              UnitTypeId.PYLON, UnitTypeId.STALKER, UnitTypeId.STALKER, UnitTypeId.STALKER]"""
    baton_build_order = [UnitTypeId.NEXUS, UnitTypeId.PYLON, UnitTypeId.GATEWAY, UnitTypeId.ASSIMILATOR,
                         UnitTypeId.NEXUS, UnitTypeId.CYBERNETICSCORE, UnitTypeId.ASSIMILATOR, UnitTypeId.FORGE,
                         UnitTypeId.PYLON, UnitTypeId.STALKER, "boost", UnitTypeId.PHOTONCANNON,
                         UnitTypeId.PHOTONCANNON, UnitTypeId.STALKER,
                         "boost", UnitTypeId.PHOTONCANNON, "all", UnitTypeId.PYLON, UnitTypeId.ASSIMILATOR,
                         UnitTypeId.STARGATE, UnitTypeId.STALKER, "boost", UnitTypeId.SHIELDBATTERY, "all",
                         UnitTypeId.GATEWAY, UnitTypeId.PYLON, UnitTypeId.PHOENIX, UnitTypeId.ASSIMILATOR,
                         UnitTypeId.STALKER, "boost", UnitTypeId.PYLON, UnitTypeId.FLEETBEACON]
    """anti_raid_build_order = [UnitTypeId.NEXUS, UnitTypeId.PYLON, "scout", UnitTypeId.GATEWAY, UnitTypeId.ASSIMILATOR,
                             UnitTypeId.FORGE, UnitTypeId.PYLON, UnitTypeId.PHOTONCANNON, UnitTypeId.CYBERNETICSCORE,
                             UnitTypeId.STALKER, "boost", UnitTypeId.PYLON, UnitTypeId.GATEWAY, UnitTypeId.STALKER,
                             "boost", UnitTypeId.STALKER, "boost", UnitTypeId.STALKER, "boost",
                             UnitTypeId.NEXUS, UnitTypeId.PYLON, UnitTypeId.PYLON, UnitTypeId.PYLON, UnitTypeId.STALKER,
                             UnitTypeId.PHOTONCANNON, "all", UnitTypeId.TWILIGHTCOUNCIL]"""
    anti_rush_build_order = [UnitTypeId.NEXUS, UnitTypeId.PYLON, UnitTypeId.GATEWAY, UnitTypeId.ASSIMILATOR,
                             UnitTypeId.FORGE, UnitTypeId.PYLON, UnitTypeId.PHOTONCANNON, UnitTypeId.CYBERNETICSCORE,
                             UnitTypeId.STALKER, "boost", UnitTypeId.PYLON, UnitTypeId.PHOTONCANNON, "all",
                             UnitTypeId.GATEWAY, UnitTypeId.STALKER, "boost", UnitTypeId.SHIELDBATTERY,
                             UnitTypeId.STALKER, "boost", UnitTypeId.SHIELDBATTERY, UnitTypeId.STALKER, "boost",
                             UnitTypeId.SHIELDBATTERY, "all", UnitTypeId.NEXUS, UnitTypeId.PYLON, UnitTypeId.PYLON,
                             UnitTypeId.PYLON, UnitTypeId.STALKER]
    anti_raid_build_order = anti_rush_build_order
    build_order = baton_build_order
    gas_priotity = True

    async def make_buildings_map(self):

        def find_closest_points():
            def find_next_pos(p, cvec, rvec, poses):
                def has_nonbuildable_neighbours(p, min_nbr):
                    if not self.in_placement_grid(p):
                        return False
                    ncount = 0
                    for np in p.neighbors8:
                        if not self.in_placement_grid(np):
                            ncount += 1
                    if min_nbr < ncount < 6:
                        return True
                    return False

                neighbours = [p + Point2((cvec.x, -cvec.y)), p + Point2((cvec.x, 0)), p + cvec, p + Point2((0, cvec.y)),
                              p + Point2((-cvec.x, cvec.y))]
                more_neighbours = [p + Point2((-cvec.x, 0)), p + Point2((0, -cvec.y))]
                if cvec.x == rvec.x:
                    neighbours.reverse()
                    more_neighbours.reverse()
                neighbours.extend(more_neighbours)

                for np in neighbours:
                    if np not in poses and has_nonbuildable_neighbours(np, 1):
                        return np
                for np in neighbours:
                    if np not in poses and has_nonbuildable_neighbours(np, 0):
                        return np
                return None

            wall1 = []
            center_vector = self.main_base_ramp.bottom_center.direction_vector(self.game_info.map_center)
            ramp_vector = self.cached_main_ramp_top.direction_vector(self.main_base_ramp.bottom_center)
            ne_vector = self.main_base_ramp.bottom_center \
                .direction_vector(self.cached_minerals.closest_to(self.main_base_ramp.bottom_center).position)
            if center_vector.distance_to_point2(ramp_vector) != 2:
                search_vector = ne_vector
            else:
                search_vector = ramp_vector
            ptr = self.main_base_ramp.bottom_center.rounded
            while not self.in_placement_grid(ptr):
                ptr += ramp_vector
            closest_ramp = min(
                {ramp for ramp in self.game_info.map_ramps if ramp is not self.main_base_ramp},
                key=(lambda r: ptr.distance_to(r.top_center))
            )
            # find points of right wall
            for x in range(25):
                wall1.append(ptr)
                if ptr.neighbors8.intersection(closest_ramp.points):
                    break  # found ramp
                ptr = find_next_pos(ptr, center_vector, search_vector, wall1)
                if ptr is None:
                    break  # no more points

            # get center of wall points
            ptr = Point2.center(wall1).rounded
            # move to the other wall
            ptr += search_vector * Point2((7, 7))

            # find other wall
            while self.in_placement_grid(ptr):
                ptr += search_vector

            # find points of left wall
            wall2 = []
            search_vector *= Point2((-1, -1))
            for x in range(25):
                wall2.append(ptr)
                if ptr.neighbors8.intersection(closest_ramp.points):
                    break  # found ramp
                ptr = find_next_pos(ptr, center_vector, search_vector, wall2)
                if ptr is None:
                    break  # no more points

            # find 2 closest points
            poses = []
            min_dist = 2000000000
            for a in wall1:
                for b in wall2:
                    new_dist = a._distance_squared(b)
                    if new_dist < min_dist:
                        poses = [a, b]
                        min_dist = new_dist
            return poses

        def natural_wall(poses):
            # add buildings using found points as corners, prefer closer to each other
            wall = []
            for poses in [[poses[0], poses[1]], [poses[1], poses[0]]]:
                vec = poses[0].direction_vector(poses[1])
                for pos in [poses[0] + vec, poses[0] + Point2((-vec.x, vec.y)),
                            poses[0] + Point2((vec.x, -vec.y)), poses[0] + Point2((-vec.x, -vec.y))]:
                    if len([p for p in pos.neighbors8 if not self.in_placement_grid(p)]) == 0:
                        wall.append(pos)
                        break

            if wall[0].distance_to(self.start_location) > wall[1].distance_to(self.start_location):
                close_part = wall[1]
                far_part = wall[0]
            else:
                far_part = wall[1]
                close_part = wall[0]
            if not (4 <= wall[0].manhattan_distance(wall[1]) <= 6):
                # wall is not done, find last building position
                vec = far_part.direction_vector(close_part)
                candidates = []
                if self.in_placement_grid(Point2((far_part.x + vec.x * 3, far_part.y))):
                    pos = Point2((far_part.x + vec.x * 3, far_part.y))
                    # prevent wall closing
                    if wall[0].manhattan_distance(wall[1]) <= 8:
                        pos = Point2((pos.x, pos.y - vec.y))
                    for i in range(3):
                        if 4 <= pos.manhattan_distance(close_part) <= 6:
                            candidates.append(pos)
                            break
                        pos = Point2((pos.x, pos.y + vec.y))
                if self.in_placement_grid(Point2((far_part.x, far_part.y + vec.y * 3))):
                    pos = Point2((far_part.x, far_part.y + vec.y * 3))
                    # prevent wall closing
                    if wall[0].manhattan_distance(wall[1]) <= 8:
                        pos = Point2((pos.x - vec.x, pos.y))
                    for i in range(3):
                        if 4 <= pos.manhattan_distance(close_part) <= 6:
                            candidates.append(pos)
                            break
                        pos = Point2((pos.x + vec.x, pos.y))
                if candidates:
                    best = min(candidates, key=(lambda p: p.distance_to(self.start_location)))
                    wall.append(best)

            if len(wall) >= 2:
                for pos in wall:
                    self.positions_for_buildings.insert(0, grid_to_point2(pos))
                # position for unit guarding the gap between buildings
                self.guard_pos = Point2.center([grid_to_point2(wall[-1]), grid_to_point2(close_part)])
                # find place for pylon
                if len(wall) == 2:
                    poses = wall[0].circle_intersection(wall[1], 5.5)  # pylon radius?
                    best = min(poses, key=(lambda p: p.distance_to(self.start_location)))
                    self.positions_for_pylons.insert(0, best.rounded)
                    vec = close_part.direction_vector(self.game_info.map_center) * Point2((-1, -1))
                    if abs(far_part.x - close_part.x) < abs(far_part.y - close_part.y):
                        self.positions_for_cannons = [close_part + grid_to_point2(Point2((2.5 * vec.x, 0.5 * vec.y)))]
                        self.positions_for_batteries = [far_part + grid_to_point2(Point2((2.5 * vec.x, 0.5 * vec.y)))]
                    else:
                        self.positions_for_cannons = [close_part + grid_to_point2(Point2((0.5 * vec.x, 2.5 * vec.y)))]
                        self.positions_for_batteries = [far_part + grid_to_point2(Point2((0.5 * vec.x, 2.5 * vec.y)))]
                else:  # 3
                    vec = wall[-1].direction_vector(self.game_info.map_center) * Point2((-1, -1))
                    if abs(far_part.x - wall[-1].x) < abs(far_part.y - wall[-1].y):
                        pylon_pos = wall[-1] + grid_to_point2(Point2((1.5 * vec.x, 2.5 * vec.y)))
                        self.positions_for_batteries = [wall[-1] + grid_to_point2(Point2((2.5 * vec.x, 0.5 * vec.y)))]
                        self.positions_for_cannons = [far_part + grid_to_point2(Point2((2.5 * vec.x, 0.5 * vec.y)))]
                    else:
                        pylon_pos = wall[-1] + grid_to_point2(Point2((2.5 * vec.x, 1.5 * vec.y)))
                        self.positions_for_batteries = [wall[-1] + grid_to_point2(Point2((0.5 * vec.x, 2.5 * vec.y)))]
                        self.positions_for_cannons = [far_part + grid_to_point2(Point2((0.5 * vec.x, 2.5 * vec.y)))]
                    self.positions_for_pylons.insert(0, pylon_pos)

        def cannon_wall(poses):
            wall = []
            for poses in [[poses[0], poses[1]], [poses[1], poses[0]]]:
                vec = poses[0].direction_vector(poses[1])
                for pos in [poses[0] + vec, poses[0] + Point2((-vec.x, vec.y)),
                            poses[0] + Point2((vec.x, -vec.y)), poses[0] + Point2((-vec.x, -vec.y))]:
                    if len([p for p in pos.neighbors8 if not self.in_placement_grid(p)]) == 0:
                        wall.append((pos + poses[0]) / 2)
                        break

            wall_center = Point2.center(wall)
            nat_vec = -wall_center.direction_vector(self._game_info.map_center)
            dist = poses[0].manhattan_distance(poses[1])
            for pos in wall.copy():
                center_vec = pos.direction_vector(wall_center)
                if dist < 8:
                    wall.append(pos + center_vec * 2 + Point2((nat_vec.x, -nat_vec.y)))  # todo: fix if more maps
                    break  # add only one
                elif dist < 12:
                    wall.append(pos + center_vec * 1.5 + nat_vec * 0.5)
                else:
                    diff = pos - wall_center
                    if abs(diff.x) < abs(diff.y):
                        wall.append(pos + center_vec * 2 + Point2((sign(diff.x), 0)))
                    else:
                        wall.append(pos + center_vec * 2 + Point2((0, sign(diff.y))))
            dist = wall[-1].manhattan_distance(wall[-2])
            diff = wall[-1] - wall[-2]
            if dist == 3:
                if abs(diff.x) < abs(diff.y):
                    pos = (wall[-1] + wall[-3]) / 2 + nat_vec * Point2((1.5, 0.5))
                    self.positions_for_batteries.extend([grid_to_point2(wall[-1] + Point2((nat_vec.x * 2, 0))),
                                                         grid_to_point2(wall[-2] + Point2((nat_vec.x * 2, 0))),
                                                         grid_to_point2(pos + Point2((nat_vec.x * 2, 0)))])
                    self.positions_for_pylons.insert(2, grid_to_point2(wall[1] + Point2((nat_vec.x * 4, 0))))
                else:
                    pos = (wall[-1] + wall[-3]) / 2 + nat_vec * Point2((0.5, 1.5))
                    self.positions_for_batteries.extend([grid_to_point2(wall[-1] + Point2((0, nat_vec.y * 2))),
                                                         grid_to_point2(wall[-2] + Point2((0, nat_vec.y * 2))),
                                                         grid_to_point2(pos + Point2((0, nat_vec.y * 2)))])
                    self.positions_for_pylons.insert(2, grid_to_point2(wall[1] + Point2((0, nat_vec.y * 4))))
            elif dist == 4:
                if abs(diff.x) == abs(diff.y):
                    pos = (wall[-1] + wall[-2]) / 2 + nat_vec
                    diff = wall[-3] - wall[-4]
                    if abs(diff.x) == abs(diff.y):
                        if nat_vec == Point2((1, -1)):
                            wall = [wall[1], wall[0], wall[3], wall[2]]  # dreamcatcher hack, todo: fix
                        self.positions_for_batteries.extend([grid_to_point2(wall[0] + Point2((nat_vec.x * 2, 0))),
                                                             grid_to_point2(wall[1] + Point2((0, nat_vec.y * 2))),
                                                             grid_to_point2(wall[2] + Point2((nat_vec.x * 2, 0))),
                                                             grid_to_point2(wall[3] + Point2((0, nat_vec.y * 2)))])
                        self.positions_for_pylons.insert(2, grid_to_point2(wall[1] + Point2((0, nat_vec.y * 4))))
                        self.positions_for_pylons.insert(2, grid_to_point2(wall[2] + Point2((nat_vec.x * 4, 0))))
                    elif abs(diff.x) > abs(diff.y):
                        self.positions_for_batteries.extend([grid_to_point2(wall[0] + Point2((0, nat_vec.y * 2))),
                                                             grid_to_point2(wall[1] + Point2((0, nat_vec.y * 2))),
                                                             grid_to_point2(wall[3] + Point2((0, nat_vec.y * 2))),
                                                             grid_to_point2(pos + Point2((0, nat_vec.y * 2)))])
                        self.positions_for_pylons.insert(2, grid_to_point2(wall[0] + Point2((0, nat_vec.y * 4))))
                        self.positions_for_pylons.insert(2, grid_to_point2(wall[3] + Point2((0, nat_vec.y * 4))))
                    else:
                        self.positions_for_batteries.extend([grid_to_point2(wall[0] + Point2((nat_vec.x * 2, 0))),
                                                             grid_to_point2(wall[1] + Point2((nat_vec.x * 2, 0))),
                                                             grid_to_point2(wall[3] + Point2((nat_vec.x * 2, 0))),
                                                             grid_to_point2(pos + Point2((nat_vec.x * 2, 0)))])
                        self.positions_for_pylons.insert(2, grid_to_point2(wall[0] + Point2((nat_vec.x * 4, 0))))
                        self.positions_for_pylons.insert(2, grid_to_point2(wall[3] + Point2((nat_vec.x * 4, 0))))
                elif diff.x == 0 or diff.y == 0:
                    pos = (wall[-1] + wall[-2]) / 2
                    if diff.x == 0:
                        for wpos in wall.copy():
                            self.positions_for_batteries.append(grid_to_point2(wpos + Point2((nat_vec.x * 2, 0))))
                        self.positions_for_pylons.insert(2, grid_to_point2(wall[0] + Point2((nat_vec.x * 4, 0))))
                        self.positions_for_pylons.insert(2, grid_to_point2(wall[3] + Point2((nat_vec.x * 4, 0))))
                    else:
                        for wpos in wall.copy():
                            self.positions_for_batteries.append(grid_to_point2(wpos + Point2((0, nat_vec.y * 2))))
                        self.positions_for_pylons.insert(2, grid_to_point2(wall[0] + Point2((0, nat_vec.y * 4))))
                        self.positions_for_pylons.insert(2, grid_to_point2(wall[3] + Point2((0, nat_vec.y * 4))))
                """else:
                    pos = (wall[-1] + wall[-2]) / 2 + nat_vec * 1.5"""
            elif dist == 5:
                if abs(diff.x) < abs(diff.y):
                    pos = (wall[-1] + wall[-2]) / 2 + nat_vec * Point2((1, 0.5))
                    self.positions_for_batteries.extend([grid_to_point2(wall[0] + Point2((0, nat_vec.y * 2))),
                                                         grid_to_point2(wall[1] + Point2((0, nat_vec.y * 2))),
                                                         grid_to_point2(wall[3] + Point2((0, nat_vec.y * 2))),
                                                         grid_to_point2(pos + Point2((0, nat_vec.y * 2)))])
                    self.positions_for_pylons.insert(2, grid_to_point2(wall[0] + Point2((0, nat_vec.y * 4))))
                    self.positions_for_pylons.insert(2, grid_to_point2(wall[3] + Point2((0, nat_vec.y * 4))))
                else:
                    pos = (wall[-1] + wall[-2]) / 2 + nat_vec * Point2((0.5, 1))
                    self.positions_for_batteries.extend([grid_to_point2(wall[0] + Point2((nat_vec.x * 2, 0))),
                                                         grid_to_point2(wall[1] + Point2((nat_vec.x * 2, 0))),
                                                         grid_to_point2(wall[3] + Point2((nat_vec.x * 2, 0))),
                                                         grid_to_point2(pos + Point2((nat_vec.x * 2, 0)))])
                    self.positions_for_pylons.insert(2, grid_to_point2(wall[0] + Point2((nat_vec.x * 4, 0))))
                    self.positions_for_pylons.insert(2, grid_to_point2(wall[3] + Point2((nat_vec.x * 4, 0))))
            self.positions_for_pylons.insert(1, grid_to_point2(pos))

            for pos in wall:
                self.positions_for_cannons.insert(0, grid_to_point2(pos))

        base_height = self._game_info.terrain_height[self.start_location.rounded]
        max_x = self._game_info.map_size.width
        max_y = self._game_info.map_size.height
        min_pos = self.cached_minerals.closer_than(self.RESOURCE_SPREAD_THRESHOLD, self.start_location).center
        vector = min_pos.direction_vector(self.start_location)
        if vector.x == 0 or vector.y == 0:
            vector = min_pos.direction_vector(self.game_info.map_center)
        p0 = self.start_location + (vector * Point2((5.5, 5.5))).rounded
        p1 = p0 + vector * Point2((4, 6))
        b0 = p0 + vector * Point2((0.5, 2.5))
        b1 = b0 + vector * Point2((0, 3))
        b2 = p0 + vector * Point2((4.5, 0.5))
        b3 = b2 + vector * Point2((0, 3))
        for y in range(-3, 3):
            for x in range(-3, 3):
                if x < 0 and y < 0:
                    continue
                for pos in [p0 + vector * Point2((x * 8, y * 9)), p1 + vector * Point2((x * 8, y * 9))]:
                    if 0 < pos.x < max_x and 0 < pos.y < max_y and \
                            self._game_info.terrain_height[pos.rounded] == base_height:
                        self.positions_for_pylons.append(pos)
                for pos in [b0 + vector * Point2((x * 8, y * 9)), b1 + vector * Point2((x * 8, y * 9)),
                            b2 + vector * Point2((x * 8, y * 9)), b3 + vector * Point2((x * 8, y * 9))]:
                    if 0 < pos.x < max_x and 0 < pos.y < max_y and \
                            self._game_info.terrain_height[pos.rounded] == base_height:
                        self.positions_for_buildings.append(pos)
        self.positions_for_pylons.sort(key=lambda a: self.start_location.distance_to(a))
        self.positions_for_buildings.sort(key=lambda a: self.start_location.distance_to(a))

        if self.game_info._proto.map_name.replace(" ", "").lower() not in ["automatonle", "stasisle"]:
            poses = find_closest_points()
            # natural_wall(poses)
            cannon_wall(poses)

        # find nexuses positions for expansions
        # todo: better function?
        for pos in sorted(self.expansion_locations.keys(),
                          key=lambda p: p.distance_to(self.main_base_ramp.bottom_center)):
            n = await self.find_placement(UnitTypeId.NEXUS, pos, max_distance=8,
                                          random_alternative=False, placement_step=1)
            if n is not None:
                self.positions_for_nexuses.append(n)

        await self.find_position_for_defensive_pylon(self.start_location)
        """for np in self.positions_for_nexuses:
            await self.find_position_for_defensive_pylon(np)"""
        """for pos in self.expansion_locations.keys():
            self._client.debug_box_out(Point3((pos.x + 0.1, pos.y - 0.9, 0)), Point3((pos.x + 0.9, pos.y - 0.1, 10.2)))
        await self._client.send_debug()"""

    def choose_unit_to_train(self) -> Optional[UnitTypeId]:
        """if not self.units(UnitTypeId.CYBERNETICSCORE).ready and self.can_train(UnitTypeId.ZEALOT, 4):
            return UnitTypeId.ZEALOT
        if self.can_train(UnitTypeId.STALKER, 100):
            return UnitTypeId.STALKER
        if self.can_train(UnitTypeId.SENTRY, 2):
            return UnitTypeId.SENTRY
        # todo: more strats for other races and units they use
        if self.enemy_race in [Race.Terran, Race.Zerg]:  # less zealots, more adepts
            if self.can_train(UnitTypeId.ZEALOT, (self.supply_used / 20).__round__()):
                return UnitTypeId.ZEALOT
            elif self.can_train(UnitTypeId.ADEPT, (self.supply_used / 10).__round__()):
                return UnitTypeId.ADEPT
        #  too much minerals and no gas spend them on zealots
        if self.can_train(UnitTypeId.ZEALOT, (self.supply_used / 10).__round__()) or \
                self.minerals >= 250 and self.vespene < 25 and self.can_train(UnitTypeId.ZEALOT, 50):
            return UnitTypeId.ZEALOT
        return None"""
        """if self.enemy_race is Race.Zerg and self.can_train(UnitTypeId.ADEPT, 1):
            return UnitTypeId.ADEPT"""
        """if self.can_train(UnitTypeId.ADEPT, self.units(UnitTypeId.STALKER).amount + 1) and \
                self.cached_enemies.of_type([UnitTypeId.ZERGLING, UnitTypeId.MARINE,
                                             UnitTypeId.ZEALOT]).amount / 4 > self.units(UnitTypeId.ADEPT).amount:
            return UnitTypeId.ADEPT"""
        """if self.can_train(UnitTypeId.ZEALOT, round(self.units(UnitTypeId.STALKER).amount / 2)):
            return UnitTypeId.ZEALOT"""
        if self.can_train(UnitTypeId.STALKER, 100):
            return UnitTypeId.STALKER
        """if self.vespene >= 400 and self.can_train(UnitTypeId.SENTRY, 100):
            return UnitTypeId.SENTRY"""
        return None

    async def boost(self, building: Unit) -> bool:
        boosters = self.units(UnitTypeId.NEXUS).ready
        if boosters:
            for booster in boosters.sorted(lambda b: b.energy, reverse=True):
                if await self.has_ability(AbilityId.EFFECT_CHRONOBOOSTENERGYCOST, booster) and \
                        booster.energy >= 50 and not building.has_buff(BuffId.CHRONOBOOSTENERGYCOST):
                    await self.do(booster(AbilityId.EFFECT_CHRONOBOOSTENERGYCOST, building))
                    return True
        return False

    async def strategy(self):
        def check_build_option(order_key) -> Optional[str]:
            if len(self.build_order) > order_key + 1:
                return self.build_order[order_key + 1]
            return None

        nexuses = self.units(UnitTypeId.NEXUS)
        await self.handle_workers(nexuses.ready)

        # Workers
        if nexuses.empty:  # banzai!
            for worker in self.workers:
                await self.do(worker.attack(self.enemy_start_locations[0]))
            return
        nexus = nexuses.ready.prefer_idle.first
        if self.minerals > self.reserve_minerals + 50 and self.workers_needed() > 0 and \
                self.stop_workers_build < self.state.game_loop and \
                await self.train_if_can(UnitTypeId.PROBE, nexus, self.max_probes_count):
            self.dbg("Building worker")
            return  # Here and after: no more actions if one done

        # Chronoboost
        boosters = self.units(UnitTypeId.NEXUS).ready
        if boosters:
            for booster in boosters.sorted(lambda b: b.energy, reverse=True):
                if await self.has_ability(AbilityId.EFFECT_CHRONOBOOSTENERGYCOST, booster):
                    if booster.energy >= 50:
                        for building in self.units.of_type([UnitTypeId.CYBERNETICSCORE, UnitTypeId.FORGE,
                                                            UnitTypeId.TWILIGHTCOUNCIL, UnitTypeId.ROBOTICSBAY]).ready:
                            if not building.noqueue and not building.has_buff(BuffId.CHRONOBOOSTENERGYCOST):
                                time = self._game_data.abilities[building.orders[0].ability.id.value].cost.time
                                if not time:  # can't get time for ability
                                    time = 136 * 22.4  # average time for upgrades which abilities has no time
                                if (1 - building.orders[0].progress) * time / 22.4 < 25:
                                    continue  # skip if less than 25 seconds left
                                await self.do(booster(AbilityId.EFFECT_CHRONOBOOSTENERGYCOST, building))
                                self.dbg("Boost on " + str(building))
                                return
                    if booster.energy >= 150:
                        for gate in self.units(UnitTypeId.STARGATE).ready:
                            if gate.orders:
                                time = self._game_data.abilities[gate.orders[0].ability.id.value].cost.time
                                if (1 - gate.orders[0].progress) * time / 22.4 < 25:
                                    continue  # skip if less than 25 seconds left
                                await self.do(booster(AbilityId.EFFECT_CHRONOBOOSTENERGYCOST, gate))
                                self.dbg("Boost on " + str(gate))
                                return

        await self.morph_warpgates()

        # select build order
        if self.wroker_rush_detected and self.build_order != self.anti_worker_rush_build_order:
            self.build_order = self.anti_worker_rush_build_order
            self.dbg("Switched to anti_worker_rush_build_order")
        elif self.raid_detected and self.build_order != self.anti_raid_build_order:
            self.build_order = self.anti_raid_build_order
            for building in self.units(UnitTypeId.NEXUS).not_ready:
                await self.do(building(AbilityId.CANCEL))
            self.dbg("Switched to anti_raid_build_order")
        elif self.rush_detected and self.build_order != self.anti_rush_build_order:
            self.build_order = self.anti_rush_build_order
            for building in self.units(UnitTypeId.NEXUS).not_ready:
                await self.do(building(AbilityId.CANCEL))
            self.dbg("Switched to anti_rush_build_order")
        elif self.units(UnitTypeId.STALKER).amount >= 5 and (self.build_order == self.anti_raid_build_order or
                                                             self.build_order == self.anti_rush_build_order):
            self.build_order = self.baton_build_order
            self.dbg("Switched to baton_build_order")
        elif self.build_order not in [self.baton_build_order, self.main_build_order, self.anti_raid_build_order,
                                      self.anti_rush_build_order] and not self.wroker_rush_detected:
            self.positions_for_cannons = []
            self.positions_for_batteries = []
            self.build_order = self.main_build_order
            self.dbg("Switched to main_build_order")
        """elif self.rush_detected and self.build_order != self.anti_proxy_build_order:
            self.build_order = self.anti_proxy_build_order
            self.dbg("Switched to anti_proxy_build_order")
        elif self.build_order != self.main_build_order:
            self.build_order = self.main_build_order
            self.dbg("Switched to main_build_order")"""

        should_exist = {}
        for order_key, action in enumerate(self.build_order):
            if isinstance(action, str):
                continue

            if self.minerals < self.reserve_minerals or self.vespene < self.reserve_vespene:
                return  # don't build anything if worker already moving to build position

            if isinstance(action, AbilityId):
                researchers = self.units(self.upgrade_researcher[action]).ready
                if researchers.exists and await self.has_ability(action, researchers.first):
                    if self.can_afford(action):
                        await self.do(researchers.first(action))
                        self.dbg("Researching " + str(action))
                    if not self.rush_detected:  # todo: other reasons to skip?
                        self.dbg("Waiting for resources for " + str(action))
                        return

            if isinstance(action, UnitTypeId):
                if action is UnitTypeId.STALKER:  # hack. todo: better
                    action = self.choose_unit_to_train()
                    if action is None:
                        action = UnitTypeId.STALKER

                if action.value not in should_exist:
                    should_exist[action.value] = 0
                build_option = check_build_option(order_key)
                if build_option == "all":
                    if action is UnitTypeId.SHIELDBATTERY:
                        should_exist[action.value] = len(self.positions_for_batteries) - 1
                    elif action is UnitTypeId.PHOTONCANNON:
                        should_exist[action.value] = len(self.positions_for_cannons) - 1

                if self.is_less_than(action, should_exist[action.value] + 1):
                    # is structure
                    if Attribute.Structure.value in self._game_data.units[action.value].attributes:
                        """if self.builder is not None:
                            builder = self.units.find_by_tag(self.builder)
                            creation_ability = self._game_data.units[action.value].creation_ability
                            if len(builder.orders) and builder.orders[0] is creation_ability:
                                self.dbg(action)
                                return  # wait until builder will start previous order"""

                        # build it or take worker and move him to build position if resources will be enough soon
                        ok = await self.build_if_can(action, should_exist[action.value] + 1)
                        if ok:
                            # check options after build
                            build_option = check_build_option(order_key)
                            if build_option == "scout" and self.scout is None:
                                self.scout = (await self.take_probe(self.enemy_start_locations[0])).tag
                            if self.builder is not None and build_option is not None:
                                builder = self.units.find_by_tag(self.builder)
                                if builder:
                                    if build_option == "wait":
                                        await self.do(builder.hold_position(queue=True))
                                    """elif build_option == "scout":
                                        self.scout = builder.tag
                                        pos = self.positions_for_pylons[0]  # todo: fix this hack?
                                        builder = self.take_probe(self.start_location, ignore=[self.scout])
                                        await self.do(builder.move(pos))
                                        await self.do(builder.hold_position(queue=True))"""
                                    if build_option == "swb":
                                        self.dbg("Stop workers build")
                                        self.stop_workers_build = self.state.game_loop + 336  # 15 sec
                                    else:
                                        self.stop_workers_build = 0
                            self.builder = None
                            self.reserve_minerals = 0
                            self.reserve_vespene = 0

                        if not ok and self.builder is None:
                            pos = await self.get_build_position(action)
                            if pos is not None:
                                worker = await self.take_probe(pos)
                                if worker is not None and isinstance(pos, Point2):  # not gas for assim
                                    frames = await self.frames_to_target(worker, pos)
                                    if frames >= self.frames_before_can_afford(action):
                                        self.builder = worker.tag
                                        unit = self._game_data.units[action.value]
                                        cost = self._game_data.calculate_ability_cost(unit.creation_ability)
                                        self.reserve_minerals = cost.minerals
                                        self.reserve_vespene = cost.vespene
                                        await self.do(worker.move(pos))
                        # can skip build if ex. no positions. But this is hack. Todo: better
                        if action not in [UnitTypeId.SHIELDBATTERY, UnitTypeId.PHOTONCANNON]:
                            self.dbg("Waiting resources for " + str(action))
                            return
                    else:  # not a structure
                        req_building = self._game_data.units[action.value].tech_requirement
                        if self.units(req_building).ready.exists:
                            if self.unit_producer[action] is UnitTypeId.GATEWAY:
                                gate = await self.build_using_gateway(action)
                                if gate is not None and len(self.build_order) > order_key + 1 and \
                                        self.build_order[order_key + 1] == "boost":
                                    await self.boost(gate)
                            elif self.unit_producer[action] is UnitTypeId.STARGATE:
                                gate = self.units(UnitTypeId.STARGATE).ready.noqueue
                                if gate.exists:
                                    await self.train_if_can(action, gate.first, 100)
                                    if len(self.build_order) > order_key + 1 and \
                                            self.build_order[order_key + 1] == "boost":
                                        await self.boost(gate.first)
                            self.dbg("Building or waiting resources for " + str(action))
                            return
                should_exist[action.value] += 1

        # If buildorder is done, use common strategy
        if self.build_order in [self.baton_build_order, self.anti_raid_build_order, self.anti_rush_build_order]:
            # Buildings
            if self.supply_cap < 200 and self.supply_left < 16 and self.cached_already_pending(UnitTypeId.PYLON) < 2 \
                    and await self.build_if_can(UnitTypeId.PYLON, 20):
                self.dbg("Building " + str(UnitTypeId.PYLON))
                return
            if (self.units(UnitTypeId.STARGATE).noqueue.empty or self.units(UnitTypeId.FLEETBEACON).exists) and \
                    self.minerals >= 400 and self.vespene >= 300 and await self.build_if_can(UnitTypeId.STARGATE, 4):
                self.dbg("Building " + str(UnitTypeId.STARGATE))
                return

            # Upgrades
            if self.build_order != self.anti_raid_build_order:
                if self.units(UnitTypeId.CARRIER).exists:
                    cc = self.units(UnitTypeId.CYBERNETICSCORE).ready.noqueue
                    if cc.exists:
                        for ability in self.cybernetic_upgrades:
                            if await self.has_ability(ability, cc.first):
                                if self.can_afford(ability):
                                    await self.do(cc.first(ability))
                                self.dbg("Waiting resources for " + str(ability))
                                return
                    fb = self.units(UnitTypeId.FLEETBEACON).ready.noqueue
                    if fb.exists and await self.has_ability(AbilityId.RESEARCH_INTERCEPTORGRAVITONCATAPULT, fb.first):
                        if self.can_afford(AbilityId.RESEARCH_INTERCEPTORGRAVITONCATAPULT):
                            await self.do(fb.first(AbilityId.RESEARCH_INTERCEPTORGRAVITONCATAPULT))
                        self.dbg("Waiting resources for " + str(AbilityId.RESEARCH_INTERCEPTORGRAVITONCATAPULT))
                        return

            # Expand on new maps
            if self.game_info._proto.map_name.replace(" ", "").lower() not in \
                    ["acidplantle", "blueshiftle", "ceruleanfallle", "dreamcatcherle",
                     "fracturele", "lostandfoundle", "parasitele", "kairosjunctionle"]:
                if not self.cached_already_pending(UnitTypeId.NEXUS) and \
                        (self.workers_needed() <= 0 and self.is_less_than(UnitTypeId.NEXUS, self.supply_used / 20)) or \
                        (self.units(UnitTypeId.NEXUS).amount >= 5 and self.workers_needed() < 0):
                    await self.build_if_can(UnitTypeId.NEXUS, 10)
                    self.dbg("Building " + str(UnitTypeId.NEXUS))
                    if self.minerals < 400:
                        return  # because sometimes there is no place for nexus

                if self.vespene < 400 and await self.build_if_can(UnitTypeId.ASSIMILATOR, nexuses.ready.amount * 2):
                    self.dbg("Building " + str(UnitTypeId.ASSIMILATOR))
                    return

            # Units
            stargates = self.units(UnitTypeId.STARGATE).ready.noqueue
            if stargates.exists:
                stargate = stargates.first
                if self.can_train(UnitTypeId.CARRIER, 20):
                    await self.train_if_can(UnitTypeId.CARRIER, stargate, 20)
                return  # gather resources
        else:
            # Upgrades
            if not self.rush_detected:
                cc = self.units(UnitTypeId.CYBERNETICSCORE).ready.noqueue
                if cc.exists and await self.has_ability(AbilityId.RESEARCH_WARPGATE, cc.first):
                    if self.can_afford(AbilityId.RESEARCH_WARPGATE):
                        self.dbg("Researching " + str(AbilityId.RESEARCH_WARPGATE))
                        await self.do(cc.first(AbilityId.RESEARCH_WARPGATE))
                    self.dbg("Waiting resources for " + str(AbilityId.RESEARCH_WARPGATE))
                    return

                forge = self.units(UnitTypeId.FORGE).ready.noqueue
                if forge.exists and self.units(UnitTypeId.TWILIGHTCOUNCIL).exists:
                    for ability in self.forge_upgrades:
                        if await self.has_ability(ability, forge.first):
                            if self.can_afford(ability):
                                self.dbg("Researching " + str(ability))
                                await self.do(forge.first(ability))
                            self.dbg("Waiting resources for " + str(ability))
                            return

                robobay = self.units(UnitTypeId.ROBOTICSBAY).ready.noqueue
                if robobay.exists:
                    for ability in self.robobay_upgrades:
                        if await self.has_ability(ability, robobay.first):
                            if self.can_afford(ability):
                                self.dbg("Researching " + str(ability))
                                await self.do(robobay.first(ability))
                            self.dbg("Waiting resources for " + str(ability))
                            return

                tc = self.units(UnitTypeId.TWILIGHTCOUNCIL).ready.noqueue
                if tc.exists:
                    if await self.has_ability(AbilityId.RESEARCH_BLINK, tc.first):
                        if self.can_afford(AbilityId.RESEARCH_BLINK):
                            self.dbg("Researching " + str(AbilityId.RESEARCH_BLINK))
                            await self.do(tc.first(AbilityId.RESEARCH_BLINK))
                        self.dbg("Waiting resources for " + str(AbilityId.RESEARCH_BLINK))
                        return
                    if await self.has_ability(AbilityId.RESEARCH_CHARGE, tc.first) and \
                            self.units(UnitTypeId.ZEALOT).amount >= 4:
                        if self.can_afford(AbilityId.RESEARCH_CHARGE):
                            self.dbg("Researching " + str(AbilityId.RESEARCH_CHARGE))
                            await self.do(tc.first(AbilityId.RESEARCH_CHARGE))
                        self.dbg("Waiting resources for " + str(AbilityId.RESEARCH_CHARGE))
                        return
                    if await self.has_ability(AbilityId.RESEARCH_ADEPTRESONATINGGLAIVES, tc.first) and \
                            self.units(UnitTypeId.ADEPT).amount >= 4:
                        if self.can_afford(AbilityId.RESEARCH_ADEPTRESONATINGGLAIVES):
                            self.dbg("Researching " + str(AbilityId.RESEARCH_ADEPTRESONATINGGLAIVES))
                            await self.do(tc.first(AbilityId.RESEARCH_ADEPTRESONATINGGLAIVES))
                        # else: do nothing, wait for resources
                        self.dbg("Waiting resources for " + str(AbilityId.RESEARCH_ADEPTRESONATINGGLAIVES))
                        return

            # Buildings
            if self.supply_left < 3 + self.supply_used / 10 and self.can_afford(UnitTypeId.PYLON) and \
                    self.cached_already_pending(UnitTypeId.PYLON) < self.supply_used / 50 and \
                    self.supply_cap < 200 and await self.take_probe_and_build(UnitTypeId.PYLON):
                self.dbg("Building " + str(UnitTypeId.PYLON))
                return

            if self.vespene < 400 and await self.build_if_can(UnitTypeId.ASSIMILATOR, nexuses.ready.amount * 2):
                self.dbg("Building " + str(UnitTypeId.ASSIMILATOR))
                return

            # self.get_free_warpgate() is None if self.supply_cap == 200?
            if self.units.of_type([UnitTypeId.GATEWAY, UnitTypeId.WARPGATE]).amount < 8 and self.supply_cap < 199:
                if self.already_pending_upgrade(UpgradeId.WARPGATERESEARCH) == 1:
                    condition = self.units(UnitTypeId.WARPGATE).amount >= 2 and await self.get_free_warpgate() is None
                else:
                    condition = self.units(UnitTypeId.GATEWAY).amount >= 2 and self.units(
                        UnitTypeId.GATEWAY).noqueue.empty
                if self.units(UnitTypeId.PYLON).ready.exists and self.cached_already_pending(
                        UnitTypeId.GATEWAY) <= 1 and \
                        condition and self.can_afford(UnitTypeId.GATEWAY) and self.units(
                    UnitTypeId.CYBERNETICSCORE).exists:
                    await self.take_probe_and_build(UnitTypeId.GATEWAY)
                    self.dbg("Building " + str(UnitTypeId.GATEWAY))
                    return

            if not self.is_less_than(UnitTypeId.NEXUS, 2) and self.units(UnitTypeId.CYBERNETICSCORE).ready.exists and \
                    await self.build_if_can(UnitTypeId.FORGE, 1):
                self.dbg("Building " + str(UnitTypeId.FORGE))
                return

            if not self.is_less_than(UnitTypeId.NEXUS, 3) and self.units(UnitTypeId.CYBERNETICSCORE).ready.exists and \
                    await self.build_if_can(UnitTypeId.FORGE, min(round(self.army.not_flying.amount / 8), 2)):
                self.dbg("Building " + str(UnitTypeId.FORGE))
                return

            if not self.is_less_than(UnitTypeId.NEXUS, 3) and self.units(UnitTypeId.CYBERNETICSCORE).ready.exists and \
                    await self.build_if_can(UnitTypeId.ROBOTICSFACILITY, round(self.army.not_flying.amount / 12)):
                self.dbg("Building " + str(UnitTypeId.ROBOTICSFACILITY))
                return

            if not self.is_less_than(UnitTypeId.OBSERVER, 1) and self.units(
                    UnitTypeId.ROBOTICSFACILITY).ready.exists and \
                    await self.build_if_can(UnitTypeId.ROBOTICSBAY, 1):
                self.dbg("Building " + str(UnitTypeId.ROBOTICSBAY))
                return

            # defensive structures
            if self.units(UnitTypeId.CYBERNETICSCORE).ready.exists and \
                    self.is_less_than(UnitTypeId.SHIELDBATTERY, len(self.positions_for_batteries)) and \
                    await self.build_if_can(UnitTypeId.SHIELDBATTERY, len(self.positions_for_batteries)):
                self.dbg("Building " + str(UnitTypeId.SHIELDBATTERY))
                return
            if self.units(UnitTypeId.FORGE).ready.exists and \
                    self.is_less_than(UnitTypeId.PHOTONCANNON, len(self.positions_for_cannons)) and \
                    await self.build_if_can(UnitTypeId.PHOTONCANNON, len(self.positions_for_cannons)):
                self.dbg("Building " + str(UnitTypeId.PHOTONCANNON))
                return

            # expand
            if not self.cached_already_pending(UnitTypeId.NEXUS) and \
                    (self.workers_needed() <= 0 and self.is_less_than(UnitTypeId.NEXUS, self.supply_used / 20)) or \
                    (self.units(UnitTypeId.NEXUS).amount >= 5 and self.workers_needed() < 0):
                await self.build_if_can(UnitTypeId.NEXUS, 10)
                self.dbg("Building " + str(UnitTypeId.NEXUS))
                if self.minerals < 400:
                    return  # because sometimes there is no place for nexus

            # Units
            stargates = self.units(UnitTypeId.STARGATE).ready.noqueue
            if stargates.exists:
                stargate = stargates.first
                oracles_needed = min(self.units(UnitTypeId.STALKER).amount / 4, 8)
                if self.is_less_than(UnitTypeId.ORACLE, oracles_needed) and self.can_feed(UnitTypeId.ORACLE):
                    if self.can_train(UnitTypeId.ORACLE, oracles_needed):
                        await self.train_if_can(UnitTypeId.ORACLE, stargate, oracles_needed)
                    return  # gather resources

            robos = self.units(UnitTypeId.ROBOTICSFACILITY).ready.noqueue
            if robos.exists:
                robo = robos.first
                observers_needed = 1
                if self.units(UnitTypeId.COLOSSUS).exists:
                    observers_needed = 2
                if self.can_train(UnitTypeId.OBSERVER, observers_needed):
                    await self.train_if_can(UnitTypeId.OBSERVER, robo, observers_needed)
                    self.dbg("Building " + str(UnitTypeId.OBSERVER))
                    return
                if self.units(UnitTypeId.ROBOTICSBAY).ready.exists:
                    colossi_needed = max(1, min(self.units(UnitTypeId.IMMORTAL).amount / 2, 4))
                    if self.is_less_than(UnitTypeId.COLOSSUS, colossi_needed) and self.can_feed(UnitTypeId.COLOSSUS):
                        if self.can_train(UnitTypeId.COLOSSUS, colossi_needed):
                            await self.train_if_can(UnitTypeId.COLOSSUS, robo, colossi_needed)
                        self.dbg("Building " + str(UnitTypeId.COLOSSUS))
                        return  # gather resources
                immortals_needed = round(min(self.units.of_type([UnitTypeId.STALKER, UnitTypeId.ADEPT,
                                                                 UnitTypeId.ZEALOT]).amount / 2, 8))
                if self.is_less_than(UnitTypeId.IMMORTAL, immortals_needed) and self.can_feed(UnitTypeId.IMMORTAL):
                    if self.can_train(UnitTypeId.IMMORTAL, immortals_needed):
                        await self.train_if_can(UnitTypeId.IMMORTAL, robo, immortals_needed)
                    self.dbg("Building " + str(UnitTypeId.IMMORTAL))
                    return  # gather resources

            new_unit = self.choose_unit_to_train()
            if new_unit is not None:
                await self.build_using_gateway(new_unit)
                self.dbg("Building " + str(new_unit))

    async def tactics(self):
        async def probe_defence():
            # don't try to destroy gateway with probes. Pylon is enough
            targets = self.cached_enemies.not_flying.exclude_type([UnitTypeId.GATEWAY, UnitTypeId.REAPER]) \
                .closer_than(self.defence_radius, self.start_location)
            if targets.empty or self.workers.empty or self.army.amount >= 2 or \
                    self.units(UnitTypeId.PHOTONCANNON).amount >= 2:
                attacking_workers = self.workers.filter(lambda u: u.is_attacking)
                for aw in attacking_workers:
                    await self.do(aw.stop())
                return False  # no enemies, or no workers act as always

            enemy_dps = 0
            for unit in targets:
                enemy_dps += unit.ground_dps
            worker_dps = self.workers.first.ground_dps

            home_mineral = self.cached_minerals.closest_to(self.start_location)
            army = self.workers.filter(lambda u: u.is_attacking)
            # is_moving - will build
            army |= self.workers.sorted(lambda u: u.shield + u.health +
                                                  u.distance_to(self.start_location) / 10 -
                                                  len(u.orders) * 100, reverse=True) \
                .take(max(0, round(1 + enemy_dps / worker_dps - army.amount + targets.structure.amount * 6)),
                      require_all=False)

            for unit in army:
                if targets.of_type(UnitTypeId.PYLON).exists:
                    # 1/2 probes attack pylon
                    if hash(str(unit.tag)) % 2:
                        target = targets.structure.closest_to(unit)
                    else:
                        target = targets.closest_to(unit)
                else:
                    target = targets.closest_to(unit).position
                enemy_is_far = self.start_location.distance_to(target) > self.defence_radius - 1
                low_health = unit.shield + unit.health <= 20
                if (low_health or enemy_is_far) and unit.is_attacking and unit.distance_to(home_mineral) > 2:
                    if unit.type_id == UnitTypeId.PROBE:
                        await self.do(unit.gather(home_mineral))
                    else:
                        await self.do(unit.move(home_mineral))
                    continue
                if not enemy_is_far and not low_health:
                    await self.do(unit.attack(target))
            return True

        async def detect_rush():
            rush = False
            if self.enemy_race is Race.Zerg and \
                    self.cached_enemies.structure.of_type(UnitTypeId.SPAWNINGPOOL).exists:
                rush = True
            if self.enemy_race is Race.Terran and \
                    (self.cached_enemies.structure.of_type(UnitTypeId.BARRACKS).amount not in [1, 2] or
                     self.cached_enemies.structure.of_type(UnitTypeId.REFINERY).empty):
                rush = True
            if self.enemy_race is Race.Terran and \
                    self.cached_enemies.structure.of_type(UnitTypeId.REFINERY).amount == 2:
                self.raid_detected = True
            if self.enemy_race is Race.Protoss and \
                    self.cached_enemies.structure.of_type(UnitTypeId.GATEWAY).amount >= 2:
                """self.cached_enemies.structure.of_type(UnitTypeId.ASSIMILATOR).empty) and \
               self.cached_enemies.structure.of_type(UnitTypeId.NEXUS).amount == 1:"""
                rush = True
            if rush:
                if not self.wroker_rush_detected:
                    self.rush_detected = True
                    self.army_attack_amount = self.rush_army_attack_amount
                self.defence_radius = self.large_defence_radius

        async def handle_worker_rush():
            if not self.wroker_rush_detected:
                self.wroker_rush_detected = self.cached_enemies \
                                                .of_type([UnitTypeId.SCV, UnitTypeId.DRONE, UnitTypeId.PROBE]) \
                                                .closer_than(self.defence_radius, self.start_location).amount >= 10 and \
                                            self.army.empty
                if self.wroker_rush_detected:
                    self.army_attack_amount = 1
                    self.defence_radius = self.worker_rush_defence_radius
                    # remove distant buildings, this should be only once
                    self.positions_for_buildings = self.positions_for_buildings[3:]
                    self.positions_for_pylons = self.positions_for_pylons[1:]
                    self.rush_detected = False  # this is not proxy then
                    """for building in self.units.structure.not_ready:
                        await self.do(building(AbilityId.CANCEL))"""
            elif self.cached_enemies.of_type([UnitTypeId.SCV, UnitTypeId.DRONE, UnitTypeId.PROBE]) \
                    .closer_than(self.defence_radius * 2, self.start_location).empty and \
                    self.units(UnitTypeId.ZEALOT).amount >= 4:
                self.defence_radius = self.normal_defence_radius
                self.wroker_rush_detected = False

        async def handle_raid():
            self.raid_detected = self.state.game_loop < 4032 and \
                                 self.cached_enemies.of_type([UnitTypeId.REAPER]).amount > 2

        async def handle_rush():
            if self.cached_enemies.structure.exclude_type([UnitTypeId.CREEPTUMOR, UnitTypeId.CREEPTUMORBURROWED,
                                                           UnitTypeId.KD8CHARGE]) \
                    .closer_than(self.large_defence_radius, self.cached_main_ramp_top).exists:
                self.rush_detected = True
                self.army_attack_amount = self.rush_army_attack_amount
                self.defence_radius = self.large_defence_radius

            if self.rush_detected and (self.army.amount >= self.rush_army_attack_amount or
                                       self.state.game_loop >= 2688):  # 2:00
                self.rush_detected = False
                self.defence_radius = self.normal_defence_radius
                self.scout = None

        async def guardian():
            if self.raid_detected or self.wroker_rush_detected or self.rush_detected or self.guard_pos is None or \
                    self.cached_enemies.closer_than(40, self.start_location) \
                            .filter(lambda u: u.ground_range > 2 or u.type_id is UnitTypeId.ZEALOT).exists:
                # disable guardian if each unit is needed or ranged units detected
                self.guardian = None
            else:
                # assign new guardian
                if self.guard_pos is not None and (self.guardian is None or
                                                   self.army.find_by_tag(self.guardian) is None) and \
                        self.army.not_flying.exists:
                    guardians = self.army.of_type([UnitTypeId.STALKER, UnitTypeId.ADEPT, UnitTypeId.ZEALOT])
                    if guardians.exists:
                        self.guardian = guardians.closest_to(self.guard_pos).tag
                # guardian handling
                if self.guard_pos is not None and self.guardian is not None:
                    guardian = self.army.find_by_tag(self.guardian)
                    if guardian is not None:
                        self.army = self.army.tags_not_in([self.guardian])  # exclude guardian from army
                        meele = self.cached_enemies.of_type([UnitTypeId.ZEALOT, UnitTypeId.DARKTEMPLAR,
                                                             UnitTypeId.ZERGLING]).closer_than(10, self.guard_pos)
                        close_meele = meele.closer_than(2, self.guard_pos)
                        if meele.exists and close_meele.empty:
                            if not guardian.position.is_same_as(self.guard_pos):
                                await self.do(guardian.move(self.guard_pos))
                            await self.do(guardian.hold_position(queue=True))
                        elif close_meele.empty and not guardian.position.is_same_as(self.guard_pos, dist=2):
                            await self.do(guardian.move(self.guard_pos))
                        elif not guardian.is_idle and not guardian.is_attacking:
                            await self.do(guardian.stop(queue=True))

        async def scout():
            # scout base to detect cannon proxies
            async def scout_base(scout):
                base_height = self.get_terrain_height(self.start_location)
                if not self.base_scout_points:
                    for pos in points_in_circum(18, self.start_location):
                        if not self.is_explored(pos) and self.get_terrain_height(pos) == base_height:
                            self.base_scout_points.append(pos)
                for pos in self.base_scout_points:
                    await self.do(scout.move(pos, queue=True))

            # scout only terrans
            if self.enemy_race is Race.Terran and self.state.game_loop == 336:  # 0:15
                scout = await self.take_probe(self.enemy_start_locations[0])
                if scout:
                    esl = self.enemy_start_locations[0]
                    vec = esl.direction_vector(self._game_info.map_center)
                    await self.do(scout.move(esl + vec * 8))
                    await self.do(scout.move(esl + Point2((vec.x, -vec.y)) * 8, queue=True))
                    await self.do(scout.move(esl - vec * 8, queue=True))
                    await self.do(scout.move(esl + Point2((-vec.x, vec.y)) * 8, queue=True))
            if self.enemy_race is Race.Terran and self.state.game_loop == 1680:  # 1:15
                self.scout = None
                await detect_rush()

            # 1:15, 2:15
            if self.enemy_race is Race.Protoss and (self.state.game_loop == 1680 or self.state.game_loop == 3024):
                scout = await self.take_probe(self.start_location)
                if scout:
                    await self.do(scout.stop())
                    await scout_base(scout)

            if self.state.game_loop == 1008:  # 45 sec
                scout = await self.take_probe(self.start_location)
                if scout:
                    await self.do(scout.stop())
                    for pos in get_unexplored_points(self.large_defence_radius):
                        await self.do(scout.move(pos, queue=True))

        async def handle_army():
            gs_active = self.army.filter(lambda u: u.has_buff(BuffId.GUARDIANSHIELD)).exists or \
                        self.last_gs_casted + 20 > self.state.game_loop
            low_health_amount = len([unit for unit in self.army if is_low_health(unit)])

            enemy_dps = 0
            if enemies.ready.exists:
                for u in enemies:  # .ready.closer_than(20, unit):
                    enemy_dps += u.ground_dps
            my_dps = 0
            for u in self.army:  # .closer_than(10, unit):
                if not is_low_health(u):
                    my_dps += u.ground_dps

            for unit in self.army:
                if not gs_active and unit.type_id == UnitTypeId.SENTRY and self.units_hp > 0 and \
                        await self.can_cast(unit, AbilityId.GUARDIANSHIELD_GUARDIANSHIELD):
                    await self.do(unit(AbilityId.GUARDIANSHIELD_GUARDIANSHIELD))
                    gs_active = True
                    self.last_gs_casted = self.state.game_loop
                    continue

                target = None
                # half stalkers always attack air
                if unit.type_id is UnitTypeId.STALKER and good_only_flying.exists and hash(str(unit.tag)) % 2:
                    target = good_only_flying.closest_to(unit)

                possible_targets = enemies.filter(lambda enemy: unit.target_in_range(enemy))
                closest_target = None
                if possible_targets and target is None:
                    # don't retreat from reapers, just kill them
                    fearable_targets = possible_targets.exclude_type([UnitTypeId.REAPER])
                    if fearable_targets.exists:
                        closest_target = fearable_targets.closest_to(unit)
                    # target weakest unit
                    # target = min(possible_targets, key=lambda t: t.health + t.shield)
                    # target weakest damager
                    target = min(possible_targets, key=lambda t: (t.health + t.shield) /
                                                                 (t.ground_dps + t.air_dps + 1))
                closest_enemy = None
                treat_outrange = -100
                if enemies:
                    closest_enemy = enemies.closest_to(unit)
                    fearable_enemies = enemies.exclude_type([UnitTypeId.REAPER])
                    if fearable_enemies.exists:
                        if unit.type_id is UnitTypeId.COLOSSUS:
                            treat = max(fearable_enemies, key=lambda e: get_range(e, "both") ** 2 -
                                                                        e.position._distance_squared(unit.position))
                            treat_outrange = unit.radius + treat.radius + max(1, get_range(treat, "both")) - \
                                             unit.distance_to(treat)
                        elif unit.is_flying:
                            treat = max(fearable_enemies, key=lambda e: e.air_range ** 2 -
                                                                        e.position._distance_squared(unit.position))
                            treat_outrange = unit.radius + treat.radius + max(1, get_range(treat, "air")) - \
                                             unit.distance_to(treat)
                        else:
                            treat = max(fearable_enemies, key=lambda e: e.ground_range ** 2 -
                                                                        e.position._distance_squared(unit.position))
                            treat_outrange = unit.radius + treat.radius + max(1, get_range(treat, "ground")) - \
                                             unit.distance_to(treat)

                # army is big enough | we are winning | enemy is near
                attack = (self.army.amount >= self.army_attack_amount and my_dps > enemy_dps) or \
                         self.units_dps > self.units_hps or \
                         (unit.can_attack_ground and ok_ground.closer_than(self.defence_radius, self.start_location)) \
                         or (unit.can_attack_air and ok_flying.closer_than(self.defence_radius, self.start_location))

                if target is None:  # no unit to attack right now
                    target = self.cached_main_ramp_top
                    if self.guard_pos is not None:
                        target = self.guard_pos.towards(self.start_location, 4)
                    if attack:
                        # check for available targets
                        target = get_target(unit)

                need_move = False
                if unit.type_id is not UnitTypeId.ZEALOT:  # zealots don't retreat!
                    # unit is close to the enemy and can't fire yet OR
                    # if low health stand 1 coupus behind emeny atack radius
                    if (unit.type_id is not UnitTypeId.VOIDRAY and unit.weapon_cooldown > 2 and
                        filter_attacking(possible_targets).exists and
                        closest_target is not None and (in_range(unit, closest_target) or treat_outrange >= 0)) or \
                            ((low_health_amount < self.army.amount / 2) and is_low_health(unit) and
                             (treat_outrange + unit.radius * 2 >= 0 or unit.type_id is UnitTypeId.SENTRY)):
                        target = self.start_location
                        if unit.distance_to(self.start_location) < 10:
                            target = closest_enemy.position.towards(unit.position, 10)
                        need_move = True

                queue = False
                if await self.has_ability(AbilityId.EFFECT_BLINK_STALKER, unit,
                                          ignore_resource_requirements=False) and unit.distance_to(target) > 6 and \
                        target is not UnitTypeId.ZERGLING:  # don't jump into zerglings
                    if not need_move:
                        towards = -unit.radius + unit.ground_range  # one corpus closer
                        if isinstance(target, Unit):
                            towards += target.radius
                            target = target.position.towards(unit.position, towards)
                        else:
                            target = target.towards(unit.position, towards)
                    await self.do(unit(AbilityId.EFFECT_BLINK_STALKER, target))
                    if need_move and possible_targets.exists:
                        # blink in other direction if can't blink back to base
                        alt_target = unit.position.towards(possible_targets.center, -8)
                        await self.do(unit(AbilityId.EFFECT_BLINK_STALKER, alt_target, queue=True))
                    queue = True

                # don't repeat orders
                if is_same_order(unit, target, check_point=True, dist=2):
                    return

                if need_move:
                    await self.do(unit.move(target, queue=queue))
                else:
                    await self.do(unit.attack(target, queue=queue))

        async def handle_observers():
            async def handle_target(obs: Unit, target: Point2):
                eaapos = evade_anti_air(obs, target)
                await self.do(obs.move(eaapos))
                # siege doesn't work now because of different orders (and dangers of being static)
                '''if eaapos.is_same_as(target) and obs.position.is_same_as(eaapos, dist=2) and not obs.is_moving:
                    if obs.type_id is UnitTypeId.OBSERVER:
                        await self.do(obs(AbilityId.MORPH_SURVEILLANCEMODE))
                else:
                    if obs.type_id is UnitTypeId.OBSERVERSIEGEMODE:
                        await self.do(obs(AbilityId.MORPH_OBSERVERMODE))
                    else:
                        await self.do(obs.move(eaapos))'''

            # will handle only 2 first observers
            if self.army.empty:
                return
            ac = self.army.closest_to(self.army.center)
            if observers.amount > 0:
                obs = observers.first
                if good_flying.exists:
                    target = good_flying.closest_to(ac).position
                else:
                    # target = ac.position.towards(self.enemy_start_locations[0], 10)
                    target = self.enemy_start_locations[0]
                await handle_target(obs, target)

            if observers.amount > 1:
                obs = observers[1]
                target = ac.position
                await handle_target(obs, target)

        async def handle_fleet():
            # 0.25s for the last four
            IC_LAUNCH = 8
            IC_LEASH = 12

            # todo: method for every unit, so self.fleet - carrires only
            if self.fleet.empty:
                return

            # count interceptors
            ic_max = self.fleet.amount * 8
            ic_ordered = sum([order.ability.id == AbilityId.BUILD_INTERCEPTORS
                              for unit in self.fleet for order in unit.orders])
            # ic_ordered can't be more than 5
            ic_amount = ic_max - ic_ordered
            ic_rate = ic_amount / ic_max
            if ic_rate < 0.5:  # can't be less than 0.4
                self.fleet_retreat = True
            elif ic_rate >= 0.75:
                self.fleet_retreat = False

            fleet_gathering_point = self.cached_main_ramp_top
            batts = self.units(UnitTypeId.SHIELDBATTERY)
            if batts.exists:
                fleet_gathering_point = batts.center

            group_target = None
            attack = not self.fleet_retreat and (self.fleet.amount >= 8 or
                                                 ok_flying.closer_than(self.defence_radius, self.start_location) or
                                                 self.minerals < 50)
            if attack:
                leader = self.fleet.closest_to(self.enemy_start_locations[0])
                # check for available targets
                if good_flying.exists:
                    group_target = good_flying.closest_to(leader)
                elif ok_flying.exists:
                    group_target = ok_flying.closest_to(leader)
                elif not self.is_explored(self.enemy_start_locations[0]):
                    group_target = self.enemy_start_locations[0]
            else:
                group_target = fleet_gathering_point

            for unit in self.fleet:
                # add interceptors to count amounts
                if await self.has_ability(AbilityId.BUILD_INTERCEPTORS, self.fleet.first):
                    await self.do(self.fleet.first(AbilityId.BUILD_INTERCEPTORS))

                target = group_target
                if target is None:
                    # individual targets if searching for enemy
                    possible_locations = self.cached_minerals.sorted_by_distance_to(self.start_location)
                    target = possible_locations[hash(str(unit.tag)) % len(possible_locations)].position

                targets = enemies.filter(lambda enemy: enemy.distance_to(unit) <= IC_LEASH)
                treats = targets.filter(lambda enemy: enemy.can_attack_air or enemy.type_id is UnitTypeId.MEDIVAC)
                treats_dps = sum([enemy.air_dps for enemy in treats])
                dangers = targets.filter(lambda enemy: in_range(enemy, unit, gap=-1, air_or_ground="air"))
                dangers_dps = sum([enemy.air_dps for enemy in dangers])
                if treats and attack:
                    target = min(treats, key=lambda treat: (treat.health + treat.shield) /
                                                           (treat.air_dps + 1 +
                                                            (treat.type_id is UnitTypeId.MEDIVAC) * 100))
                elif targets and attack:
                    target = targets.closest_to(unit)

                need_move = self.fleet_retreat
                if unit.hp > 0 or dangers_dps > (unit.health + unit.shield) / 5 or \
                        treats_dps > (unit.health + unit.shield) / 2.5:
                    target = fleet_gathering_point
                    if unit.position._distance_squared(self.start_location) < \
                            fleet_gathering_point._distance_squared(self.start_location) + 4:
                        target = self.start_location
                    if treats:
                        # here target is fleet_gathering_point or start_location
                        target = treats.center.towards(unit, 20).towards(target, 5)
                    need_move = True

                # don't repeat orders
                if is_same_order(unit, target, check_point=True, dist=2):
                    return

                if need_move:
                    await self.do(unit.move(target))
                else:
                    await self.do(unit.attack(target))

        async def handle_phoenixes():
            # tested on one unit
            phoenixes = self.units(UnitTypeId.PHOENIX)
            if phoenixes.empty:
                return

            target = None
            # priority: flying anti-ground like banshee
            targets = good_only_flying.filter(lambda target: not target.can_attack_air)
            # next: flying non-attackers like overs, buildings
            if targets.empty:
                targets = ok_flying.flying.filter(lambda target: not target.can_attack_air)

            for unit in phoenixes:
                if targets:
                    enemy = unit.position.closest(targets)
                    target = enemy.position.towards(unit, 4 + unit.radius + enemy.radius)
                if target is None:
                    if unit.is_idle:
                        target = random.choice(self.positions_for_nexuses)
                    else:
                        order_target = unit.order_target
                        if isinstance(unit.order_target, Point2):
                            target = order_target
                        elif isinstance(unit.order_target, int):
                            enemy = self.cached_enemies.find_by_tag(unit.order_target)
                            if enemy:
                                target = enemy.position.towards(unit, 3 + unit.radius + enemy.radius)
                        if target is None:
                            # this should not happen
                            continue

                evade_target = evade_anti_air(unit, target.position)
                if not evade_target.is_same_as(target.position):
                    target = evade_target

                if is_same_order(unit, target, check_point=True, dist=0.1):
                    return

                await self.do(unit.move(target))

        async def handle_batteries():
            """ used only to heal pylon """
            batts = self.units(UnitTypeId.SHIELDBATTERY)
            pylons = self.units(UnitTypeId.PYLON)
            if batts.empty or pylons.empty:
                return
            # pprint(await self.get_available_abilities(batts.first))

            pylon = pylons.closest_to(batts.center)
            if pylon.shield < pylon.shield_max:
                for batt in batts.prefer_close_to(pylon):
                    if batt.energy > 0:
                        await self.do(batt(AbilityId.EFFECT_RESTORE, pylon))

        def evade_anti_air(unit: Unit, target: Point2) -> Point2:
            def check_enemy_ranged(pos: Point2) -> Point2:
                already_in_range_of = [enemy.position for enemy in enemies.closer_than(16, pos) if enemy.can_attack_air
                                       and in_range(enemy, unit, gap=-1, air_or_ground="air")]
                # shortest evasion route
                if already_in_range_of:
                    center = Point2.center(already_in_range_of)
                    vec = pos - center
                    l = abs(vec)
                    if l > 0.1:
                        vec /= l
                        return pos + vec * 5  # 5 cells to use full speed
                return pos

            pos = unit.position
            npos = check_enemy_ranged(pos)
            if not npos.is_same_as(pos):
                return npos

            # not in range now, but if you move 1 cell further?
            vec = target - pos
            l = abs(vec)
            if l > 0.1:
                vec /= l
                npos = check_enemy_ranged(pos + vec)
                if not npos.is_same_as(pos + vec):
                    return npos

            return target

        def is_same_order(unit: Unit, target, check_point=False, dist=1.0):
            # move sometimes don't work, so check_point=False by default
            order_target = unit.order_target
            if order_target is not None:
                if isinstance(order_target, int):
                    enemy = self.cached_enemies.find_by_tag(order_target)
                    if enemy is not None and isinstance(target, Unit) and enemy.tag == target.tag:
                        return True  # same target
                elif check_point and isinstance(order_target, Point2) and isinstance(target, Point2) and \
                        (order_target.is_same_as(target, dist=dist)):
                    return True  # same target
            elif isinstance(target, Point2) and unit.position.is_same_as(target.position, dist=dist):
                return True  # same target
            return False

        def get_target(unit: Unit):
            if good_flying.exists and unit.can_attack_air:
                target = good_flying.closest_to(unit).position
            elif good_ground.exists:
                target = good_ground.closest_to(unit).position
            elif ok_flying.exists and unit.can_attack_air:
                target = ok_flying.closest_to(unit).position
            elif ok_ground.exists:
                target = ok_ground.closest_to(unit).position
            else:
                target = self.enemy_start_locations[0]
                # explore all expansions if enemy main is destroyed
                if self.is_explored(target):
                    possible_locations = self.cached_minerals.sorted_by_distance_to(self.start_location)
                    target = possible_locations[hash(str(unit.tag)) % len(possible_locations)].position
            return target

        def get_unexplored_points(distance) -> [Point2]:
            els = sorted(self.expansion_locations.keys(),
                         key=lambda p: p.distance_to(self.cached_minerals
                                                     .closest_to(self.main_base_ramp.bottom_center)))
            els[0] = els[0].towards(self.start_location, -6)  # check natural
            return [p for p in els if p.distance_to(self.cached_main_ramp_top) <= distance and not self.is_explored(p)]

        def is_low_health(unit):
            return unit.health + unit.shield < min(unit.health_max, unit.shield_max)

        def get_range(unit: Unit, target: str) -> Union[int, float]:
            bonus = 0
            if Unit.type_id is UnitTypeId.BUNKER:
                bonus = 7
            elif Unit.type_id is UnitTypeId.HYDRALISK:
                bonus = 1
            elif Unit.type_id is UnitTypeId.PHOENIX:
                bonus = 2
            elif Unit.type_id is UnitTypeId.COLOSSUS:
                bonus = 2
            elif Unit.type_id is UnitTypeId.PLANETARYFORTRESS:
                bonus = 1
            elif Unit.type_id is UnitTypeId.REAPER:
                bonus = -5  # ignore them
            if target == "ground":
                return unit.ground_range + bonus
            elif target == "air":
                return unit.air_range + bonus
            elif target == "both":
                return max(unit.ground_range, unit.air_range) + bonus
            else:
                raise ValueError('Unknown target type', target)

        def in_range(unit, target, gap=0.5, air_or_ground="both"):
            # if gap > 0, in_range will be true if unit is closer than maximum fire range
            return unit.distance_to(target) + gap < unit.radius + target.radius + get_range(unit, air_or_ground)

        def filter_attacking(units: Units) -> Units:
            return units.filter(lambda u: (u.can_attack_ground or u.can_attack_air) and (
                    u.position._distance_squared(self.map_corners[0]) > 2 and  # hack: corner flyers, todo: better
                    u.position._distance_squared(self.map_corners[1]) > 2 and
                    u.position._distance_squared(self.map_corners[2]) > 2 and
                    u.position._distance_squared(self.map_corners[3]) > 2
            ))

        ok_flying = self.cached_enemies.exclude_type([UnitTypeId.LARVA, UnitTypeId.EGG, UnitTypeId.KD8CHARGE])
        ok_ground = ok_flying.not_flying
        good_flying = filter_attacking(ok_flying)
        good_ground = filter_attacking(ok_ground)
        good_only_flying = good_flying.flying
        self.army = self.units.of_type([UnitTypeId.ZEALOT, UnitTypeId.ADEPT, UnitTypeId.STALKER, UnitTypeId.SENTRY,
                                        UnitTypeId.IMMORTAL, UnitTypeId.COLOSSUS]).ready
        observers = self.units.of_type([UnitTypeId.OBSERVER, UnitTypeId.OBSERVERSIEGEMODE]).sorted(lambda o: o.tag)
        self.fleet = self.units.of_type([UnitTypeId.CARRIER, UnitTypeId.MOTHERSHIP])

        await handle_worker_rush()
        await handle_raid()
        # await guardian()
        await scout()
        await handle_rush()
        await probe_defence()

        enemies = ok_flying | self.enemy_prev_units.values()
        await handle_army()
        await handle_observers()
        await handle_fleet()
        await handle_phoenixes()
        await handle_batteries()

    async def on_building_construction_complete(self, unit: Unit):
        if unit.type_id == UnitTypeId.NEXUS:
            self.defence_radius = max(self.defence_radius, self.start_location.distance_to(unit) + 10)

    async def step(self):
        if self.iteration == 0:
            await self.make_buildings_map()
            if self.game_info._proto.map_name.replace(" ", "").lower() in ["automatonle", "stasisle"]:
                self.build_order = self.main_build_order
        if self.iteration == 1:
            await self.chat_send("SeeBot v2.4.8 (glhf)")

        # await self.debug_buildings_map()
        # sleep(0.03)
        # pprint([self.state.game_loop, self.get_time(), gw.first])
        await self.strategy()
        await self.tactics()
