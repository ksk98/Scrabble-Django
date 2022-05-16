function createRoom() {
    const rn = document.querySelector('#room_name').value;
    window.location = "/create_room/?room_name=" + rn
}

function visitRoom(roomId) {
    window.location = "/room/" + roomId + "/"
}
