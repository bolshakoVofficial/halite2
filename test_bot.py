import hlt
import logging
from collections import OrderedDict

game = hlt.Game("TestBot")
logging.info("Starting TestBot")
turn_number = 0
our_player_id = None

while True:
    game_map = game.update_map()
    command_queue = []
    our_player_id = game_map.get_me().id

    team_ships = game_map.get_me().all_ships()
    number_of_enemy_ships = 0

    # print debugging stuff each turn
    logging.info("Turn number: " + str(turn_number))
    logging.info("Number of planets: " + str(len(game_map.all_planets())))
    logging.info("Number of my ships: " + str(len(team_ships)))

    for ship in team_ships:
        # shipid = ship.id

        if ship.docking_status != ship.DockingStatus.UNDOCKED:
            # if it is docked then skip it
            continue

        # get a list of entities in relation to our ship, then order it by that distance
        entities_by_distance = game_map.nearby_entities_by_distance(ship)
        entities_by_distance = OrderedDict(sorted(entities_by_distance.items(), key=lambda t: t[0]))

        # iterate over the entities by distance
        # we make sure its a planet, and that its unowned
        # if that's the case then build a list in order of the distance
        closest_empty_planets = [entities_by_distance[distance][0] for distance in entities_by_distance if
                                 isinstance(entities_by_distance[distance][0], hlt.entity.Planet) and not
                                 entities_by_distance[distance][0].is_owned()]

        # if the entity is a ship, but not ours
        closest_enemy_ships = [entities_by_distance[distance][0] for distance in entities_by_distance if
                               isinstance(entities_by_distance[distance][0], hlt.entity.Ship) and not
                               entities_by_distance[distance][0] in team_ships]

        # if (planet.owner.id == game_map.get_me().id)

        # find out if the closest planet is owned by us
        closest_owned_planets = [entities_by_distance[distance][0] for distance in entities_by_distance if
                                 isinstance(entities_by_distance[distance][0], hlt.entity.Planet) and
                                 entities_by_distance[distance][0].is_owned()]

        closest_planets_we_own = []

        for planet in closest_owned_planets:
            if planet.owner.id == our_player_id:
                closest_planets_we_own.append(planet)

        number_of_empty_planets = len(closest_empty_planets)
        number_of_enemy_ships = len(closest_enemy_ships)
        number_of_planets_we_own = len(closest_planets_we_own)

        # logging.info("We own this many planets: " + str(number_of_planets_we_own))

        # calc distance between this ship and the nearest empty planet
        # then calc the distance between this ship and the nearest enemy ship
        # if the enemy ship is less than 1/3rd the distance that an empty planet would be, instead attack that ship
        distance_factor = .5

        # if we are really close to a planet we own that is not full, then dock there
        closest_unfull_planets_we_own = []
        for planet in closest_planets_we_own:
            if not planet.is_full():
                closest_unfull_planets_we_own.append(planet)

        if len(closest_unfull_planets_we_own) > 0:
            closest_unfull_planet_we_own = closest_unfull_planets_we_own[0]

            if number_of_enemy_ships > 0:
                closest_enemy_ship = closest_enemy_ships[0]
                distance_between_ship_and_enemy_ship = ship.calculate_distance_between(closest_enemy_ship)

                if distance_between_ship_and_enemy_ship < 20:
                    # navigate towards that enemy ship
                    navigate_command = ship.navigate(
                        ship.closest_point_to(closest_enemy_ship),
                        game_map,
                        speed=int(hlt.constants.MAX_SPEED),
                        ignore_ships=False
                    )

                    if navigate_command:
                        command_queue.append(navigate_command)
                        continue
                else:
                    if ship.can_dock(closest_unfull_planet_we_own):
                        command_queue.append(ship.dock(closest_unfull_planet_we_own))
                        continue

        # if there's at least 1 empty planet
        if number_of_empty_planets > 0 and number_of_enemy_ships > 0:
            closest_empty_planet = closest_empty_planets[0]
            # if our ship can dock just go ahead and do it
            if ship.can_dock(closest_empty_planet):
                command_queue.append(ship.dock(closest_empty_planet))
                continue

            # get the distance between this ship and that planet
            distance_between_ship_and_empty_planet = ship.calculate_distance_between(closest_empty_planet)
            # logging.info("Distance between ship id " + str(ship.id) + " and nearest empty planet (id " + str(closest_empty_planet.id) + ") is: " + str(distance_between_ship_and_empty_planet))

            # get the distance between this ship and the nearest enemy ship
            closest_enemy_ship = closest_enemy_ships[0]
            distance_between_ship_and_enemy_ship = ship.calculate_distance_between(closest_enemy_ship)
            # logging.info("Distance between ship id " + str(ship.id) + " and nearest enemy ship (id " + str(closest_enemy_ship.id) + ") is: " + str(distance_between_ship_and_enemy_ship))

            # if the distance between us and an empty planet is 3x greater than the distance between us and an enemy ship, let's choose the ship
            if distance_between_ship_and_enemy_ship < (distance_between_ship_and_empty_planet * distance_factor):
                # logging.info("We are now 3x closer to an enemy ship than an empty planet. Go to the ship instead.")

                # navigate towards that enemy ship
                navigate_command = ship.navigate(
                    ship.closest_point_to(closest_enemy_ship),
                    game_map,
                    speed=int(hlt.constants.MAX_SPEED),
                    ignore_ships=False
                )

                if navigate_command:
                    command_queue.append(navigate_command)

            else:
                # navigate towards the empty planet
                navigate_command = ship.navigate(
                    ship.closest_point_to(closest_empty_planet),
                    game_map,
                    speed=int(hlt.constants.MAX_SPEED),
                    ignore_ships=False
                )

                if navigate_command:
                    command_queue.append(navigate_command)

        elif number_of_enemy_ships > 0:
            # if there are no empty planets, just move to the nearest enemy ship
            closest_enemy_ship = closest_enemy_ships[0]

            navigate_command = ship.navigate(
                ship.closest_point_to(closest_enemy_ship),
                game_map,
                speed=int(hlt.constants.MAX_SPEED),
                ignore_ships=False
            )

            if navigate_command:
                command_queue.append(navigate_command)

    logging.info("Number of enemy ships: " + str(number_of_enemy_ships))
    turn_number += 1
    game.send_command_queue(command_queue)
    # turn end
# game end
