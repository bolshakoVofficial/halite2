import hlt
import logging
from utils.feature_collector import FeatureCollector
from utils import constants as my_const
from utils import navigation
import time


def standard_strategy(ship: hlt.entity.Ship, fc: FeatureCollector):
    """
    Default behavior of a ship without specific role.

    First attack enemy if it's close. Otherwise try to go to closest planet prior to already assigned planet
    (if assigned and unassigned planets exist). Otherwise try to go to closest available assigned planet.
    Otherwise try to go to closest available unassigned planet. Else: no free planets - attack enemy ships

    :param ship: Allied ship
    :param fc: Feature collector class instance
    """

    # Skip docked ships
    if ship.docking_status != ship.DockingStatus.UNDOCKED:
        return

    # ATTACK IF ENEMY IS CLOSE
    if fc.closest_enemy_ships_distances[0] < my_const.RANGE_OF_AGGRESSION:
        # logging.info("ATTACK IF ENEMY IS CLOSE")
        navigation.attack_and_assign(ship, fc.closest_enemy_ships[0], fc)

    # GO TO CLOSEST AVAIL PLANET FROM (ASSIGNED AND UNASSIGNED PLANETS)
    elif fc.closest_avail_assigned_planet() and fc.closest_avail_unassigned_planet():
        # logging.info("GO TO CLOSEST AVAIL PLANET FROM (ASSIGNED AND UNASSIGNED PLANETS)")
        # Starting planet choice assumes greedy choice
        if ((fc.turn < 10) and ship.calculate_distance_between(
                fc.closest_avail_unassigned_planet()) + my_const.GREEDY_PLANET_DISTANCE <
            ship.calculate_distance_between(fc.closest_avail_assigned_planet())) or \
                ((fc.turn >= 10) and ship.calculate_distance_between(
                    fc.closest_avail_unassigned_planet()) < ship.calculate_distance_between(
                    fc.closest_avail_assigned_planet())):

            if fc.closest_avail_unassigned_planet().is_owned():
                # it's enemy's
                navigation.attack_and_assign(ship, fc.closest_enemy_to_planet(
                    fc.closest_avail_unassigned_planet().id), fc)
            else:
                # it's empty
                if ship.can_dock(fc.closest_avail_unassigned_planet()):
                    fc.command_queue.append(ship.dock(fc.closest_avail_unassigned_planet()))

                    fc.assign_ship(ship.id, "planet")
                    fc.assign_planet_to_ship(ship.id, fc.closest_avail_unassigned_planet())
                    fc.assign_planet(fc.closest_avail_unassigned_planet().id)

                else:
                    navigation.go_to_planet_and_assign(ship, fc.closest_avail_unassigned_planet(), fc)
        else:
            if ship.can_dock(fc.closest_avail_assigned_planet()):
                fc.command_queue.append(ship.dock(fc.closest_avail_assigned_planet()))

                fc.assign_ship(ship.id, "planet")
                fc.assign_planet_to_ship(ship.id, fc.closest_avail_assigned_planet())
                fc.assign_planet(fc.closest_avail_assigned_planet().id)
            else:
                navigation.go_to_planet_and_assign(ship, fc.closest_avail_assigned_planet(), fc)

    # NO AVAIL UNASSIGNED PLANETS. GO TO CLOSEST AVAIL ASSIGNED
    elif fc.closest_avail_assigned_planet():
        logging.info("NO AVAIL UNASSIGNED PLANETS. GO TO CLOSEST AVAIL ASSIGNED")
        if ship.can_dock(fc.closest_avail_assigned_planet()):
            fc.command_queue.append(ship.dock(fc.closest_avail_assigned_planet()))

            fc.assign_ship(ship.id, "planet")
            fc.assign_planet_to_ship(ship.id, fc.closest_avail_assigned_planet())
            fc.assign_planet(fc.closest_avail_assigned_planet().id)

        else:
            navigation.go_to_planet_and_assign(ship, fc.closest_avail_assigned_planet(), fc)

    # NO AVAIL ASSIGNED PLANETS. GO ON CLOSEST AVAIL UNASSIGNED
    elif fc.closest_avail_unassigned_planet():
        logging.info("NO AVAIL ASSIGNED PLANETS. GO ON CLOSEST AVAIL UNASSIGNED")
        if fc.closest_avail_unassigned_planet().is_owned():
            # it's enemy's
            navigation.attack_and_assign(ship, fc.closest_enemy_to_planet(
                fc.closest_avail_unassigned_planet().id), fc)
        else:
            # it's empty
            if ship.can_dock(fc.closest_avail_unassigned_planet()):
                fc.command_queue.append(ship.dock(fc.closest_avail_unassigned_planet()))

                fc.assign_ship(ship.id, "planet")
                fc.assign_planet_to_ship(ship.id, fc.closest_avail_unassigned_planet())
                fc.assign_planet(fc.closest_avail_unassigned_planet().id)

            else:
                navigation.go_to_planet_and_assign(ship, fc.closest_avail_unassigned_planet(), fc)

    # SEEMS LIKE NO USEFUL PLANETS. GO ATTACK ENEMY SHIPS
    else:
        logging.info("SEEMS LIKE NO USEFUL PLANETS. GO ATTACK ENEMY SHIPS")
        navigation.attack_and_assign(ship, fc.closest_enemy_ships[0], fc)


