from __future__ import print_function  # needed to print without newline, imported from Python 3.x
import json
import csv
import os
import statistics

SINGLE_GRAPH = None  # single global graph that has to be initialized in the main function (cannot be initialized here)
FOCUS = "teams"  # can be "single_players" or "teams"
FILE_SEPARATOR = ".csv"  # input files must have the .csv extension, otherwise the csv reader does not work
EVENTS_TO_PROCESS = {"round+risk"}  # events that can be processed:
# "gold", "round", "distance", "risk", "voting_st_dev", "risk_aversion", "round+risk", "risk_proneness"
SIMPLE_STATE_CRITERION = True  # used to determine which add_event function to use
GRAPHS = {}  # dictionary of graphs indexed by experimental conditions
VISUALIZATIONS = {}  # dictionary of visualizations based on GRAPHS
COMPETITION_LEVEL_COLUMN = 5  # column containing the leader selection algorithm
CHOSEN_FILENAME = ""  # write a string to override the output file name equal to the source file name
EVENT_COLUMN = 0  # column containing the events (including player actions)
ITEM_NAME_COLUMN = 2  # column where items' names are written during setup
ITEM_PROBABILITY_COLUMN = 4  # column where items' probability of success are written during setup
ITEM_COLUMN = 2  # column where used mining item is specified
START_VOTATION_COLUMN_1 = 2  # column containing 1st mining tool available for voting
START_VOTATION_COLUMN_2 = 3  # column containing 2nd mining tool available for voting
ITEM_VOTED_COLUMN = 3  # column containing the item voted by a player
ITEM_SELECTED_COLUMN = 2  # column containing the item selected by the leader
PLAYER_ID_COLUMN = 2  # column containing the player id (old data: column 2; new data: column 3)
TEAM_ID_COLUMN = 0  # column containing the filename, used as team ID
FOUND_GOLD_COLUMN = 4  # column containing the amount of gold found by the player
TOTAL_GOLD_COLUMN = 2  # column containing the total amount of gold collected by the team
POSITION_COLUMN = 3  # column containing the start position of "SetDestination" and the "ArrivedTo" position)
ROUND_SEPARATOR = "GoldSetup"  # when a new round starts
GOLD_INCREASE = 100  # when a new state based on the amount of TotalGold has to be created
DISTANCE_INCREASE = 100  # when a new state based on the distance traversed has to be created
RISK_THRESHOLD_LOW = 0.50  # used to select the set a selected item belongs to
RISK_THRESHOLD_MEDIUM = 0.70  # used to select the set a selected item belongs to
PROCESS_CURRENT_TEAM = True  # used to skip the rest of a team file containing "GameSuspended"

MINING_TOOLS = {}  # dictionary of mining tools available to the team, with their probability of success
MINES = {}  # dictionary of mines available to the team, with their min and max probability of success

PLAYERS = [  # players for testing purposes, to be used with the right dataset:  ["af1585u7p7", "Elrric", "sexog53oz3"]
    # "Elrric",
    # "vki5dd5plz",
    # "8grfxa3g9n",
    # "tu1tarrriy",
    # "brjhzjrinm",
    # "zvq9c5v9gd",
    # "z58lm8leyw"
]

TEAMS = []  # teams (picked from file names)

GAME_ACTIONS = [
    "ArrivedTo",
    "CensoredMessage",
    "ChatMessage",
    "DestroyRock",
    "FoundGold",
    "MiningPickaxe",
    "NewLeader",
    "PlayerConnection",
    "SelectItem",
    "SetDestination",
    "UseItem",
    "Vote"
]

# dictionaries
# STATES = {}
TRAJECTORIES = {}
LINKS = {}

# number of players or teams
TARGET_COUNT = 0

# list of file names
FILE_NAMES_LIST = []


class Graph:
    def __init__(self):
        self.index = ""  # used to index by, for instance, experimental condition
        self.states = {}
        self.trajectories = {}
        self.links = {}
        self.create_initial_and_final_states()

    def create_initial_and_final_states(self):
        """
        create all the states/nodes for glyph visualization
        :return:
        """
        state_type = 'start'  # start state
        self.states[0] = {
            'id': 0,  # start node has id 0
            'type': state_type,
            'parent_sequence': [],
            'details': {'event_type': 'start'},
            'stat': {},
            'user_ids': []}

        state_type = 'end'  # end state
        self.states[1] = {
            'id': 1,  # end node has id 1
            'parent_sequence': [],
            'type': state_type,
            'details': {'event_type': 'end'},
            'stat': {},
            'user_ids': []}

    def add_target_to_state(self, state_id, target):
        if target not in self.states[state_id]['user_ids']:
            self.states[state_id]['user_ids'].append(target)

    def create_or_update_states(self, state_id, state_type, parent_sequence, details, stat, user_id):
        # print ("state_type :" + str(state_type))
        # print ("details: " + str(details))
        if state_id in self.states:
            self.states[state_id]['type'] = state_type
            self.states[state_id]['parent_sequence'] = parent_sequence
            self.states[state_id]['details'] = details
            self.states[state_id]['stat'] = stat

            if user_id not in self.states[state_id]['user_ids']:
                self.states[state_id]['user_ids'].append(user_id)
        else:
            self.states[state_id] = {
                'id': state_id,
                'type': state_type,
                'parent_sequence': parent_sequence,
                'details': details,
                'stat': stat,
                'user_ids': [user_id]}
        # print(">>>>>>> graph: " + str(self))
        # print(">>>>>>> states: " + str(self.states))

    def add_event_string_based(self, event, event_type, target, trajectory, action_sequence):
        """
        :param event: the event to look up in the states
        :param event_type: the type of event ("mid" vs others, e.g. "round"), used to visualize nodes differently
        :param target: the target player or team
        :param trajectory: the trajectory to update
        :param action_sequence: the sequence of actions to update
        :return:
        """
        # since this may be the first time an actual state is created for this target,
        # add the target to the START state if it's not yet there:
        # this way we avoid sequence nodes that only go from START to END
        self.add_target_to_state(0, target)

        index = -1
        for key_iterator, value in self.states.items():
            existing_event_name = value['details']['event_type']

            # found an existing event: use its index
            if existing_event_name == event:
                index = key_iterator
                break

        # if the state already exists update it, otherwise create and append it after the last state
        i = index if index > 0 else self.states.__len__()

        self.create_or_update_states(i,
                                     event_type,
                                     "",
                                     {'event_type': event},
                                     "",
                                     target)
        trajectory.append(i)
        if action_sequence:
            action_sequence.append(i)

    def add_links(self, trajectory, user_id):
        """
        adds link between the consecutive nodes of the trajectory
        :param trajectory:
        :param user_id:
        :return:
        """
        for item in range(0, len(trajectory) - 1):
            uid = str(trajectory[item]) + "_" + str(trajectory[item + 1])  # id: previous node -> current node
            if uid not in self.links:
                self.links[uid] = {'id': uid,
                              'source': trajectory[item],
                              'target': trajectory[item + 1],
                              'user_ids': [user_id]}
            else:
                users = self.links[uid]['user_ids']
                users.append(user_id)
                unique_user_set = list(set(users))
                self.links[uid]['user_ids'] = unique_user_set

    def clear_graph(self):
        self.trajectories.clear()
        self.states.clear()
        self.links.clear()

    def close_graph(self, trajectory, target, action_sequence, key):
        trajectory.append(1)  # end state
        self.add_target_to_state(1, target)  # update end state with the new user id
        action_sequence.append("end_game")

        self.add_links(trajectory, target)

        user_ids = [target]

        if key in self.trajectories:
            self.trajectories[key]['user_ids'].append(target)
        else:
            self.trajectories[key] = {'trajectory': trajectory,
                                      'action_meaning': action_sequence,
                                      'user_ids': user_ids,
                                      'id': key,
                                      'completed': True}


