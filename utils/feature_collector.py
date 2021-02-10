from collections import OrderedDict
import logging
import hlt
import utils.constants as my_const


class FeatureCollector:
    """
    Class for collecting all kinds of features of game map, including handcrafted ones.

    :ivar turn: Turn of a game
    :ivar players: List of participants (might be 2 or 4 players)
    :ivar assigned_ships: Dict of type {id: "planet"} OR {id: "enemy"}
    :ivar assigned_to_enemy: Dict of type {enemy_id: int how many allied ships assigned}
    :ivar ship_enemy_ship_dict: Dict of type {ship_id: enemy_ship}
    :ivar assigned_to_planet: Dict of type {planet_id: int how many ally ships assigned}
    :ivar ship_planet_dict: Dict of type {ship_id: planet}
    :ivar kamikaze_assignment_enemy: Dict of type {enemy_id: int how many of my ships assigned}
    :ivar kamikaze_assign_ship: Dict of type {ship_id: enemy}
    :ivar ready_for_rush: Dict of type {ship_id: meaningless number}
    :ivar go_rush: Flag indicating that ships are ready for rush
    :ivar rush_ready_turn: Turn of the game, when ships were ready for rush for the first time
    :ivar rush_miner: Allied ship with role "rush miner"
    :ivar rush_leader: Allied ship that is closest to enemy while rushing
    :ivar rush_leader_modelled: Flag indicating whether rush leader movement was modelled
    :ivar rush_leader_move: List with information about speed and angle (in this order)
    """

    def __init__(self):
        self.turn = -1
        self.players = []
        self.assigned_ships = {}
        self.assigned_to_enemy = {}
        self.ship_enemy_ship_dict = {}
        self.assigned_to_planet = {}
        self.ship_planet_dict = {}
        self.kamikaze_assignment_enemy = {}
        self.kamikaze_assign_ship = {}

        self.ready_for_rush = {}
        self.go_rush = False
        self.rush_ready_turn = 300
        self.rush_miner = None
        self.rush_leader = None
        self.rush_leader_modelled = False
        self.rush_leader_move = []

    # noinspection PyAttributeOutsideInit
    def iterate_turn(self, game_map: hlt.game_map):
        """
        This should be used at the beginning of every turn of the game. This updates info about assignments,
        ships in the game, iterates turn number. Clears info about previous moves in move table and command queue.

        :param game_map: hlt.game_map
        """
        self.turn += 1
        self.game_map = game_map
        self.move_table = {}
        self.command_queue = []
        self.players = self.game_map.all_players()

        self.team_ships = self.game_map.get_me().all_ships()
        self.enemy_ships = [ship for ship in self.game_map._all_ships() if ship not in self.team_ships]

        self.my_ships_count = len(self.team_ships)
        self.enemy_ships_count = len(self.enemy_ships)

        self.update_assignments()
        self.rush_leader_modelled = False
        self.rush_leader_move = []
        if self.rush_leader is not None:
            # to update the position of rush leader
            self.rush_leader = self.game_map.get_me().get_ship(self.rush_leader.id)

    # noinspection PyAttributeOutsideInit
    def collect(self, ship: hlt.entity.Ship):
        """
        Works on per-ship basis. For a ship collects info about distances to entities, sorts entities by distance.
        Collects info about allied and enemy entities: planets, ships.

        :param ship: Allied ship
        """
        self.entities_by_distance = self.game_map.nearby_entities_by_distance(ship)
        self.entities_by_distance = OrderedDict(sorted(self.entities_by_distance.items(), key=lambda t: t[0]))

        self.closest_empty_planets = [self.entities_by_distance[distance][0] for distance in
                                      self.entities_by_distance if
                                      isinstance(self.entities_by_distance[distance][0], hlt.entity.Planet) and not
                                      self.entities_by_distance[distance][0].is_owned()]

        self.closest_empty_planets_distances = [distance for distance in self.entities_by_distance if
                                                isinstance(self.entities_by_distance[distance][0],
                                                           hlt.entity.Planet) and not
                                                self.entities_by_distance[distance][0].is_owned()]

        self.closest_not_my_planets = [self.entities_by_distance[distance][0] for distance in self.entities_by_distance
                                       if
                                       (isinstance(self.entities_by_distance[distance][0], hlt.entity.Planet) and
                                        self.entities_by_distance[distance][0].is_owned() and
                                        (self.entities_by_distance[distance][
                                             0].owner.id != self.game_map.get_me().id)) or
                                       (isinstance(self.entities_by_distance[distance][0], hlt.entity.Planet) and not
                                       self.entities_by_distance[distance][0].is_owned())]

        self.closest_not_my_planets_distances = [distance for distance in self.entities_by_distance if
                                                 (isinstance(self.entities_by_distance[distance][0],
                                                             hlt.entity.Planet) and
                                                  self.entities_by_distance[distance][0].is_owned() and
                                                  (self.entities_by_distance[distance][
                                                       0].owner.id != self.game_map.get_me().id)) or
                                                 (isinstance(self.entities_by_distance[distance][0],
                                                             hlt.entity.Planet) and not
                                                  self.entities_by_distance[distance][0].is_owned())]

        self.closest_not_enemy_planets = [self.entities_by_distance[distance][0] for distance in
                                          self.entities_by_distance
                                          if
                                          (isinstance(self.entities_by_distance[distance][0], hlt.entity.Planet) and
                                           self.entities_by_distance[distance][0].is_owned() and
                                           (self.entities_by_distance[distance][
                                                0].owner.id == self.game_map.get_me().id)) or
                                          (isinstance(self.entities_by_distance[distance][0], hlt.entity.Planet) and not
                                          self.entities_by_distance[distance][0].is_owned())]

        self.closest_not_enemy_planets_distances = [distance for distance in self.entities_by_distance if
                                                    (isinstance(self.entities_by_distance[distance][0],
                                                                hlt.entity.Planet) and
                                                     self.entities_by_distance[distance][0].is_owned() and
                                                     (self.entities_by_distance[distance][
                                                          0].owner.id == self.game_map.get_me().id)) or
                                                    (isinstance(self.entities_by_distance[distance][0],
                                                                hlt.entity.Planet) and not
                                                     self.entities_by_distance[distance][0].is_owned())]

        self.closest_my_planets = [self.entities_by_distance[distance][0] for distance in self.entities_by_distance
                                   if isinstance(self.entities_by_distance[distance][0], hlt.entity.Planet) and
                                   self.entities_by_distance[distance][0].is_owned() and (
                                           self.entities_by_distance[distance][
                                               0].owner.id == self.game_map.get_me().id)]

        self.closest_my_planets_distances = [distance for distance in self.entities_by_distance if
                                             isinstance(self.entities_by_distance[distance][0],
                                                        hlt.entity.Planet) and
                                             self.entities_by_distance[distance][0].is_owned() and (
                                                     self.entities_by_distance[distance][
                                                         0].owner.id == self.game_map.get_me().id)]

        self.closest_enemy_ships = [self.entities_by_distance[distance][0] for distance in self.entities_by_distance
                                    if isinstance(self.entities_by_distance[distance][0], hlt.entity.Ship) and
                                    self.entities_by_distance[distance][0] not in self.team_ships]

        self.closest_enemy_ships_distances = [distance for distance in self.entities_by_distance if
                                              isinstance(self.entities_by_distance[distance][0],
                                                         hlt.entity.Ship) and
                                              self.entities_by_distance[distance][0] not in self.team_ships]

        self.closest_enemy_planets = [self.entities_by_distance[distance][0] for distance in
                                      self.entities_by_distance if
                                      isinstance(self.entities_by_distance[distance][0], hlt.entity.Planet) and
                                      self.entities_by_distance[distance][0] not in self.closest_my_planets and
                                      self.entities_by_distance[distance][0] not in self.closest_empty_planets]

        self.closest_enemy_planets_distances = [distance for distance in self.entities_by_distance if
                                                isinstance(self.entities_by_distance[distance][0],
                                                           hlt.entity.Planet) and
                                                self.entities_by_distance[distance][
                                                    0] not in self.closest_my_planets and
                                                self.entities_by_distance[distance][
                                                    0] not in self.closest_empty_planets]

    # how many of my attackers assigned to this enemy
    def assign_enemy(self, enemy_id):
        self.assigned_to_enemy[enemy_id] = self.assigned_to_enemy.get(enemy_id, 0) + 1

    def unassign_enemy(self, enemy_id):
        if enemy_id in self.assigned_to_enemy and self.assigned_to_enemy[enemy_id] > 0:
            self.assigned_to_enemy[enemy_id] -= 1
        else:
            del self.assigned_to_enemy[enemy_id]

    # assign ship on one of two (bot_v1): "ship" or "planet"
    def assign_ship(self, ship_id, str_entity):
        self.assigned_ships[ship_id] = str_entity

    def unassign_ship(self, ship_id):
        if ship_id in self.assigned_ships:
            del self.assigned_ships[ship_id]

    # assign my ship to specific enemy
    def assign_enemy_ship_to_ship(self, ship_id, enemy_ship: hlt.entity.Ship):
        self.ship_enemy_ship_dict[ship_id] = enemy_ship

    def unassign_enemy_ship_to_ship(self, ship_id):
        if ship_id in self.ship_enemy_ship_dict:
            del self.ship_enemy_ship_dict[ship_id]

    # assign my ship to planet
    def assign_planet_to_ship(self, ship_id, planet: hlt.entity.Planet):
        self.ship_planet_dict[ship_id] = planet

    def unassign_planet_to_ship(self, ship_id):
        if ship_id in self.ship_planet_dict:
            del self.ship_planet_dict[ship_id]

    # how many of my miners assigned to this planet
    def assign_planet(self, planet_id):
        self.assigned_to_planet[planet_id] = self.assigned_to_planet.get(planet_id, 0) + 1

    def unassign_planet(self, planet_id):
        if planet_id in self.assigned_to_planet and self.assigned_to_planet[planet_id] > 0:
            self.assigned_to_planet[planet_id] -= 1
        if planet_id in self.assigned_to_planet and self.assigned_to_planet[planet_id] == 0:
            del self.assigned_to_planet[planet_id]

    # how many allied ships assigned to this enemy
    def assign_kamikaze_enemy(self, enemy_id):
        self.kamikaze_assignment_enemy[enemy_id] = self.kamikaze_assignment_enemy.get(enemy_id, 0) + 1

    def unassign_kamikaze_enemy(self, enemy_id):
        if enemy_id in self.kamikaze_assignment_enemy and self.kamikaze_assignment_enemy[enemy_id] > 0:
            self.kamikaze_assignment_enemy[enemy_id] -= 1
        if enemy_id in self.kamikaze_assignment_enemy and self.kamikaze_assignment_enemy[enemy_id] == 0:
            del self.kamikaze_assignment_enemy[enemy_id]

    # assign low hp allied ship to enemy for mutual destruction
    def assign_ship_as_kamikaze(self, ship_id, enemy: hlt.entity.Ship):
        self.kamikaze_assign_ship[ship_id] = enemy

    def unassign_ship_as_kamikaze(self, ship_id):
        if ship_id in self.kamikaze_assign_ship:
            del self.kamikaze_assign_ship[ship_id]

    def closest_not_assigned_enemy(self, ship: hlt.entity.Ship, num_ships):
        pass

    def closest_avail_assigned_planet(self):
        """
        In list of assigned planets does "greedy" search for ones with (num_docking_spots > assigned_to_planet)

        :return: Closest assigned planet with free docking spots
        :rtype: hlt.entities.Planet of None
        """
        planets_distances = zip(self.closest_not_enemy_planets, self.closest_not_enemy_planets_distances)

        # assigned_pd = [(planet, distance), (planet, distance), ...]
        assigned_pd = [planet for planet in planets_distances if
                       planet[0].id in self.assigned_to_planet and
                       (planet[0].num_docking_spots > self.assigned_to_planet[planet[0].id])]

        if len(assigned_pd) > 1:
            if (assigned_pd[0][0].num_docking_spots < assigned_pd[1][0].num_docking_spots) and \
                    (assigned_pd[0][1] + my_const.GREEDY_PLANET_DISTANCE > assigned_pd[1][1]):
                return assigned_pd[1][0]
            else:
                return assigned_pd[0][0]
        else:
            return assigned_pd[0][0] if len(assigned_pd) > 0 else None

    # In list of planets does "greedy" search
    def closest_avail_unassigned_planet(self):
        """
        In list of unassigned planets does "greedy" search.

        :return: Closest unassigned planet with free docking spots
        :rtype: hlt.entities.Planet of None
        """
        planets_distances = zip(self.closest_not_my_planets, self.closest_not_my_planets_distances)

        # unassigned_pd = [(planet, distance), (planet, distance), ...]
        unassigned_pd = [planet for planet in planets_distances if planet[0].id not in self.assigned_to_planet]

        if len(unassigned_pd) > 1:
            if (unassigned_pd[0][0].num_docking_spots < unassigned_pd[1][0].num_docking_spots) and (
                    unassigned_pd[0][1] + my_const.GREEDY_PLANET_DISTANCE > unassigned_pd[1][1]):
                return unassigned_pd[1][0]
            else:
                return unassigned_pd[0][0]
        else:
            return unassigned_pd[0][0] if len(unassigned_pd) > 0 else None

    def closest_both_types_planet(self):
        pass

    def update_assignments(self):
        """
        Updates information about assignments.

        Cases:
        - allied ship is destroyed -> delete info about it
        - planet became occupied by enemy -> re-assign ships on that enemy
        - update positions of enemy ships
        """
        alive_ships_ids = [ship.id for ship in self.team_ships]
        alive_planets_ids = [planet.id for planet in self.game_map.all_planets()]

        # my deaths
        status_changed_ships_ids = []
        for s_id in self.assigned_ships:
            if s_id not in alive_ships_ids:
                status_changed_ships_ids.append(s_id)

        for s_id in status_changed_ships_ids:
            if s_id not in alive_ships_ids:
                if self.assigned_ships[s_id] == "enemy":
                    self.unassign_kamikaze_enemy(self.ship_enemy_ship_dict[s_id].id)
                    self.unassign_ship_as_kamikaze(s_id)
                    self.unassign_enemy(self.ship_enemy_ship_dict[s_id].id)
                    self.unassign_enemy_ship_to_ship(s_id)
                    self.unassign_ship(s_id)
                elif self.assigned_ships[s_id] == "planet":
                    self.unassign_planet(self.ship_planet_dict[s_id].id)
                    self.unassign_planet_to_ship(s_id)
                    self.unassign_ship(s_id)
                else:
                    # maybe add "defender" later
                    pass

        # planet status changes
        status_changed_planets_ids = []
        for p_id in self.assigned_to_planet:
            if p_id in alive_planets_ids:
                if self.game_map.get_planet(p_id).is_owned() and (self.game_map.get_planet(
                        p_id).owner.id != self.game_map.get_me().id):
                    status_changed_planets_ids.append(p_id)
            else:
                status_changed_planets_ids.append(p_id)

        for p_id in status_changed_planets_ids:
            if p_id in alive_planets_ids:
                if self.game_map.get_planet(p_id).owner.id != self.game_map.get_me().id:
                    del self.assigned_to_planet[p_id]
                    assigned_ships_ids = [item[0] for item in self.ship_planet_dict.items() if item[1].id == p_id]

                    for s_id in assigned_ships_ids:
                        self.unassign_planet_to_ship(s_id)
                        self.unassign_ship(s_id)

                        new_target = self.closest_enemy_to_planet(p_id)

                        self.assign_ship(s_id, "enemy")
                        self.assign_enemy(new_target.id)
                        self.assign_enemy_ship_to_ship(s_id, new_target)
            else:
                del self.assigned_to_planet[p_id]
                assigned_ships_ids = [item[0] for item in self.ship_planet_dict.items() if item[1].id == p_id]
                for s_id in assigned_ships_ids:
                    self.unassign_planet_to_ship(s_id)
                    self.unassign_ship(s_id)

        # position update
        for k, v in self.ship_enemy_ship_dict.items():
            enemy = [ship for ship in self.game_map._all_ships() if ship.id == v.id]
            if enemy:
                self.ship_enemy_ship_dict.update({k: enemy[0]})

        for k, v in self.kamikaze_assign_ship.items():
            enemy = [ship for ship in self.game_map._all_ships() if ship.id == v.id]
            if enemy:
                self.kamikaze_assign_ship.update({k: enemy[0]})

    def closest_enemy_to_planet(self, p_id):
        entities_near_planet = self.game_map.nearby_entities_by_distance(self.game_map.get_planet(p_id))
        sorted_entities_near_planet = OrderedDict(
            sorted(entities_near_planet.items(), key=lambda t: t[0]))

        closest_enemy = [sorted_entities_near_planet[distance][0] for distance in
                         sorted_entities_near_planet if
                         isinstance(sorted_entities_near_planet[distance][0], hlt.entity.Ship) and
                         sorted_entities_near_planet[distance][0].owner.id != self.game_map.get_me().id][0]
        return closest_enemy

    def sorted_ships_from_enemy(self, enemy):
        entities_near_enemy = self.game_map.nearby_entities_by_distance(enemy)
        sorted_entities = OrderedDict(sorted(entities_near_enemy.items(), key=lambda t: t[0]))

        closest_ships = [sorted_entities[distance][0] for distance in sorted_entities if
                         isinstance(sorted_entities[distance][0], hlt.entity.Ship) and
                         sorted_entities[distance][0].owner.id == self.game_map.get_me().id]
        return closest_ships

    def assign_rush_leader(self):
        # ship that is farthest from enemies will become rush leader
        closest_enemy = self.closest_enemy_ships[0]
        ships_distances = [(ship, closest_enemy.calculate_distance_between(ship)) for ship in self.team_ships]
        self.rush_leader = list(sorted(ships_distances, key=lambda pair: pair[1], reverse=True))[0][0]

    def center_of_mass(self, exclude=None):
        """
        Finds the position on map, that is the center of mass of team ships.

        :param exclude: Allied ship, that should be excluded from calculations
        :return: Position of center of mass on the game map
        :rtype: hlt.entity.Position
        """
        if exclude is not None:
            x_y = [(ship.x, ship.y) for ship in self.team_ships if ship.id != exclude.id]
        else:
            x_y = [(ship.x, ship.y) for ship in self.team_ships]
        x_avg = sum(list(zip(*x_y))[0]) / len(x_y)
        y_avg = sum(list(zip(*x_y))[1]) / len(x_y)
        return hlt.entity.Position(x_avg, y_avg)
