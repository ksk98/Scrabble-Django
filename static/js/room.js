let game_in_progress = false;
let my_turn = false;
let letters_on_board = {};
let selected_letter = null;
let chatSocket;
const board_table = document.getElementById("board_table");

function getButtonFor(x, y) {
    const table = document.getElementById('board_table');
    return table.rows[y].cells[x].innerHTML;
}

function setBoard(letters) {
    for (let i = 0; i < 15; i++) {
        for (let j = 0; j < 15; j++) {
            const letter = letters.charAt((i * 15) + j)
            const button = board_table.rows[i].cells[j].firstChild;
            button.textContent = letter;

            if (letter !== " ")
                button.disabled = true;
        }
    }
}

function getBoard() {
    let out = "";

    for (let i = 0; i < 15; i++) {
        for (let j = 0; j < 15; j++) {
            out += board_table.rows[i].cells[j].firstChild.textContent;
        }
    }

    return out;
}

function getXOf(field_button) {
    return parseInt(field_button.id.split('-')[0])
}

function getYOf(field_button) {
    return parseInt(field_button.id.split('-')[1])
}

function boardButton(field_button) {
    if (!my_turn)
        return

    if (Object.keys(letters_on_board).length > 0) {
        // Letters can only be placed in a straight line
        let xGood = true;
        let yGood = true;

        for (const letter_id in letters_on_board) {
            if (getXOf(field_button) !== getXOf(document.getElementById(letter_id)))
                xGood = false;

            if (getYOf(field_button) !== getYOf(document.getElementById(letter_id)))
                yGood = false;

            if (!xGood && !yGood)
                return;
        }
    }

    if (selected_letter != null) {
        removeLetter(selected_letter);

        if (field_button.textContent !== " ") {
            // Selected field is occupied
            // Since all occupied fields that weren't occupied this turn are not clickable
            // just put the letter back to the hand and place a new one
            putLetterInNextSlot(letters_on_board[field_button.id].textContent)
        }

        letters_on_board[field_button.id] = selected_letter;
        field_button.textContent = selected_letter.textContent;
        selected_letter = null;
    } else {
        if (field_button.textContent === " ")
            return;

        // No letter is selected to place, place this letter back to the hand
        putLetterInNextSlot(field_button.textContent)
        field_button.textContent = " ";
        delete letters_on_board[field_button.id];
    }
}

function letterButton(selected) {
    selected_letter = selected;
}

function putLetterInNextSlot(letter) {
    const table = document.getElementById('letters_table');

    for (let i = 0; i < 8; i++) {
        if (table.rows[0].cells[i].childElementCount === 0) {
            const button = document.createElement("button");
            button.style.width = "100%";
            button.style.height = "100%";
            button.style.fontSize = "25px";
            button.textContent = letter;
            button.onclick = function() { letterButton(button) }

            const td = document.getElementById("letters-td-" + i);
            td.appendChild(button);
            return true;
        }
    }

    return false;
}

function removeLetter(button) {
    button.parentNode.removeChild(button);
}

function addLetters(letters) {
    let index = 0
    for (let i = 0; i < letters.length; i++) {
        if (index >= letters.length)
            break;

        putLetterInNextSlot(letters.charAt(i))
        index += 1;
    }
}

function indicateTurn(isMyTurn) {
    const indicator_table = document.getElementById("turn_indicator");
    my_turn = isMyTurn
    if (isMyTurn) {
        indicator_table.rows[0].cells[0].textContent = "YOUR TURN";
        indicator_table.style.backgroundColor = "#54f542";
    } else {
        indicator_table.rows[0].cells[0].textContent = "ENEMY TURN";
        indicator_table.style.backgroundColor = "#ed2f4f";
    }
}

function accept() {
    const out = []

    for (const letter_id in letters_on_board) {
        const record = {};
        const field = document.getElementById(letter_id);

        record["x"] = getXOf(field);
        record["y"] = getYOf(field);
        record["value"] = field.textContent;
        out.push(record)
    }

    chatSocket.send(JSON.stringify({
        "action": "accept",
        "data": out
    }))
}

function pass() {
    chatSocket.send(JSON.stringify({
        "action": "pass"
    }))
}

function initialise(room_id) {
    chatSocket = new WebSocket('ws://' + window.location.host + '/ws/scrabble/' + room_id + '/');
    for (let i = 0; i < 15; i++) {
        const tr = document.createElement("tr");
        for (let j = 0; j < 15; j++) {
            const td = document.createElement("td");
            const btn = document.createElement("button");
            btn.id = j + "-" + i;
            btn.onclick = function() { boardButton(btn) }
            btn.textContent = "";
            btn.style.width = "100%";
            btn.style.height = "100%";
            btn.style.fontSize = "25px";
            td.appendChild(btn);
            tr.appendChild(td);
        }
        board_table.appendChild(tr);
    }

    const letters_table = document.getElementById("letters_table");
    const tr = document.createElement("tr");
    for (let i = 0; i < 8; i++) {
        const td = document.createElement("td");
        td.id = "letters-td-" + i;
        tr.appendChild(td);
    }
    letters_table.appendChild(tr);

    document.getElementById("button-accept").onclick = function() { accept() }
    document.getElementById("button-pass").onclick = function() { pass() }

    // IO control
    chatSocket.onmessage = function(e) {
        const data = JSON.parse(e.data);
        if (data.operation === "set_letters") {
            addLetters(data.letters);
            indicateTurn(data.turn)
            letters_on_board = {}
        } else if (data.operation === "set_board") {
            setBoard(data.board);
        } else if (data.operation === "game_started") {
            game_in_progress = true;
        } else if (data.operation === "game_stopped") {
            game_in_progress = false;
            my_turn = false

            if (data.winner === "DRAW")
                alert("DRAW")
            else
                alert("WINNER: " + data.winner)
        }
    }
}
