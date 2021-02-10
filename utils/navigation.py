import hlt
import math
from hlt.entity import Position, Ship, Planet, Entity
from utils.geometry import Point, Seg, min_dist, ps_dist
from hlt.constants import *
from utils.feature_collector import FeatureCollector
import logging


def unite_for_rush(ship: Ship, target: Ship, fc: FeatureCollector):
    """
    Simple rush_nav command for positioning ships close to each other.
    Target supposed to be center of mass of allied ships.

    :param ship: Allied ship
    :param target: Center of mass of allied ships
    :param fc: Feature collector class instance
    """
    navigate_command, move, _, _ = rush_nav(ship, ship.closest_point_to(target, min_distance=0.1), fc.game_map,
                                            None, fc.move_table)
    if navigate_command:
        fc.command_queue.append(navigate_command)
        fc.move_table[ship] = move


def rush_attack(ship: Ship, target: Ship, fc: FeatureCollector, speed=hlt.constants.MAX_SPEED):
    """
    Simple rush_nav command for attacking enemy ship

    :param ship: Allied ship
    :param target: Enemy ship
    :param fc: Feature collector class instance
    :param speed: Speed of allied ship
    """
    navigate_command, move, _, _ = rush_nav(ship, ship.closest_point_to(target, min_distance=4), fc.game_map,
                                            None, fc.move_table, speed=speed)
    if navigate_command:
        fc.command_queue.append(navigate_command)
        fc.move_table[ship] = move


def rush_leader_modeling(ship: Ship, target: Ship, fc: FeatureCollector, speed=hlt.constants.MAX_SPEED, dist=4):
    """
    Trying to move rush leader ship.

    :param ship: Rush leader ship
    :param target: Enemy ship
    :param fc: Feature collector class instance
    :param speed: Speed of rush leader ship
    :param dist: Minimum distance to approach
    :return: Speed and angle for ship thrust if rush leader move is available, None otherwise
    :rtype: int or None
    """
    navigate_command, move, spd, move_ang = rush_nav(ship, ship.closest_point_to(target, min_distance=dist),
                                                     fc.game_map, None, speed=speed)
    if navigate_command:
        return spd, move_ang
    else:
        return None, None


def attack(ship: Ship, target: Ship, fc: FeatureCollector, speed=hlt.constants.MAX_SPEED, kamikaze=True):
    """
    Standard attack command. Navigates allied ship to specified closest point near enemy ship.
    Takes into account kamikaze mode.

    :param ship: Allied ship
    :param target: Enemy ship
    :param fc: Feature collector class instance
    :param speed: Speed of allied ship
    :param kamikaze: Boolean, ship with low hp will self-destruct damaging enemy if True
    """
    if (ship.health <= hlt.constants.WEAPON_DAMAGE * 1.25) and kamikaze and (
            target.id not in fc.kamikaze_assignment_enemy) and (
            target.docking_status == target.DockingStatus.UNDOCKED) and (
            target.health >= hlt.constants.MAX_SHIP_HEALTH - hlt.constants.WEAPON_DAMAGE * 1.25):
        # KAMIKAZE
        navigate_command, move = nav(ship, ship.closest_point_to(target, min_distance=0), fc.game_map, None,
                                     fc.move_table, speed=speed)
        if navigate_command:
            fc.command_queue.append(navigate_command)
            fc.move_table[ship] = move
            fc.assign_kamikaze_enemy(target.id)
    else:
        navigate_command, move = nav(ship, ship.closest_point_to(target, min_distance=4), fc.game_map, None,
                                     fc.move_table, speed=speed)
        if navigate_command:
            fc.command_queue.append(navigate_command)
            fc.move_table[ship] = move


def go_to_planet(ship: Ship, target: Planet, fc: FeatureCollector):
    """
    Navigate ship to planet.

    :param ship: Allied ship
    :param target: Planet
    :param fc: Feature collector class instance
    """
    navigate_command, move = nav(ship, ship.closest_point_to(target), fc.game_map, None, fc.move_table)
    if navigate_command:
        fc.command_queue.append(navigate_command)
        fc.move_table[ship] = move


