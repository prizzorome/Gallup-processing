import json
import csv
import os

ACTION_COLUMN = 0  # column containing the actions
PLAYER_ID_COLUMN = 2  # column containing the user id
TOTAL_GOLD_COLUMN = 2 # column containing the total amount of gold collected by the team
# use next variable to find when a new round starts
ROUND_SEPARATOR = "GoldSetup"
# use the next variable to set the target round number and avoid processing other rounds
TARGET_ROUND_NUMBER = 1

# players for testing purposes, to be used with the right dataset:  ["af1585u7p7", "Elrric", "sexog53oz3"]
PLAYERS = [
    "Elrric",
    "vki5dd5plz",
    "8grfxa3g9n",
    "tu1tarrriy",
    "brjhzjrinm",
    "z58lm8leyw",
    "zvq9c5v9gd"
]

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
ACTIONS = {}
STATES = {}
TRAJECTORIES = {}
LINKS = {}

file_names_list = []


def create_initial_and_final_states():
    """
    create all the states/nodes for glyph visualization
    :return:
    """
    stateType = 'start'  # start state
    STATES[0] = {
        'id': 0,  # start node has id 0
        'type': stateType,
        'parent_sequence': [],
        'details': {'event_type': 'start'},
        'stat': {},
        'user_ids': []}

    stateType = 'end'  # end state
    STATES[1] = {
        'id': 1,  # end node has id 1
        'parent_sequence': [],
        'type': stateType,
        'details': {'event_type': 'end'},
        'stat': {},
        'user_ids': []}


def create_mid_state(i):
    """
    create an arbitrary state between the start and end states
    :return:
    """
    stateType = 'mid'
    STATES[i] = {
        'id': i,  # start node has id 0
        'type': stateType,
        'parent_sequence': [],
        'details': {'event_type': stateType},
        'stat': {},
        'user_ids': []}


def update_state(state_id, user_id):
    STATES[state_id]['user_ids'].append(user_id)


def create_or_update_state(state_id, state_type, parent_sequence, details, stat, user_id):
    if state_id in STATES:
        STATES[state_id]['details'] = details
        STATES[state_id]['user_ids'].append(user_id)
    else:
        STATES[state_id] = {
            'id': state_id,
            'type': state_type,
            'parent_sequence': parent_sequence,
            'details': details,
            'stat': stat,
            'user_ids': [user_id]}


def add_links(trajectory, user_id):
    """
    adds link between the consecutive nodes of the trajectory
    :param trajectory:
    :param user_id:
    :return:
    """
    for item in range(0, len(trajectory) - 1):
        id = str(trajectory[item]) + "_" + str(trajectory[item + 1])  # id: previous node -> current node
        if id not in LINKS:
            LINKS[id] = {'id': id,
                         'source': trajectory[item],
                         'target': trajectory[item + 1],
                         'user_ids': [user_id]}
        else:
            users = LINKS[id]['user_ids']
            users.append(user_id)
            unique_user_set = list(set(users))
            LINKS[id]['user_ids'] = unique_user_set


