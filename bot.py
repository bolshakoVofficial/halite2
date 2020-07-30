import hlt
import logging
from collections import OrderedDict
import numpy as np

game = hlt.Game("MyBot")
turn_number = 0
rush = False

while True:
    game_map = game.update_map()
    command_queue = []
    my_slots = 0

    team_ships = game_map.get_me().all_ships()
    enemy_ships = [ship for ship in game_map._all_ships() if ship not in team_ships]

    my_ships_count = len(team_ships)
    enemy_ships_count = len(enemy_ships)

    logging.info(rush)

    # RUSH
    if turn_number < 5 or rush:
        for ship in game_map.get_me().all_ships():
            entities_by_distance = game_map.nearby_entities_by_distance(ship)
            entities_by_distance = OrderedDict(sorted(entities_by_distance.items(), key=lambda t: t[0]))

            closest_empty_planets = [entities_by_distance[distance][0] for distance in entities_by_distance if
                                     isinstance(entities_by_distance[distance][0], hlt.entity.Planet) and not
                                     entities_by_distance[distance][0].is_owned()]
            closest_empty_planets_distances = [distance for distance in entities_by_distance if
                                               isinstance(entities_by_distance[distance][0], hlt.entity.Planet) and not
                                               entities_by_distance[distance][0].is_owned()]

            closest_enemy_ships = [entities_by_distance[distance][0] for distance in entities_by_distance if
                                   isinstance(entities_by_distance[distance][0], hlt.entity.Ship) and
                                   entities_by_distance[distance][0] not in team_ships]
            closest_enemy_ships_distances = [distance for distance in entities_by_distance if
                                             isinstance(entities_by_distance[distance][0], hlt.entity.Ship) and
                                             entities_by_distance[distance][0] not in team_ships]

            if ((closest_empty_planets_distances[0] + 40) > closest_enemy_ships_distances[0]) or rush:
                rush = True
                navigate_command = ship.navigate(
                    ship.closest_point_to(closest_enemy_ships[0]),
                    game_map,
                    speed=int(hlt.constants.MAX_SPEED))

                if navigate_command:
                    command_queue.append(navigate_command)
        if rush:
            turn_number += 1
            game.send_command_queue(command_queue)
            continue
        # TURN END

    for ship in game_map.get_me().all_ships():
        if ship.docking_status != ship.DockingStatus.UNDOCKED:
            continue

        entities_by_distance = game_map.nearby_entities_by_distance(ship)
        entities_by_distance = OrderedDict(sorted(entities_by_distance.items(), key=lambda t: t[0]))

        closest_empty_planets = [entities_by_distance[distance][0] for distance in entities_by_distance if
                                 isinstance(entities_by_distance[distance][0], hlt.entity.Planet) and not
                                 entities_by_distance[distance][0].is_owned()]
        closest_empty_planets_distances = [distance for distance in entities_by_distance if
                                           isinstance(entities_by_distance[distance][0], hlt.entity.Planet) and not
                                           entities_by_distance[distance][0].is_owned()]

        closest_my_planets = [entities_by_distance[distance][0] for distance in entities_by_distance if
                              isinstance(entities_by_distance[distance][0], hlt.entity.Planet) and
                              entities_by_distance[distance][0].is_owned() and (
                                      entities_by_distance[distance][0].owner.id == game_map.get_me().id)]
        closest_my_planets_distances = [distance for distance in entities_by_distance if
                                        isinstance(entities_by_distance[distance][0], hlt.entity.Planet) and
                                        entities_by_distance[distance][0].is_owned() and (
                                                entities_by_distance[distance][
                                                    0].owner.id == game_map.get_me().id)]

        closest_enemy_planets = [entities_by_distance[distance][0] for distance in entities_by_distance if
                                 isinstance(entities_by_distance[distance][0], hlt.entity.Planet) and
                                 entities_by_distance[distance][0] not in closest_my_planets and
                                 entities_by_distance[distance][0] not in closest_empty_planets]
        closest_enemy_planets_distances = [distance for distance in entities_by_distance if
                                           isinstance(entities_by_distance[distance][0], hlt.entity.Planet) and
                                           entities_by_distance[distance][0] not in closest_my_planets and
                                           entities_by_distance[distance][0] not in closest_empty_planets]

        closest_team_ships = [entities_by_distance[distance][0] for distance in entities_by_distance if
                              isinstance(entities_by_distance[distance][0], hlt.entity.Ship) and
                              entities_by_distance[distance][0] in team_ships]
        closest_team_ships_distances = [distance for distance in entities_by_distance if
                                        isinstance(entities_by_distance[distance][0], hlt.entity.Ship) and
                                        entities_by_distance[distance][0] in team_ships]

        closest_enemy_ships = [entities_by_distance[distance][0] for distance in entities_by_distance if
                               isinstance(entities_by_distance[distance][0], hlt.entity.Ship) and
                               entities_by_distance[distance][0] not in team_ships]
        closest_enemy_ships_distances = [distance for distance in entities_by_distance if
                                         isinstance(entities_by_distance[distance][0], hlt.entity.Ship) and
                                         entities_by_distance[distance][0] not in team_ships]

        for planet in closest_my_planets:
            if not planet.is_full():
                my_slots += 1

        # ATTACK IF ENEMY IS CLOSE
        if closest_enemy_ships_distances[0] < 20:
            navigate_command = ship.navigate(
                ship.closest_point_to(closest_enemy_ships[0]),
                game_map,
                speed=int(hlt.constants.MAX_SPEED))

            if navigate_command:
                command_queue.append(navigate_command)

        # ATTACK IF CONFIDENT OF WINNING
        elif ((len(team_ships) >= 30) and (len(team_ships) >= len(enemy_ships) * 2)) or \
                (len(team_ships) >= len(enemy_ships) * 4):
            if not isinstance(closest_enemy_ships[0], int):
                navigate_command = ship.navigate(
                    ship.closest_point_to(closest_enemy_ships[0]),
                    game_map,
                    speed=int(hlt.constants.MAX_SPEED))

                if navigate_command:
                    command_queue.append(navigate_command)

        # MINE IF SLOT EXIST OR EXPAND AGGRESSIVELY
        elif (my_slots > 0) and (len(closest_enemy_planets) > 0) and (len(closest_empty_planets) > 0):
            is_enemy_closer = False
            for planet in closest_my_planets:
                if (not planet.is_full()) and \
                        (ship.calculate_distance_between(planet) < closest_enemy_planets_distances[0]) and \
                        (ship.calculate_distance_between(planet) < closest_empty_planets_distances[0]):
                    if ship.can_dock(planet):
                        command_queue.append(ship.dock(planet))
                    else:
                        navigate_command = ship.navigate(
                            ship.closest_point_to(planet),
                            game_map,
                            speed=int(hlt.constants.MAX_SPEED))

                        if navigate_command:
                            command_queue.append(navigate_command)
                    is_enemy_closer = False
                    break

                elif closest_empty_planets_distances[0] < closest_enemy_planets_distances[0]:
                    if ship.can_dock(closest_empty_planets[0]):
                        command_queue.append(ship.dock(closest_empty_planets[0]))
                    else:
                        navigate_command = ship.navigate(
                            ship.closest_point_to(closest_empty_planets[0]),
                            game_map,
                            speed=int(hlt.constants.MAX_SPEED))

                        if navigate_command:
                            command_queue.append(navigate_command)
                    is_enemy_closer = False
                    break
                else:
                    is_enemy_closer = True

            if is_enemy_closer:
                navigate_command = ship.navigate(
                    ship.closest_point_to(closest_enemy_ships[0]),
                    game_map,
                    speed=int(hlt.constants.MAX_SPEED))

                if navigate_command:
                    command_queue.append(navigate_command)

        # MINE IF SLOT EXIST
        elif (my_slots > 0) and (len(closest_empty_planets) > 0):
            for planet in closest_my_planets:
                if (not planet.is_full()) and \
                        (ship.calculate_distance_between(planet) < closest_empty_planets_distances[0]):
                    if ship.can_dock(planet):
                        command_queue.append(ship.dock(planet))
                    else:
                        navigate_command = ship.navigate(
                            ship.closest_point_to(planet),
                            game_map,
                            speed=int(hlt.constants.MAX_SPEED))

                        if navigate_command:
                            command_queue.append(navigate_command)
                    break

        # EXPAND AGGRESSIVELY
        elif (len(closest_empty_planets) > 0) and (len(closest_enemy_planets) > 0):
            gambit_distance = 20

            if closest_empty_planets_distances[0] < closest_enemy_planets_distances[0]:

                if len(closest_empty_planets) > 2:
                    if (closest_empty_planets[0].num_docking_spots < closest_empty_planets[1].num_docking_spots) and \
                            (closest_empty_planets_distances[0] > (
                                    closest_empty_planets_distances[1] - gambit_distance)) and \
                            (closest_empty_planets[0].num_docking_spots < 3):
                        nearest_planet = closest_empty_planets[1]
                    elif (closest_empty_planets[0].num_docking_spots < closest_empty_planets[2].num_docking_spots) and \
                            (closest_empty_planets_distances[0] > (
                                    closest_empty_planets_distances[2] - gambit_distance)) and \
                            (closest_empty_planets[0].num_docking_spots < 3):
                        nearest_planet = closest_empty_planets[2]
                    else:
                        nearest_planet = closest_empty_planets[0]
                elif len(closest_empty_planets) > 1:
                    if (closest_empty_planets[0].num_docking_spots < closest_empty_planets[1].num_docking_spots) and \
                            (closest_empty_planets_distances[0] > (
                                    closest_empty_planets_distances[1] - gambit_distance)) and \
                            (closest_empty_planets[0].num_docking_spots < 3):
                        nearest_planet = closest_empty_planets[1]
                    else:
                        nearest_planet = closest_empty_planets[0]
                else:
                    nearest_planet = closest_empty_planets[0]

                if ship.can_dock(nearest_planet):
                    command_queue.append(ship.dock(nearest_planet))
                else:
                    logging.info("closest_empty_planets: " + str(closest_empty_planets))
                    logging.info("closest_empty_planets_distances: " + str(closest_empty_planets_distances))
                    navigate_command = ship.navigate(
                        ship.closest_point_to(nearest_planet),
                        game_map,
                        speed=int(hlt.constants.MAX_SPEED))

                    if navigate_command:
                        command_queue.append(navigate_command)
            else:
                navigate_command = ship.navigate(
                    ship.closest_point_to(closest_enemy_ships[0]),
                    game_map,
                    speed=int(hlt.constants.MAX_SPEED))

                if navigate_command:
                    command_queue.append(navigate_command)

        # EXPAND ON EMPTY PLANETS
        elif len(closest_empty_planets) > 0:
            gambit_distance = 20

            if len(closest_empty_planets) > 2:
                if (closest_empty_planets[0].num_docking_spots < closest_empty_planets[1].num_docking_spots) and \
                        (closest_empty_planets_distances[0] > (
                                closest_empty_planets_distances[1] - gambit_distance)) and \
                        (closest_empty_planets[0].num_docking_spots < 3):
                    nearest_planet = closest_empty_planets[1]
                elif (closest_empty_planets[0].num_docking_spots < closest_empty_planets[2].num_docking_spots) and \
                        (closest_empty_planets_distances[0] > (
                                closest_empty_planets_distances[2] - gambit_distance)) and \
                        (closest_empty_planets[0].num_docking_spots < 3):
                    nearest_planet = closest_empty_planets[2]
                else:
                    nearest_planet = closest_empty_planets[0]
            elif len(closest_empty_planets) > 1:
                if (closest_empty_planets[0].num_docking_spots < closest_empty_planets[1].num_docking_spots) and \
                        (closest_empty_planets_distances[0] > (
                                closest_empty_planets_distances[1] - gambit_distance)) and \
                        (closest_empty_planets[0].num_docking_spots < 3):
                    nearest_planet = closest_empty_planets[1]
                else:
                    nearest_planet = closest_empty_planets[0]
            else:
                nearest_planet = closest_empty_planets[0]

            if ship.can_dock(nearest_planet):
                command_queue.append(ship.dock(nearest_planet))
            else:
                navigate_command = ship.navigate(
                    ship.closest_point_to(nearest_planet),
                    game_map,
                    speed=int(hlt.constants.MAX_SPEED))

                if navigate_command:
                    command_queue.append(navigate_command)

        # ATTACK IF NOTHING ELSE
        else:
            if not isinstance(closest_enemy_ships[0], int):
                navigate_command = ship.navigate(
                    ship.closest_point_to(closest_enemy_ships[0]),
                    game_map,
                    speed=int(hlt.constants.MAX_SPEED))

                if navigate_command:
                    command_queue.append(navigate_command)

    turn_number += 1
    game.send_command_queue(command_queue)
    # TURN END
# GAME END