# def create_initial_and_final_states():
#     """
#     create all the states/nodes for glyph visualization
#     :return:
#     """
#     state_type = 'start'  # start state
#     STATES[0] = {
#         'id': 0,  # start node has id 0
#         'type': state_type,
#         'parent_sequence': [],
#         'details': {'event_type': 'start'},
#         'stat': {},
#         'user_ids': []}
#
#     state_type = 'end'  # end state
#     STATES[1] = {
#         'id': 1,  # end node has id 1
#         'parent_sequence': [],
#         'type': state_type,
#         'details': {'event_type': 'end'},
#         'stat': {},
#         'user_ids': []}


# def add_target_to_state(state_id, target):
#     if target not in STATES[state_id]['user_ids']:
#         STATES[state_id]['user_ids'].append(target)


# def create_or_update_state(state_id, state_type, parent_sequence, details, stat, user_id):
#     # print ("state_type :" + str(state_type))
#     # print ("details: " + str(details))
#     if state_id in STATES:
#         STATES[state_id]['type'] = state_type
#         STATES[state_id]['parent_sequence'] = parent_sequence
#         STATES[state_id]['details'] = details
#         STATES[state_id]['stat'] = stat
#
#         if user_id not in STATES[state_id]['user_ids']:
#             STATES[state_id]['user_ids'].append(user_id)
#     else:
#         STATES[state_id] = {
#             'id': state_id,
#             'type': state_type,
#             'parent_sequence': parent_sequence,
#             'details': details,
#             'stat': stat,
#             'user_ids': [user_id]}


def add_links(trajectory, user_id):
    """
    adds link between the consecutive nodes of the trajectory
    :param trajectory:
    :param user_id:
    :return:
    """
    for item in range(0, len(trajectory) - 1):
        uid = str(trajectory[item]) + "_" + str(trajectory[item + 1])  # id: previous node -> current node
        if uid not in LINKS:
            LINKS[uid] = {'id': uid,
                          'source': trajectory[item],
                          'target': trajectory[item + 1],
                          'user_ids': [user_id]}
        else:
            users = LINKS[uid]['user_ids']
            users.append(user_id)
            unique_user_set = list(set(users))
            LINKS[uid]['user_ids'] = unique_user_set


def roundup(x):
    return x if x % GOLD_INCREASE == 0 else x + GOLD_INCREASE - x % 100


# def add_event(event, quantity, target, trajectory, action_sequence, items_selected=None, success_chance=None):
#     """
#     :param event: the event to look up in the states
#     :param quantity: the quantity we need to associate with the state
#     :param target: the target player or team
#     :param trajectory: the trajectory to update
#     :param action_sequence: the sequence of actions to update
#     :param items_selected: the possible items selected
#     :return:
#     """
#     # since this may be the first time an actual state is created for this target,
#     # add the target to the START state if it's not yet there:
#     # this way we avoid sequence nodes that only go from START to END
#     # TODO: uncomment and massage next line
#     # add_target_to_state(0, target)
#
#     index = -1
#     for key_iterator, value in STATES.items():
#         value_list = value['details']['event_type'].split()
#         existing_event_name = value_list[0]
#
#         # if an event with a given name and value exists, get its index
#         if existing_event_name == event and len(value_list) > 1:
#             existing_event_quantity = value_list[1]
#
#             # found an existing event: use its index
#             if existing_event_quantity == str(quantity):
#                 index = key_iterator
#                 break
#
#     # if the state already exists update it, otherwise create and append it after the last state
#     i = index if index > 0 else STATES.__len__()
#
#     # rounds are a special case
#     if event == "round":
#         create_or_update_state(i,
#                                "round",
#                                "",
#                                {'event_type': event + " "
#                                               + str(quantity)
#                                 # + " | avg. quotient: "
#                                 # + str(success_chance)
#                                 # + " | items: "
#                                 # + ', '.join(str(e) for e in items_selected)
#                                 },
#                                "",
#                                target)
#     # all other cases are default
#     else:
#         create_or_update_state(i,
#                                "mid",
#                                "",
#                                {'event_type': event + " " + str(quantity)},
#                                "",
#                                target)
#
#     trajectory.append(i)
#     if action_sequence:
#         action_sequence.append(i)