def strategy_if_assigned(ship: hlt.entity.Ship, fc: FeatureCollector):
    """
    For each role there is its own behavior.

    Ship can be assigned to (bot_v1):
    - enemy
    - planet

    :param ship: Allied ship
    :param fc: Feature collector class instance
    """

    # Strategy for ship assigned to enemy ships
    if fc.assigned_ships[ship.id] == "enemy":
        if ship.calculate_distance_between(fc.closest_enemy_ships[0]) < (2 * hlt.constants.MAX_SPEED):
            # if closest enemy closer than 2 * MAX_SPEED
            if fc.closest_enemy_ships[0].id == fc.ship_enemy_ship_dict[ship.id].id:
                # if it is that same assigned enemy
                navigation.attack(ship, fc.ship_enemy_ship_dict[ship.id], fc)
            else:
                # or attack nearest then
                fc.unassign_ship(ship.id)
                fc.unassign_enemy(fc.ship_enemy_ship_dict[ship.id].id)
                fc.unassign_enemy_ship_to_ship(ship.id)
                navigation.attack_and_assign(ship, fc.closest_enemy_ships[0], fc)
        elif fc.ship_enemy_ship_dict[ship.id] in fc.closest_enemy_ships:
            # if enemy is still alive
            navigation.attack(ship, fc.ship_enemy_ship_dict[ship.id], fc)
        else:
            # that assigned enemy is not alive anymore
            if fc.ship_enemy_ship_dict[ship.id].id in fc.kamikaze_assignment_enemy:
                fc.unassign_kamikaze_enemy(fc.ship_enemy_ship_dict[ship.id].id)
                fc.unassign_ship_as_kamikaze(ship.id)
            fc.unassign_ship(ship.id)
            fc.unassign_enemy(fc.ship_enemy_ship_dict[ship.id].id)
            fc.unassign_enemy_ship_to_ship(ship.id)
            standard_strategy(ship, fc)

    # Strategy for ship assigned to planets
    elif fc.assigned_ships[ship.id] == "planet":
        if ship.docking_status != ship.DockingStatus.UNDOCKED:
            # Undocking when planet has no resources anymore (ruled by flag in my_const)
            if (ship.docking_status == ship.DockingStatus.DOCKED) and (
                    fc.game_map.get_planet(
                        fc.ship_planet_dict[
                            ship.id].id).remaining_resources <= 0) and my_const.UNDOCK_IF_PLANET_DEPLETED:
                fc.unassign_ship(ship.id)
                fc.unassign_planet_to_ship(ship.id)
                fc.command_queue.append(ship.undock())
                # Not unassigning planet to prevent new ships from docking with depleted planet

        elif fc.closest_enemy_ships_distances[0] < my_const.RANGE_OF_AGGRESSION:
            # if assigned to planet, but enemies are close - attack them!
            fc.unassign_ship(ship.id)
            fc.unassign_planet(fc.ship_planet_dict[ship.id].id)
            fc.unassign_planet_to_ship(ship.id)
            navigation.attack_and_assign(ship, fc.closest_enemy_ships[0], fc)
        else:
            if ship.can_dock(fc.ship_planet_dict[ship.id]):
                fc.command_queue.append(ship.dock(fc.ship_planet_dict[ship.id]))
            else:
                navigation.go_to_planet(ship, fc.ship_planet_dict[ship.id], fc)
    else:
        # maybe add "defender" role
        pass