def attack_and_assign(ship: Ship, target: Ship, fc: FeatureCollector):
    """
    Attack command with ship assignment to enemy ship.

    :param ship: Allied ship
    :param target: Enemy ship
    :param fc: Feature collector class instance
    """
    navigate_command, move = nav(ship, ship.closest_point_to(target, min_distance=4), fc.game_map, None, fc.move_table)
    if navigate_command:
        fc.command_queue.append(navigate_command)
        fc.move_table[ship] = move
    fc.assign_ship(ship.id, "enemy")
    fc.assign_enemy_ship_to_ship(ship.id, target)
    fc.assign_enemy(target.id)


def go_to_planet_and_assign(ship: Ship, target: Planet, fc: FeatureCollector):
    """
    Navigate ship to planet with ship assignment to that planet

    :param ship: Allied ship
    :param target: Planet
    :param fc: Feature collector class instance
    """
    navigate_command, move = nav(ship, ship.closest_point_to(target), fc.game_map, None, fc.move_table)
    if navigate_command:
        fc.command_queue.append(navigate_command)
        fc.move_table[ship] = move
    fc.assign_ship(ship.id, "planet")
    fc.assign_planet_to_ship(ship.id, target)
    fc.assign_planet(target.id)


def undocking_thrust(ship: Ship, target: Position, fc: FeatureCollector, speed=hlt.constants.MAX_SPEED,
                     avoid_obstacles=True, max_corrections=90, angular_step=1,
                     ignore_ships=False, ignore_planets=False, initial_angle=0):
    """
    In Halite II there is a bug, that allows to undock one move faster, if thrust on last step of undocking process.
    Here we take into account possible collisions when undocking. This code is from hlt.entity.Ship.navigate

    :param ship: Allied ship
    :param target: Position to which ship is moving. Initially it can be planet, but with angle = angle - 180
    :param fc: Feature collector class instance
    :param speed: Speed of allied ship
    :param max_corrections: Max tries to correct angle
    :param initial_angle: That same angle = angle - 180
    :return: None, if correction failed, else navigation command (thrust)
    """
    # Assumes a position, not planet (as it would go to the center of the planet otherwise)
    if max_corrections <= 0:
        return None

    # TODO: fix here, distance should be MAX_SPEED, not distance to planet

    distance = ship.calculate_distance_between(target)
    angle = initial_angle
    ignore = () if not (ignore_ships or ignore_planets) \
        else Ship if (ignore_ships and not ignore_planets) \
        else Planet if (ignore_planets and not ignore_ships) \
        else Entity
    if avoid_obstacles and fc.game_map.obstacles_between(ship, target, ignore):
        new_target_dx = math.cos(math.radians(angle + angular_step)) * distance
        new_target_dy = math.sin(math.radians(angle + angular_step)) * distance
        new_target = Position(ship.x + new_target_dx, ship.y + new_target_dy)
        return undocking_thrust(ship, new_target, fc, max_corrections=max_corrections - 1)
    speed = speed if (distance >= speed) else distance
    return ship.thrust(speed, angle)