def close_graph(trajectory, target, action_sequence, key):
    trajectory.append(1)  # end state
    # TODO: uncomment and massage next line
    # add_target_to_state(1, target)  # update end state with the new user id
    action_sequence.append("end_game")

    add_links(trajectory, target)

    user_ids = [target]

    if key in TRAJECTORIES:
        TRAJECTORIES[key]['user_ids'].append(target)
    else:
        TRAJECTORIES[key] = {'trajectory': trajectory,
                             'action_meaning': action_sequence,
                             'user_ids': user_ids,
                             'id': key,
                             'completed': True}


def process_gold(row, column, gold_counter, accumulation, target, trajectory, action_meaning):
    gold_found = int(row[column])
    if accumulation:
        gold_counter = gold_counter + gold_found
    else:
        gold_counter = gold_found

    # create a new state every time the total gold amount has increased by DIVISOR (approximate)
    rest_of_division = (float(gold_counter) / GOLD_INCREASE) % 1.0
    remainder = 1.0 - rest_of_division
    if remainder == 1.0 or remainder <= 0.05:
        rounded_gold_counter = roundup(gold_counter)
        # TODO: uncomment and massage next line
        # add_event("gold:", rounded_gold_counter, target, trajectory, action_meaning, None, None)
        print("updated gold for target: " + target + " gold: " + str(rounded_gold_counter))
    return gold_counter


# def clear_graph():
#     TRAJECTORIES.clear()
#     STATES.clear()
#     LINKS.clear()


def process_single_players(input_file, file_reader):
    for player in PLAYERS:

        # uncomment next line to experiment only with specific players
        # if player == "z58lm8leyw" or player == "zvq9c5v9gd":

        gold_counter = 0
        round_counter = 1
        items_selected = set()
        items_used = set()
        trajectory = [0]  # initialize trajectory with start state
        action_sequence = ["start_game"]  # used to document the action sequence contained in each trajectory
        key = ""
        new_round = False  # flag used to get the player position when a new round starts
        initial_x = 0  # initial x position of the player when a new round starts
        initial_y = 0  # initial y position of the player when a new round starts
        distance_covered = 0  # total distance covered by the player while moving

        # TODO: uncomment and massage next line
        # add_target_to_state(0, player)  # update START state with new user id

        # "reset" the CSV iterator by resetting the read position of the file object,
        # otherwise the inner loop processes the csv file only once
        input_file.seek(0)

        # update the player's trajectory by processing each row
        for row in file_reader:

            action = row[EVENT_COLUMN]

            if action == "LeaderSelection":
                items_selected.add(row[ITEM_SELECTED_COLUMN])

            if len(row) > PLAYER_ID_COLUMN and row[PLAYER_ID_COLUMN] == player:
                key += ('_' + action)  # generate the key for the trajectory as a sequence of action strings
                # append the action here (NOT when gold is found, otherwise only FoundGold is appended)
                action_sequence.append(action)

                if action == "UseItem":
                    items_used.add(row[ITEM_COLUMN])

                if "gold" in EVENTS_TO_PROCESS and action == "FoundGold":
                    gold_counter = process_gold(row, FOUND_GOLD_COLUMN, gold_counter, True, player, trajectory,
                                                action_sequence)

                # TODO: if covered distance is useful, convert the code for processing it into a function
                if "distance" in EVENTS_TO_PROCESS and action == "ArrivedTo":
                    if new_round:
                        # get the player's initial position at the start of the new round
                        initial_position = row[POSITION_COLUMN]
                        initial_position = initial_position.translate(None, '()').split()
                        initial_x = int(initial_position[0])
                        initial_y = int(initial_position[1])
                        # reset the flag that triggers the getting of the initial position
                        new_round = False
                    else:
                        position = row[POSITION_COLUMN]
                        position = position.translate(None, '()').split()
                        print("player " + player + " position: " + str(position))
                        x = int(position[0])
                        y = int(position[1])
                        distance_covered = distance_covered + abs(x - initial_x) + abs(y - initial_y)
                        initial_x = x
                        initial_y = y
                        print("distance_covered: " + str(distance_covered))

                        # create a new state every time total distance has increased by DIVISOR (approximate)
                        rest_of_division = (float(distance_covered) / DISTANCE_INCREASE) % 1.0
                        remainder = 1.0 - rest_of_division
                        if remainder == 1.0 or remainder <= 0.02:
                            rounded_distance_counter = roundup(distance_covered)
                            # TODO: uncomment and massage next line
                            # add_event("distance:", rounded_distance_counter, player, trajectory, action_sequence, None, None)

            if "round" in EVENTS_TO_PROCESS and action == ROUND_SEPARATOR:
                # start creating new states based on rounds after the first gold_setup (because
                # the very first one occurs at the beginning of the game) and avoid
                # updating the action sequence because rounds are not player's actions
                if round_counter >= 1:
                    # TODO: uncomment and massage next line
                    # add_event("round", round_counter, player, trajectory, None, items_selected, None)
                    print("added round event num: " + str(round_counter))

                round_counter = round_counter + 1
                items_selected.clear()

        # ------ close states, trajectories and links, update target count, clear mining tools
        close_graph(trajectory, player, action_sequence, key)

        # increase the count of targets
        global TARGET_COUNT
        TARGET_COUNT = TARGET_COUNT + 1

        # clear the mining tools and mines
        MINING_TOOLS.clear()
        MINES.clear()