def parse_data_to_json_format(csv_reader, data_file):
    """
    parse csv data to create node, link and trajectory
    :param csv_reader: raw csv data
    :return:
    """

    create_initial_and_final_states()

    # initialize the count the rounds
    round_counter = 0

    # TODO: update the user_count (it is NOT updated in the original code)
    user_count = 0

    # paola 180912: start simple by looping over each predefined player
    for player in PLAYERS:

        trajectory = [0]  # initialize with start state
        action_meaning = ["start_game"]
        key = ""
        update_state(0, player)  # update START state with new user id

        # initialize a state counter (starting from 2 because 0 and 1 are for the initial and final states respectively)
        i = 2

        # "reset" every time the CSV iterator by resetting the read position of the file object,
        # otherwise the inner loop processes the csv file only once
        data_file.seek(0)

        # update the player's trajectory by processing each row
        for row in csv_reader:

            # stop when the round ends (it must be when the SECOND round separator is met,
            # because GoldSetup is also used at the beginning!
            if row[ACTION_COLUMN] == "GoldSetup":
                break

                # use next nested IFs as a starting point to process only the rows concerning a specific round
            # (for details about how to proceed after the second IF, see:
            # https://python-forum.io/Thread-How-to-Loop-CSV-File-Beginning-at-Specific-Row)
            # if row[EVENT_COLUMN] == ROUND_SEPARATOR:
            #     round_counter = round_counter +1
            #
            #     if round_counter <= TARGET_ROUND_NUMBER: # for now we assume that the target round is the first one

            if row[PLAYER_ID_COLUMN] == player:
                action = row[ACTION_COLUMN]
                key += ('_' + action)  # generate the key for the trajectory as a sequence of action strings
                trajectory.append(i)   # append state to the trajectory
                action_meaning.append(action)

            if row[ACTION_COLUMN] == "TotalGold":
                # create a new state every time the total gold amount has increased by 50
                # if (int(row[TOTAL_GOLD_COLUMN]) % 100) == 0:
                create_or_update_state(i,
                                       "mid",
                                       "",
                                       {'event_type': "state_" + str(i) + " gold: " + row[TOTAL_GOLD_COLUMN]},
                                       "",
                                       player)
                print ("i: " + str(i))
                print(STATES[i])

                i = i + 1

                # temporary halt for more than 50 states
                if i >= 100:
                    break

        # print(key)
        trajectory.append(1)  # end state
        update_state(1, player)  # update end state with the new used id
        action_meaning.append("end_game")

        add_links(trajectory, player)

        user_ids = [player]

        if key in TRAJECTORIES:
            TRAJECTORIES[key]['user_ids'].append(player)
        else:
            TRAJECTORIES[key] = {'trajectory': trajectory,
                                 'action_meaning': action_meaning,
                                 'user_ids': user_ids,
                                 'id': key,
                                 'completed': True}

    # generate lists from dictionaries
    state_list = list(STATES.values())
    link_list = list(LINKS.values())
    trajectory_list = list(TRAJECTORIES.values())

    return {'level_info': 'Visualization',
            'num_patterns': user_count,
            'num_users': user_count,
            'nodes': state_list,
            'links': link_list,
            'trajectories': trajectory_list,
            'traj_similarity': [],
            'setting': 'test'}


def find_actions(csv_reader):
    """
    finds the action names in the csv file
    :param csv_reader: input file
    :return:
    """
    global ACTIONS
    ACTIONS = {}
    count_action = 0

    # paola 180911: in next FOR loop used columns instead of rows
    for col in csv_reader:
        actions = col[ACTION_COLUMN:]

        for item in actions:
            if item == "":
                break
            if item not in ACTIONS:
                ACTIONS[item] = count_action
                count_action += 1


def process_data(raw_data_folder, output_folder, action_from_file=True):
    """
    process each csv file to create the json file for glyph
    :param filename: input csv file
    :param action_from_file: if True then finds the actions names from the file; if False then the actions should be
    manually set in the game_actions variable in main
    :return:
    """

    for subdir, dirs, files in os.walk(raw_data_folder):
        ind = 1
        for filename in files:
            # print (os.path.join(rootdir, file))

            file_base = os.path.basename(filename).split('.')[0]
            ext = os.path.basename(filename).split('.')[1]

            if ext == 'csv':
                print(ind, ":", file_base)
                file_names_list.append(file_base)

                with open(raw_data_folder+filename, 'rU') as data_file:
                    csv_reader = csv.reader(data_file)
                    viz_data = parse_data_to_json_format(csv_reader, data_file)
                    with open(output_folder + file_base + '.json', 'w') as outfile:
                        json.dump(viz_data, outfile)
                        outfile.close()

                    print('\tDone writing to : ' + file_base + '.json')

            ind += 1


def create_game_action_dict(actions):
    """
    initializes the dictionary ACTION with the actions and assigns a unique number to each action
    :param actions: a list containing the action names
    :return:
    """
    count_action = 0
    for action in actions:
        ACTIONS[action] = count_action
        count_action += 1


if __name__ == "__main__":
    # manually set actions

    create_game_action_dict(GAME_ACTIONS)
    # print(ACTIONS)

    raw_data_folder = "../data/raw/"
    output_folder = "../data/output/"

    process_data(raw_data_folder, output_folder, action_from_file=True)
    # print(ACTIONS)
    # print(STATES)

    # print("File names of visualization_ids.json")
    # print(json.dumps(FILE_NAMES_LIST))

    # generate the visualization_ids.json file
    with open(output_folder + 'visualization_ids.json', 'w') as outfile:
        json.dump(file_names_list, outfile)
        outfile.close()
        print("\nvisualization_ids.json file generated.")
