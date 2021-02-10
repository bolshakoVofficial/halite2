import hlt
import logging
import utils.constants as my_const
from utils.feature_collector import FeatureCollector


class RushDetector:
    """
    Class for detecting rush in both 2p and 4p games.

    :ivar rush: Boolean flag indicating are we rushed or not.
    :ivar done_with_rush: Boolean flag indicating that we defended rush and its time to follow standard strategy
    :ivar enemy_has_docked: Boolean flag indicating that at least one of enemy ships is not undocked
    :ivar closest_player_id: Used for 4p game. ID of player that is closest to allied ships
    :ivar closest_player_ships: List of closest player ships
    """
    def __init__(self):
        self.rush = False
        self.done_with_rush = False
        self.enemy_has_docked = False
        self.closest_player_id = None
        self.closest_player_ships = []

    def detect_rush(self, ship: hlt.entity.Ship, fc: FeatureCollector):
        """
        Method for detecting rush. Can do it for 2-players games and for 4-players games.

        For 4p games:
        Find closest player and check whether its rushing. Choose allied ship, that will mine no matter what.
        Rush mode, if enemy is not docked, is close to our ships and turn <= specified turn.

        For 2p games:
        Rush mode, if enemy is not docked, is close to our ships and turn <= specified turn.

        :param ship: Allied ship
        :param fc: Feature collector class instance
        :return: Rush status
        :rtype: bool
        """
        if not self.done_with_rush:
            # 4 PLAYERS RUSH
            if len(fc.players) > 2:
                # choose and set closest player id
                if self.closest_player_id is None:
                    self.closest_player_id = fc.closest_enemy_ships[0].owner.id

                self.closest_player_ships = [enemy for enemy in fc.closest_enemy_ships if
                                             enemy.owner.id == self.closest_player_id]
                # choose and set rush miner (ship that mines planet no matter what)
                if fc.rush_miner is None:
                    fc.rush_miner = fc.sorted_ships_from_enemy(fc.closest_enemy_ships[0])[-1]

                for enemy in self.closest_player_ships:
                    if enemy.docking_status != enemy.DockingStatus.UNDOCKED:
                        self.enemy_has_docked = True
                        break
                else:
                    self.enemy_has_docked = False

                # main condition
                # if early game & closest opponent did not dock -> seems like rush
                if (fc.turn <= my_const.RUSH_DETECT_DURATION) and not self.enemy_has_docked:
                    closest_player_distances = [ship.calculate_distance_between(target) for target in
                                                self.closest_player_ships]
                    if ship.id == fc.rush_miner.id:
                        if closest_player_distances[0] <= my_const.RUSH_DETECT_RANGE_DUEL * hlt.constants.MAX_SPEED:
                            self.rush = True
                    else:
                        if closest_player_distances[0] <= my_const.RUSH_DETECT_RANGE_FFA * hlt.constants.MAX_SPEED:
                            self.rush = True

                elif (fc.turn > my_const.RUSH_DETECT_DURATION) and not self.rush:
                    self.done_with_rush = True
                else:
                    # rushing but rush detect duration passed
                    if fc.rush_miner.calculate_distance_between(
                            fc.closest_enemy_ships[0]) < my_const.RUSH_DETECT_RANGE_FFA * 2:
                        self.rush = True
                    else:
                        self.rush = False
                        self.done_with_rush = True

            # 2 PLAYERS RUSH
            else:
                for enemy in fc.closest_enemy_ships:
                    if enemy.docking_status != enemy.DockingStatus.UNDOCKED:
                        self.enemy_has_docked = True
                        break

                # main condition
                # if early game & closest opponent did not dock & he's close -> seems like rush
                if (fc.turn <= my_const.RUSH_DETECT_DURATION) and not self.enemy_has_docked:
                    if fc.closest_enemy_ships_distances[0] <= \
                            my_const.RUSH_DETECT_RANGE_DUEL * hlt.constants.MAX_SPEED:
                        self.rush = True
                    else:
                        self.rush = False

                elif (fc.turn > my_const.RUSH_DETECT_DURATION) and not self.rush:
                    self.done_with_rush = True
                else:
                    # rushing but rush detect duration passed
                    if fc.closest_enemy_ships_distances[0] <= \
                            my_const.RUSH_DETECT_RANGE_DUEL * hlt.constants.MAX_SPEED:
                        self.rush = True
                    else:
                        self.rush = False
                        self.done_with_rush = True
        return self.rush