def parse_data_to_json_format(csv_reader, data_file):
    """
    parse csv data to create node, link and trajectory
    :param csv_reader: raw csv data
    :param data_file: input file
    :return:
    """

    # initialize the global graph
    global SINGLE_GRAPH
    SINGLE_GRAPH = Graph()

    if FOCUS == "single_players" and len(PLAYERS) > 0:
        process_single_players(data_file, csv_reader)
    elif FOCUS == "teams" and len(TEAMS) > 0:
        # "reset" the CSV iterator by resetting the read position of the file object,
        # otherwise the inner loop processes the csv file only once
        data_file.seek(0)

        # initialize variables
        gold_counter = 0
        round_counter = 1
        items_selected = []
        selection_counter = 0
        selected_items_quotient_sum = 0
        num_of_items = 0
        item1 = ""
        item1_prob = 0
        item2_prob = 0
        voters = 0
        voted_items = []
        selected_probabilities = []
        initial_team = ""

        # initialize trajectory, action sequence and key
        trajectory = [0]  # initialize with start state
        event_sequence = ["start_game"]
        key = ""

        for row in csv_reader:

            first_cell = row[TEAM_ID_COLUMN]
            if first_cell in TEAMS:
                team = first_cell
                if team != initial_team:

                    # a new team has been found: process it
                    global PROCESS_CURRENT_TEAM
                    PROCESS_CURRENT_TEAM = True

                    # print("---starting to process new team: " + team)

                    # use row_counter to count the lines of each team's file, because it's easier to debug single files
                    row_counter = 1

                    # ------ close previous team's states, trajectories and links
                    if initial_team != "":
                        if initial_team in SINGLE_GRAPH.states[0]['user_ids']:
                            SINGLE_GRAPH.close_graph(trajectory, initial_team, event_sequence, key)
                        # else:
                        # print ("---------------- found useless team: " + initial_team)
                        # increase the count of targets
                        global TARGET_COUNT
                        TARGET_COUNT = TARGET_COUNT + 1
                        # clear the mining tools and mines
                        MINING_TOOLS.clear()
                        MINES.clear()

                        # temporary
                        # print_risk_sequences(selected_probabilities)

                    # reinitialize variables
                    gold_counter = 0
                    round_counter = 1
                    items_selected = []
                    selection_counter = 0
                    selected_items_quotient_sum = 0
                    num_of_items = 0
                    item1 = ""
                    item1_prob = 0
                    item2_prob = 0
                    voted_items = []
                    voters = 0
                    selected_probabilities = []

                    # reinitialize trajectory, action sequence and key
                    trajectory = [0]  # initialize with start state
                    event_sequence = ["start_game"]
                    key = ""

                    # update initial team
                    initial_team = team

            event = row[EVENT_COLUMN]
            row_counter = row_counter + 1

            # make sure the current team can be processed because it has not yet reached "GameSuspended"
            global PROCESS_CURRENT_TEAM
            if PROCESS_CURRENT_TEAM:

                if event == "ItemSetup":
                    MINING_TOOLS[row[ITEM_COLUMN]] = row[ITEM_PROBABILITY_COLUMN]
                    # print ("MINING_TOOLS: " + str(MINING_TOOLS))
                elif event == "MineSetup":
                    prob_string = row[ITEM_PROBABILITY_COLUMN]
                    # mines have a min and max probability of success: we store their average in MINING_TOOLS
                    prob_list = prob_string.translate(None, '()').split()
                    floor = float(prob_list[0])
                    ceiling = float(prob_list[1])
                    MINES[row[ITEM_COLUMN]] = [floor, ceiling]
                    # MINING_TOOLS[row[ITEM_COLUMN]] = (floor + ceiling)/2
                    # print("MINES: " + str(MINES))

                # if the event is different from the team name,
                # append it to the key that distinguishes sequence graph nodes (i.e. players or teams)
                # and to the sequence of actions, and pick the mining tool if it's in the event
                if event != team:
                    key += ('_' + event)
                    # append the event here (NOT when specific events happen, otherwise only those events are appended)
                    event_sequence.append(event)

                if event == "StartVotation":

                    # print ("StartVotation - file: " + team + "  line: " + str(row_counter))
                    item1 = row[START_VOTATION_COLUMN_1]
                    item2 = row[START_VOTATION_COLUMN_2]

                    if item1.find("Mine") > -1:
                        item1_prob = MINES[item1][0]
                    else:
                        item1_prob = float(MINING_TOOLS[item1])

                    if item2.find("Mine") > -1:
                        item2_prob = MINES[item2][0]
                    else:
                        item2_prob = float(MINING_TOOLS[item2])

                    # mining_tools_prob_sum = item1_prob + item2_prob  # sum of success probs. of mining tools to choose from

                    # print("--- items to choose from: " +
                    #       item1 + " (" + str(item1_prob) + ")" + ", " +
                    #       item2 + " (" + str(item2_prob) + ")"
                    #       # + " - sum of probabilities: " + str(mining_tools_prob_sum)
                    #       )

                if event == "Vote":
                    item = row[ITEM_VOTED_COLUMN]
                    if item in MINING_TOOLS:
                        item_prob_of_success = MINING_TOOLS[item]
                        voted_items.append(float(item_prob_of_success))
                        voters = voters + 1
                        # print("-------------- voted item: " + item + " (" + str(item_prob_of_success) + ")")

                if event == "LeaderSelection":

                    # compute st_dev of votes and create a state based on it
                    if "voting_st_dev" in EVENTS_TO_PROCESS and voted_items.__len__() > 1:
                        st_dev = statistics.stdev(voted_items)
                        if st_dev == 0:
                            st_dev_bin = "None"
                        elif 0 < st_dev <= 0.35:
                            st_dev_bin = "Small"
                        elif st_dev > 0.35:
                            st_dev_bin = "Large"
                        # print("...... voted_items: " + str(voted_items))
                        # print("...... st_dev of voted items: " + str(st_dev) + " -- bin: " + st_dev_bin)
                        # print("...... added state based on st_dev_bin")

                        # add the round+risk event
                        if SIMPLE_STATE_CRITERION:
                            # print (">>> team: " + team + " round: " + str(round_counter) + " selected_probabilities: " + str(selected_probabilities))
                            event_to_add = "st_dev r" + str(round_counter) + ": " + str(st_dev_bin) + " voters: " + str(voters)
                            # print("event_to_add: " + event_to_add)
                            SINGLE_GRAPH.add_event_string_based(event_to_add, "mid", team, trajectory, None)
                        # TODO: uncomment and massage next lines
                        # else:
                        # add_event("st_dev", st_dev_bin, team, trajectory, None, None, None)

                    # reset votes and voters
                    voted_items = []
                    voters = 0

                    item = row[ITEM_SELECTED_COLUMN]
                    items_selected.append(item)
                    # print("item selected: " + item)
                    if item in MINING_TOOLS or item in MINES:

                        # print("... diff between risks: " + str(abs(item1_prob - item2_prob)))

                        difference_between_risks = float(abs(item1_prob - item2_prob))

                        if item1_prob == item2_prob:
                            risk = "n.a."
                            # print(".......... team: " + team + " RISK DIFFERENCE: NONE!")
                        elif difference_between_risks <= 0.1001:
                            risk = "negligible"
                            # print (".......... team: " + team + " RISK DIFFERENCE <= 0.1!")
                        elif item == item1 and item1_prob < item2_prob:
                            risk = "high"
                        else:
                            risk = "low"
                        selected_probabilities.append(risk)
                        # print("-------------- difference between risks: " + str(float(abs(item1_prob - item2_prob))))
                        # print("item1_prob: " + str(item1_prob) + ", " "item2_prob: " + str(item2_prob))

                        risk_proneness = ""
                        if risk == "high":
                            if difference_between_risks <= 0.3001:
                                risk_proneness = "low"
                            elif 0.3001 < difference_between_risks < 0.6001:
                                risk_proneness = "medium"
                            elif difference_between_risks >= 0.6001:
                                risk_proneness = "high"

                            if "risk_proneness" in EVENTS_TO_PROCESS and risk_proneness != "":
                                if SIMPLE_STATE_CRITERION:
                                    event_to_add = "risk_proneness" + ": " + risk_proneness
                                    # print (event_to_add)
                                    SINGLE_GRAPH.add_event_string_based(event_to_add, "mid", team, trajectory, None)

                        if "risk" in EVENTS_TO_PROCESS and risk != "":
                            if SIMPLE_STATE_CRITERION:
                                event_to_add = "r" + str(round_counter) + ":" + "risk " + risk
                                SINGLE_GRAPH.add_event_string_based(event_to_add, "mid", team, trajectory, None)
                            # TODO: uncomment and massage next lines
                            # else:
                                #add_event("risk", risk, team, trajectory, None, items_selected, risk)
                                # print("_______ added risk event: " + team + " risk: " + risk)

                if "gold" in EVENTS_TO_PROCESS and event == "TotalGold":
                    gold_counter = process_gold(row, TOTAL_GOLD_COLUMN, False, gold_counter, team, trajectory,
                                                event_sequence)

                if event == ROUND_SEPARATOR:
                    if round_counter >= 1:
                        avg_selected_item_success_prob = 0
                        risk_aversion = ""

                        if num_of_items > 0:
                            # compute the average quotient and then reset its components
                            avg_selected_item_success_prob = round(
                                float(selected_items_quotient_sum) / selection_counter, 2)
                            num_of_items = 0
                            selected_items_quotient_sum = 0
                            selection_counter = 0
                            # select the risk aversion category
                            if avg_selected_item_success_prob <= RISK_THRESHOLD_LOW:
                                risk_aversion = "low"
                            elif RISK_THRESHOLD_LOW < avg_selected_item_success_prob <= RISK_THRESHOLD_MEDIUM:
                                risk_aversion = "medium"
                            else:
                                risk_aversion = "high"

                        # add the risk aversion event
                        # TODO: uncomment and massage next lines
                        # if "risk_aversion" in EVENTS_TO_PROCESS and risk_aversion != "":
                             # add_event("risk_aversion", risk_aversion, team, trajectory, None, items_selected, str(avg_selected_item_success_prob))

                        # add the round event and avoid updating action sequence because rounds are not team's actions
                        if "round" in EVENTS_TO_PROCESS:
                            if SIMPLE_STATE_CRITERION:
                                event_to_add = "round " + str(round_counter)
                                SINGLE_GRAPH.add_event_string_based(event_to_add, "round", team, trajectory, None)
                            # TODO: uncomment and massage next lines
                            # else:
                                #add_event("round", round_counter, team, trajectory, None, items_selected, risk_aversion)
                                # print("added round event num: " + str(round_counter))
                                # print(">>>>>>>>>> avg_selected_item_success_prob: " + str(avg_selected_item_success_prob))
                                # print(">>>>>>>>>> risk_aversion: " + risk_aversion)

                        # add the round+risk event
                        if "round+risk" in EVENTS_TO_PROCESS and selected_probabilities.__len__() > 0:
                            if SIMPLE_STATE_CRITERION:
                                # print (">>> team: " + team + " round: " + str(round_counter) + " selected_probabilities: " + str(selected_probabilities))

                                event_to_add = "round+risk" + str(round_counter) + ": " + str(selected_probabilities)
                                SINGLE_GRAPH.add_event_string_based(event_to_add, "round", team, trajectory, None)
                                # print("...... team: " + team + " round counter: " + str(round_counter) + " selected probs.: " + str(selected_probabilities))
                                # reset the list of selected probabilities
                                selected_probabilities = []

                    round_counter = round_counter + 1

                    items_selected = []

            # if the game is suspended, stop processing the current team until a new team is found in the file
            if first_cell == "GameSuspended":
                global PROCESS_CURRENT_TEAM
                PROCESS_CURRENT_TEAM = False
                # print ("!!!!!!!!!!!! Team: " + team + " has GameSuspended!")

                # temporary
                # print_risk_sequences(selected_probabilities)

            # if it's end of file, close the graph of the current team if
            # it's in the START state (which means the team is in at least 1 actual state)
            if first_cell == "END" and team in TEAMS and team in SINGLE_GRAPH.states[0]['user_ids']:
                SINGLE_GRAPH.close_graph(trajectory, team, event_sequence, key)
                # increase the count of targets
                global TARGET_COUNT
                TARGET_COUNT = TARGET_COUNT + 1
                # clear the mining tools and mines
                MINING_TOOLS.clear()
                MINES.clear()

                # temporary
                # print_risk_sequences(selected_probabilities)

    # ------ RETURN RESULTS
    # generate lists from dictionaries
    state_list = list(SINGLE_GRAPH.states.values())
    link_list = list(SINGLE_GRAPH.links.values())
    trajectory_list = list(SINGLE_GRAPH.trajectories.values())

    # compute similarities among trajectories (possibly on the basis of simple criteria)
    # ------ FOR JIMMY: next line can be commented and replaced with a call to your function
    # Jimmy test
    # TODO: uncomment and massage next line
    # traj_similarity = compute_similarities()

    # return the results
    return {'level_info': 'Visualization',
            'num_patterns': TARGET_COUNT,
            'num_users': TARGET_COUNT,
            'nodes': state_list,
            'links': link_list,
            'trajectories': trajectory_list,
            # TODO: massage next line
            'traj_similarity': [], # traj_similarity,
            'setting': 'test'}


