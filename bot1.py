"""
bot_v1:
Added movement with no collisions
Added ship assignment
Added kamikaze mode
Logic refactored
Added rush detector
Strategies divided
Start and late greedy planet choosing
Added rush defence

"""

import hlt
import logging
import utils.constants as my_const
from utils import navigation
from utils.feature_collector import FeatureCollector
from utils.rush_detector import RushDetector
from utils import strategies

game = hlt.Game("bot_v1")
fc = FeatureCollector()
rd = RushDetector()

while True:
    game_map = game.update_map()
    fc.iterate_turn(game_map)
    logging.info(f"\n\n########### Turn number: {fc.turn}")

    for ship in fc.team_ships:
        fc.collect(ship)

        # IF RUSH
        if rd.detect_rush(ship, fc):
            strategies.rush_strategy(ship, fc)

        # IF ASSIGNED
        elif ship.id in fc.assigned_ships:
            strategies.strategy_if_assigned(ship, fc)

        # IF UNASSIGNED
        else:
            strategies.standard_strategy(ship, fc)

    game.send_command_queue(fc.command_queue)
    # TURN END
# GAME END
