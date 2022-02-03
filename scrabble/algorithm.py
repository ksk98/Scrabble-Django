from scrabble.word_set import words as dictionary


def creates_valid_word(board: list[list[str]], start_x: int, start_y: int, axis_is_x: bool) -> [bool, int, int]:
    current_pos = get_starting_pos_of_word(board, start_x, start_y, axis_is_x)
    word = []

    if axis_is_x:
        ind = 0
    else:
        ind = 1

    while current_pos[ind] < len(board):
        letter = board[current_pos[1]][current_pos[0]]

        if letter != " ":
            print(letter)
            word.append(letter)
        else:
            break

        current_pos[ind] += 1

    full_word = ("".join(word)).lower()

    if len(full_word) == 1:
        return [True, 1, 0]

    points = 0
    for letter in full_word:
        points += get_points_for_letter(letter)

    return [full_word.lower() in dictionary, len(full_word), points]


def get_starting_pos_of_word(board: list[list[str]], start_x: int, start_y: int, axis_is_x: bool) -> [int, int]:
    current_pos = [start_x, start_y]

    if axis_is_x:
        while current_pos[0] > 0:
            if board[current_pos[1]][current_pos[0] - 1] != " ":
                current_pos[0] -= 1
            else:
                break
    else:
        while current_pos[1] > 0:
            if board[current_pos[1] - 1][current_pos[0]] != " ":
                current_pos[1] -= 1
            else:
                break

    return [current_pos[0], current_pos[1]]


def board_to_string(board: list[list[str]]) -> str:
    return ''.join(item for inner_list in board for item in inner_list)


def get_points_for_letter(value: str) -> int:
    value = value.upper()
    if value in ["A", "E", "I", "N", "O", "R", "S", "W", "Z"]:
        return 1
    elif value in ["C", "D", "K", "L", "M", "P", "T", "Y"]:
        return 2
    elif value in ["B", "G", "H", "J", "Ł", "U"]:
        return 3
    elif value in ["Ą", "Ę", "F", "Ó", "Ś", "Ż"]:
        return 5
    elif value == "Ć":
        return 6
    elif value == "Ń":
        return 7
    elif value == "Ź":
        return 9
    else:
        raise ValueError("ILLEGAL LETTER " + value)