def parse_team_data_onto_multiple_json_files(csv_reader, team):
    """
    parse csv data to create node, link and trajectory
    :param csv_reader: raw csv data
    :param team: filename
    :return:
    """

    # increase the count of teams
    global TARGET_COUNT
    TARGET_COUNT = TARGET_COUNT + 1

    # initialize a new graph
    graph = Graph()

    # clear mining tools and mines
    # TODO: transform these global vars into local ones
    MINING_TOOLS.clear()
    MINES.clear()

    # initialize variables
    exp_cond = ""
    gold_counter = 0
    round_counter = 1
    items_selected = []
    selection_counter = 0
    selected_items_quotient_sum = 0
    num_of_items = 0
    item1 = ""
    item1_prob = 0
    item2_prob = 0
    voters = 0
    voted_items = []
    selected_probabilities = []
    process_current_team = True

    # initialize trajectory, action sequence and key
    trajectory = [0]  # initialize with start state
    event_sequence = ["start_game"]
    key = ""

    for row in csv_reader:
        # use row_counter to count the lines of each team's file, because it's easier to debug single files
        row_counter = 1

        event = row[EVENT_COLUMN]
        row_counter = row_counter + 1

        # if the game is suspended, output signal to stop processing the current team
        if event == "GameSuspended":
            process_current_team = False
            # print ("!!!!!!!!!!!! Team: " + team + " has GameSuspended!")

            # temporary
            # print_risk_sequences(selected_probabilities)

        # make sure the current team can be processed because it has not yet reached "GameSuspended"
        if process_current_team:

            if event == "SetupMatch":
                exp_cond = "Competition" + row[COMPETITION_LEVEL_COLUMN]
                if exp_cond not in GRAPHS:
                    # add the new graph initialized above to the dictionary of experimental conditions
                    GRAPHS[exp_cond] = graph
                else:
                    # get the graph corresponding to the current experimental condition
                    graph = GRAPHS[exp_cond]

            if event == "ItemSetup":
                MINING_TOOLS[row[ITEM_COLUMN]] = row[ITEM_PROBABILITY_COLUMN]
                # print ("MINING_TOOLS: " + str(MINING_TOOLS))
            elif event == "MineSetup":
                prob_string = row[ITEM_PROBABILITY_COLUMN]
                # mines have a min and max probability of success: we store their average in MINING_TOOLS
                prob_list = prob_string.translate(None, '()').split()
                floor = float(prob_list[0])
                ceiling = float(prob_list[1])
                MINES[row[ITEM_COLUMN]] = [floor, ceiling]
                # MINING_TOOLS[row[ITEM_COLUMN]] = (floor + ceiling)/2
                # print("MINES: " + str(MINES))

            # append the event to the key that distinguishes sequence graph nodes (i.e. players or teams)
            # and to the sequence of actions, and pick the mining tool if it's in the event
            key += ('_' + event)
            # append the event here (NOT when specific events happen, otherwise only those events are appended)
            event_sequence.append(event)

            if event == "StartVotation":

                # print ("StartVotation - file: " + team + "  line: " + str(row_counter))
                item1 = row[START_VOTATION_COLUMN_1]
                item2 = row[START_VOTATION_COLUMN_2]

                if item1.find("Mine") > -1:
                    item1_prob = MINES[item1][0]
                else:
                    item1_prob = float(MINING_TOOLS[item1])

                if item2.find("Mine") > -1:
                    item2_prob = MINES[item2][0]
                else:
                    item2_prob = float(MINING_TOOLS[item2])

                # mining_tools_prob_sum = item1_prob + item2_prob  # sum of success probs. of mining tools to choose from

                # print("--- items to choose from: " +
                #       item1 + " (" + str(item1_prob) + ")" + ", " +
                #       item2 + " (" + str(item2_prob) + ")"
                #       # + " - sum of probabilities: " + str(mining_tools_prob_sum)
                #       )

            if event == "Vote":
                item = row[ITEM_VOTED_COLUMN]
                if item in MINING_TOOLS:
                    item_prob_of_success = MINING_TOOLS[item]
                    voted_items.append(float(item_prob_of_success))
                    voters = voters + 1
                    # print("-------------- voted item: " + item + " (" + str(item_prob_of_success) + ")")

            if event == "LeaderSelection":

                # compute st_dev of votes and create a state based on it
                if "voting_st_dev" in EVENTS_TO_PROCESS and voted_items.__len__() > 1:
                    st_dev = statistics.stdev(voted_items)
                    if st_dev == 0:
                        st_dev_bin = "None"
                    elif 0 < st_dev <= 0.35:
                        st_dev_bin = "Small"
                    elif st_dev > 0.35:
                        st_dev_bin = "Large"
                    # print("...... voted_items: " + str(voted_items))
                    # print("...... st_dev of voted items: " + str(st_dev) + " -- bin: " + st_dev_bin)
                    # print("...... added state based on st_dev_bin")

                    # add the round+risk event
                    if SIMPLE_STATE_CRITERION:
                        # print (">>> team: " + team + " round: " + str(round_counter) + " selected_probabilities: " + str(selected_probabilities))
                        event_to_add = "st_dev r" + str(round_counter) + ": " + str(st_dev_bin) + " voters: " + str(voters)
                        # print("event_to_add: " + event_to_add)
                        graph.add_event_string_based(event_to_add, "mid", team, trajectory, None)
                    # TODO: uncomment and massage next lines
                    # else:
                    #     add_event("st_dev", st_dev_bin, team, trajectory, None, None, None)

                # reset votes and voters
                voted_items = []
                voters = 0

                item = row[ITEM_SELECTED_COLUMN]
                items_selected.append(item)
                # print("item selected: " + item)
                if item in MINING_TOOLS or item in MINES:

                    # print("... diff between risks: " + str(abs(item1_prob - item2_prob)))

                    difference_between_risks = float(abs(item1_prob - item2_prob))

                    if item1_prob == item2_prob:
                        risk = "n.a."
                        # print(".......... team: " + team + " RISK DIFFERENCE: NONE!")
                    elif difference_between_risks <= 0.1001:
                        risk = "negligible"
                        # print (".......... team: " + team + " RISK DIFFERENCE <= 0.1!")
                    elif item == item1 and item1_prob < item2_prob:
                        risk = "high"
                    else:
                        risk = "low"
                    selected_probabilities.append(risk)
                    # print("-------------- difference between risks: " + str(float(abs(item1_prob - item2_prob))))
                    # print("item1_prob: " + str(item1_prob) + ", " "item2_prob: " + str(item2_prob))

                    risk_proneness = ""
                    if risk == "high":
                        if difference_between_risks <= 0.3001:
                            risk_proneness = "low"
                        elif 0.3001 < difference_between_risks < 0.6001:
                            risk_proneness = "medium"
                        elif difference_between_risks >= 0.6001:
                            risk_proneness = "high"

                        if "risk_proneness" in EVENTS_TO_PROCESS and risk_proneness != "":
                            if SIMPLE_STATE_CRITERION:
                                event_to_add = "risk_proneness" + ": " + risk_proneness
                                # print (event_to_add)
                                graph.add_event_string_based(event_to_add, "mid", team, trajectory, None)

                    if "risk" in EVENTS_TO_PROCESS and risk != "":
                        if SIMPLE_STATE_CRITERION:
                            event_to_add = "r" + str(round_counter) + ":" + "risk " + risk
                            graph.add_event_string_based(event_to_add, "mid", team, trajectory, None)
                        # TODO: uncomment and massage next line
                        # else:
                            # add_event("risk", risk, team, trajectory, None, items_selected, risk)
                            # print("_______ added risk event: " + team + " risk: " + risk)

            if "gold" in EVENTS_TO_PROCESS and event == "TotalGold":
                gold_counter = process_gold(row, TOTAL_GOLD_COLUMN, False, gold_counter, team, trajectory,
                                            event_sequence)

            if event == ROUND_SEPARATOR:
                if round_counter >= 1:
                    avg_selected_item_success_prob = 0
                    risk_aversion = ""

                    if num_of_items > 0:
                        # compute the average quotient and then reset its components
                        avg_selected_item_success_prob = round(
                            float(selected_items_quotient_sum) / selection_counter, 2)
                        num_of_items = 0
                        selected_items_quotient_sum = 0
                        selection_counter = 0
                        # select the risk aversion category
                        if avg_selected_item_success_prob <= RISK_THRESHOLD_LOW:
                            risk_aversion = "low"
                        elif RISK_THRESHOLD_LOW < avg_selected_item_success_prob <= RISK_THRESHOLD_MEDIUM:
                            risk_aversion = "medium"
                        else:
                            risk_aversion = "high"

                    # add the risk aversion event
                    # TODO: uncomment and massage next lines
                    # if "risk_aversion" in EVENTS_TO_PROCESS and risk_aversion != "":
                    #     add_event("risk_aversion", risk_aversion, team, trajectory, None, items_selected,
                    #               str(avg_selected_item_success_prob))

                    # add the round event and avoid updating action sequence because rounds are not team's actions
                    if "round" in EVENTS_TO_PROCESS:
                        if SIMPLE_STATE_CRITERION:
                            event_to_add = "round " + str(round_counter)
                            graph.add_event_string_based(event_to_add, "round", team, trajectory, None)
                        # TODO: uncomment and massage next line
                        # else:
                        #     add_event("round", round_counter, team, trajectory, None, items_selected, risk_aversion)
                            # print("added round event num: " + str(round_counter))
                            # print(">>>>>>>>>> avg_selected_item_success_prob: " + str(avg_selected_item_success_prob))
                            # print(">>>>>>>>>> risk_aversion: " + risk_aversion)

                    # add the round+risk event
                    if "round+risk" in EVENTS_TO_PROCESS and selected_probabilities.__len__() > 0:
                        if SIMPLE_STATE_CRITERION:
                            # print (">>> team: " + team + " round: " + str(round_counter) + " selected_probabilities: " + str(selected_probabilities))

                            event_to_add = "round+risk" + str(round_counter) + ": " + str(selected_probabilities)
                            graph.add_event_string_based(event_to_add, "round", team, trajectory, None)
                            # print("...... team: " + team + " round counter: " + str(round_counter) + " selected probs.: " + str(selected_probabilities))
                            # reset the list of selected probabilities
                            selected_probabilities = []

                round_counter = round_counter + 1
                items_selected = []

    # if it's end of file, close the graph of the current team if
    # it's in the START state (which means the team is in at least 1 actual state)
    if team in graph.states[0]['user_ids']:
        graph.close_graph(trajectory, team, event_sequence, key)

    # temporary
    # print_risk_sequences(selected_probabilities)

    # ------ RETURN RESULTS
    # generate lists from dictionaries
    state_list = list(graph.states.values())
    link_list = list(graph.links.values())
    trajectory_list = list(graph.trajectories.values())

    # compute similarities among trajectories (possibly on the basis of simple criteria)
    # ------ FOR JIMMY: next line can be commented and replaced with a call to your function
    # Jimmy test
    # TODO: uncomment and massage next line
    # traj_similarity = compute_similarities()

    # store the results
    visualization = {
         'level_info': 'Visualization',
            'num_patterns': TARGET_COUNT,
            'num_users': TARGET_COUNT,
            'nodes': state_list,
            'links': link_list,
            'trajectories': trajectory_list,
            # TODO: massage next line
            'traj_similarity': [],  # traj_similarity,
            'setting': 'test'}
    VISUALIZATIONS[exp_cond] = visualization

    # return the results
    return {'level_info': 'Visualization',
            'num_patterns': TARGET_COUNT,
            'num_users': TARGET_COUNT,
            'nodes': state_list,
            'links': link_list,
            'trajectories': trajectory_list,
            # TODO: massage next line
            'traj_similarity': [], # traj_similarity,
            'setting': 'test'}