def nav(ship, targ, gmap, obs, move_table={}, speed=MAX_SPEED, max_deviation=60):
    # Source: https://github.com/Mvwivs/halite2-deep-rl-bot

    dist = ship.calculate_distance_between(targ)
    angle = round(ship.calculate_angle_between(targ))
    speed = speed if (dist >= speed) else int(dist)

    if obs == None:
        dships = [s for s in gmap.get_me().all_ships() if not (s.docking_status == Ship.DockingStatus.UNDOCKED)]
        uships = [s for s in gmap.get_me().all_ships() if (s.docking_status == Ship.DockingStatus.UNDOCKED)]
        obs = [e for e in gmap.all_planets() + dships
               if ship.calculate_distance_between(e) - ship.radius - e.radius <= dist]
        obs.extend([e for e in uships if e != ship
                    and ship.calculate_distance_between(e) - ship.radius - e.radius <= MAX_SPEED * 2])

    obs = sorted(obs, key=lambda t: ship.calculate_distance_between(t))
    angs = [int(n / 2) if n % 2 == 0 else -int(n / 2) for n in range(1, max_deviation * 2 + 2)]
    speeds = [speed, round(speed / 2)]

    for d_ang in angs:
        for spd in speeds:
            move_ang = (angle + d_ang) % 360
            d = Point.polar(spd, move_ang)
            move = Seg(Point(ship.x, ship.y), Point(ship.x, ship.y) + d)

            d = Point.polar(dist, move_ang)
            full_move = Seg(Point(ship.x, ship.y), Point(ship.x, ship.y) + d)

            for e in obs:
                collide_dist = ship.radius + e.radius + .00001

                if e in move_table and min_dist(move, move_table[e]) <= collide_dist:
                    break
                elif not e in move_table:
                    if type(e) == Ship and (e.docking_status == Ship.DockingStatus.UNDOCKED):
                        if ps_dist(Point(e.x, e.y), move) <= collide_dist:
                            break
                    elif ps_dist(Point(e.x, e.y), full_move) <= collide_dist:
                        break
            else:
                return ship.thrust(spd, move_ang), move

    return None, None


def rush_nav(ship, targ, gmap, obs, move_table={}, speed=MAX_SPEED, max_deviation=180):
    """
    Rush navigation function. Almost copy of nav. Greater correction range, because when rushing,
    there is only not more than three allied ships. Timeouts are "impossible".

    :param ship: Allied ship
    :param targ: Position
    :param gmap: hlt.game_map
    :param obs: List of entities on the way
    :param move_table: Dict of moves of ships
    :param speed: Speed of allied ship
    :param max_deviation: Max deviation of angle
    :return: Thrust command if there is available move without collision, None otherwise
    """
    dist = ship.calculate_distance_between(targ)
    angle = round(ship.calculate_angle_between(targ))
    speed = speed if (dist >= speed) else int(dist)

    if obs == None:
        dships = [s for s in gmap.get_me().all_ships() if not (s.docking_status == Ship.DockingStatus.UNDOCKED)]
        uships = [s for s in gmap.get_me().all_ships() if (s.docking_status == Ship.DockingStatus.UNDOCKED)]
        obs = [e for e in gmap.all_planets() + dships
               if ship.calculate_distance_between(e) - ship.radius - e.radius <= dist]
        obs.extend([e for e in uships if e != ship
                    and ship.calculate_distance_between(e) - ship.radius - e.radius <= MAX_SPEED * 2])

    obs = sorted(obs, key=lambda t: ship.calculate_distance_between(t))
    angs = [int(n / 2) if n % 2 == 0 else -int(n / 2) for n in range(1, max_deviation * 2 + 2)]
    speeds = [spd for spd in range(speed, 0, -1)]

    for d_ang in angs:
        for spd in speeds:
            move_ang = (angle + d_ang) % 360
            d = Point.polar(spd, move_ang)
            move = Seg(Point(ship.x, ship.y), Point(ship.x, ship.y) + d)

            d = Point.polar(dist, move_ang)
            full_move = Seg(Point(ship.x, ship.y), Point(ship.x, ship.y) + d)

            for e in obs:
                collide_dist = ship.radius + e.radius + .00001

                if e in move_table and min_dist(move, move_table[e]) <= collide_dist:
                    break
                elif not e in move_table:
                    if type(e) == Ship and (e.docking_status == Ship.DockingStatus.UNDOCKED):
                        if ps_dist(Point(e.x, e.y), move) <= collide_dist:
                            break
                    elif ps_dist(Point(e.x, e.y), full_move) <= collide_dist + 2:
                        break
            else:
                return ship.thrust(spd, move_ang), move, spd, move_ang
    return None, None, None, None