def rush_strategy(ship: hlt.entity.Ship, fc: FeatureCollector):
    """
    Behavior of a ship, if rush mode is on. Depends on the number of players.
    Can be 2-players game (duel) OR 4-players game (ffa).

    Docked ships need to undock. Undocked ships need to unite and attack together.
    Using some Halite II tricks while docking/undocking to do it faster.

    To keep ships close to each other, there is rush leader modeling feature. Rush leader is allied ship,
    closest to enemy. All ships are moving with same speed and angle as rush leader. This allow to achieve
    swarm effect.

    :param ship: Allied ship
    :param fc: Feature collector class instance

    """
    # 4 PLAYERS RUSH
    if len(fc.players) > 2:
        # logging.info("RUSH DETECTED ffa")
        """
        Players are farther away from each other comparing to duel games. For that reason, one ship
        will be mining resources, while other two will defend him (by attacking closest enemy) if rush detected.
        """
        # Rush miner is not affected by these rules. It is mining resources no matter what.
        if ship.id != fc.rush_miner.id:
            if ship.docking_status == ship.DockingStatus.DOCKED:
                fc.command_queue.append(ship.undock())
            elif ship.docking_status == ship.DockingStatus.UNDOCKED:
                fc.rush_leader = [ship for ship in fc.sorted_ships_from_enemy(fc.closest_enemy_ships[0]) if
                                  ship.id != fc.rush_miner.id][0]

                distances = [ship.calculate_distance_between(target) for target in fc.team_ships if
                             (target.id != ship.id) and (target.id != fc.rush_miner.id)]

                # Ships need to be close to each other for more efficient defence.
                # If already close - move on next turn.
                if (len(distances) > 0) and (max(distances) <= my_const.RUSH_READY_RADIUS):
                    fc.ready_for_rush.update({ship.id: 1})

                if not fc.go_rush and (len(fc.ready_for_rush) == (len(fc.team_ships) - 1)):
                    fc.rush_ready_turn = fc.turn
                    fc.go_rush = True

                if fc.go_rush:
                    # Unite, if ships are far from each other
                    if (len(distances) > 0) and (max(distances) > my_const.RUSH_READY_RADIUS):
                        navigation.unite_for_rush(ship, fc.center_of_mass(exclude=fc.rush_miner), fc)
                    # Swarm by rush leader modeling
                    elif (fc.turn > fc.rush_ready_turn) and len(fc.team_ships) > 1:
                        if not fc.rush_leader_modelled:
                            speed, angle = navigation.rush_leader_modeling(fc.rush_leader,
                                                                           fc.closest_enemy_ships[0], fc)
                            if speed is not None:
                                fc.rush_leader_move.extend([speed, angle])
                                fc.command_queue.append(ship.thrust(speed, angle))
                                fc.rush_leader_modelled = True
                        else:
                            fc.command_queue.append(ship.thrust(fc.rush_leader_move[0], fc.rush_leader_move[1]))
                    elif fc.turn > fc.rush_ready_turn:
                        navigation.rush_attack(ship, fc.closest_enemy_ships[0], fc)
                else:
                    docked = [ship for ship in fc.team_ships if ship.docking_status != ship.DockingStatus.UNDOCKED]
                    if (len(distances) > 0) and (max(distances) < hlt.constants.MAX_SPEED * 2) and (docked != []):
                        pass
                    else:
                        navigation.unite_for_rush(ship, fc.center_of_mass(exclude=fc.rush_miner), fc)

            # Win 1 step by thrust on the last step of undocking process
            elif ship.docking_status == ship.DockingStatus.UNDOCKING:
                angle = (180 + round(ship.calculate_angle_between(fc.closest_my_planets[0]))) % 360
                navigation_command = navigation.undocking_thrust(ship, fc.closest_my_planets[0], fc,
                                                                 initial_angle=angle)
                if navigation_command is not None:
                    fc.command_queue.append(navigation_command)
            elif ship.docking_status == ship.DockingStatus.DOCKING:
                fc.command_queue.append(ship.undock())
        else:
            if ship.id in fc.assigned_ships:
                strategy_if_assigned(ship, fc)
            else:
                standard_strategy(ship, fc)

    # 2 PLAYERS RUSH
    else:
        # logging.info("\n\nRUSH DETECTED duel")
        if ship.docking_status == ship.DockingStatus.DOCKED:
            fc.command_queue.append(ship.undock())
        elif ship.docking_status == ship.DockingStatus.UNDOCKED:
            fc.rush_leader = fc.sorted_ships_from_enemy(fc.closest_enemy_ships[0])[0]

            distances = [ship.calculate_distance_between(target) for target in fc.team_ships if
                         target.id != ship.id]

            # Ships need to be close to each other for more efficient defence.
            # If already close - move on next turn.
            if (len(distances) > 0) and (max(distances) <= my_const.RUSH_READY_RADIUS):
                fc.ready_for_rush.update({ship.id: 1})

            if not fc.go_rush and (len(fc.ready_for_rush) == len(fc.team_ships)):
                fc.rush_ready_turn = fc.turn
                fc.go_rush = True

            if fc.go_rush:
                # Unite, if ships are far from each other
                if (len(distances) > 0) and (max(distances) > my_const.RUSH_READY_RADIUS):
                    navigation.unite_for_rush(ship, fc.center_of_mass(), fc)

                # Swarm by rush leader modeling
                elif (fc.turn > fc.rush_ready_turn) and len(fc.team_ships) > 1:
                    if not fc.rush_leader_modelled:
                        if (fc.closest_enemy_ships_distances[0] > hlt.constants.MAX_SPEED * 2 + 4) or \
                                (fc.closest_enemy_ships[0].docking_status != ship.DockingStatus.UNDOCKED):
                            speed, angle = navigation.rush_leader_modeling(fc.rush_leader,
                                                                           fc.closest_enemy_ships[0], fc)
                        else:
                            min_distance = hlt.constants.MAX_SPEED + 4
                            speed, angle = navigation.rush_leader_modeling(fc.rush_leader,
                                                                           fc.closest_enemy_ships[0],
                                                                           fc, dist=min_distance)
                        if speed is not None:
                            fc.rush_leader_move.extend([speed, angle])
                            fc.command_queue.append(ship.thrust(speed, angle))
                            fc.rush_leader_modelled = True
                    else:
                        fc.command_queue.append(ship.thrust(fc.rush_leader_move[0], fc.rush_leader_move[1]))
                elif fc.turn > fc.rush_ready_turn:
                    navigation.rush_attack(ship, fc.closest_enemy_ships[0], fc)
            else:
                docked = [ship for ship in fc.team_ships if ship.docking_status != ship.DockingStatus.UNDOCKED]
                if (len(distances) > 0) and (max(distances) < hlt.constants.MAX_SPEED * 2) and (docked != []):
                    pass
                else:
                    navigation.unite_for_rush(ship, fc.center_of_mass(), fc)

        # Win 1 step by thrust on the last step of undocking process
        elif ship.docking_status == ship.DockingStatus.UNDOCKING:
            angle = (180 + round(ship.calculate_angle_between(fc.closest_my_planets[0]))) % 360
            navigation_command = navigation.undocking_thrust(ship, fc.closest_my_planets[0], fc,
                                                             initial_angle=angle)
            if navigation_command is not None:
                fc.command_queue.append(navigation_command)
        elif ship.docking_status == ship.DockingStatus.DOCKING:
            fc.command_queue.append(ship.undock())