def print_risk_sequences(selected_probabilities):
    if selected_probabilities.__len__() > 0:
        for prob in selected_probabilities:
            print(str(prob) + ",", end='')
        print()


def compute_similarities():
    # compute distances between trajectories
    similarity_criterium = "GoldSetup"
    traj_similarity = []
    similarity_id = 0
    similarity_threshold = 6
    # skipped_traj_ids stores the trajectories that are too close to some trajectories
    # thus need not be recomputed
    skipped_traj_ids = []

    for i in range(len(TRAJECTORIES) - 1):

        if i not in skipped_traj_ids:

            for j in range(i + 1, len(TRAJECTORIES)):

                quantity_i = TRAJECTORIES.values()[i]['action_meaning'].count(similarity_criterium)
                quantity_j = TRAJECTORIES.values()[j]['action_meaning'].count(similarity_criterium)
                sim = abs(quantity_i - quantity_j)

                # print("...... quantity_i: " + str(quantity_i))
                # print("...... quantity_j: " + str(quantity_j))
                # print("...... diff: " + str(sim))
                #
                # print("...... similarity: " + str(sim))

                traj_similarity.append({'id': str(similarity_id),
                                        'source': i,
                                        'target': j,
                                        'similarity': sim
                                        })

                # print("...... traj_similarity[similarity_id]: " + str(traj_similarity[similarity_id]))
                similarity_id += 1

                if sim < similarity_threshold and j not in skipped_traj_ids:
                    # print "------------ Skipping: %d" % j
                    skipped_traj_ids.append(j)
    return traj_similarity


def find_players(csv_reader):
    """
    finds the player names in the csv file
    :param csv_reader: input file
    :return:
    """
    for row in csv_reader:
        if row[EVENT_COLUMN] == "PlayerConnection":
            PLAYERS.append(row[PLAYER_ID_COLUMN])


def find_teams(csv_reader):
    """
    finds the teams in the csv file
    :param csv_reader: input file
    :return:
    """
    for row in csv_reader:
        team = row[TEAM_ID_COLUMN]
        if team.find(FILE_SEPARATOR) > -1:
            TEAMS.append(team)


def process_data(input_folder, out_folder, action_from_file=True):
    """
    process each csv file to create the json file for glyph
    :param input_folder: folder containing raw data files
    :param out_folder: output folder
    :param action_from_file: if True then finds the actions names from the file; if False then the actions should be
    manually set in the game_actions variable in main
    :return:
    """

    for subdir, dirs, files in os.walk(input_folder):
        ind = 0
        for filename in files:
            # print (os.path.join(rootdir, file))

            if CHOSEN_FILENAME == "":
                output_file = os.path.basename(filename).split('.')[0]
            else:
                output_file = CHOSEN_FILENAME

            ext = os.path.basename(filename).split('.')[1]

            if ext == 'csv':
                print(ind, ":", output_file)
                FILE_NAMES_LIST.append(output_file)

                with open(input_folder + filename, 'rU') as data_file:
                    csv_reader = csv.reader(data_file)

                    if FOCUS == "single_players":
                        find_players(csv_reader)
                    elif FOCUS == "teams":
                        find_teams(csv_reader)

                    viz_data = parse_data_to_json_format(csv_reader, data_file)

                    print('\tDone writing to : ' + output_file + '.json')
                    ind += 1

            with open(out_folder + output_file + '.json', 'w') as outfile:
                json.dump(viz_data, outfile)
                outfile.close()


def process_data_files_by_condition(input_folder, out_folder):
    """
    process each csv file to create one or more json files for glyph, each json file named according to some criteria
    :param input_folder: folder containing raw data files
    :param out_folder: output folder
    :return:
    """

    for subdir, dirs, files in os.walk(input_folder):

        for filename in files:
            # print (os.path.join(rootdir, file))

            ext = os.path.basename(filename).split('.')[1]

            if ext == 'csv':

                with open(input_folder + filename, 'rU') as data_file:
                    csv_reader = csv.reader(data_file)

                    # viz_data = parse_team_data_onto_multiple_json_files(csv_reader, filename)
                    parse_team_data_onto_multiple_json_files(csv_reader, filename)

    for exp_cond, viz_data in VISUALIZATIONS.items():

        output_file = exp_cond
        FILE_NAMES_LIST.append(output_file)

        with open(out_folder + output_file + '.json', 'w') as outfile:
            json.dump(viz_data, outfile)
            outfile.close()

        print('\tDone writing to file : ' + output_file + '.json')



if __name__ == "__main__":
    # manually set actions

    # create_game_action_dict(GAME_ACTIONS)
    # print(ACTIONS)

    raw_data_folder = "../data/raw/"
    output_folder = "../data/output/"

    # process_data(raw_data_folder, output_folder, action_from_file=True)

    process_data_files_by_condition(raw_data_folder, output_folder)

    # print(STATES)

    # print("File names of visualization_ids.json")
    # print(json.dumps(FILE_NAMES_LIST))

    # generate the visualization_ids.json file
    with open(output_folder + 'visualization_ids.json', 'w') as outfile:
        json.dump(FILE_NAMES_LIST, outfile)
        outfile.close()
        print("\nvisualization_ids.json file generated.")
