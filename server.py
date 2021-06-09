import socket
import select
import _thread as thr
import queue
import re
import random
import database
import ssl
import time

# INFO: MAIN function on the very bottom

# == GLOBALS ========================================================

HOST, PORT = '127.0.0.3', 1796

SERVER_CERT = 'certs/server.crt'
SERVER_KEY = 'certs/server.key'
CLIENT_CERT = 'certs/client.crt'

# == HELPER FUNCTIONS ===============================================

def send_to_player(info, *sockets):
    for socket in sockets:
        # get Player objs
        plr = Game.players[socket]
        # refer to socket_output_data map by user id
        socket_output_data[plr.id].put(info)
        if socket not in outputs:
            outputs.append(socket)

# this function is used when player is not in Game.players map because
# when player is authorizing he doesn't have queues which are mapped user_id -> queue
# we don't have user id until authorization is completed
def send_to_player_direct(info, *sockets):
    for socket in sockets:
        socket.sendall(info.encode() + b'\r\n\r\n')

# in rcv it is possible to use just id, not passing socket and retrieving id
def rcv(id):
    return socket_input_data.get(id).get(True)

# it is necessary to receive data independently too when user is authorizing
def rcv_direct(socket):
    data = b''
    while b'\r\n\r\n' not in data:
        data += socket.recv(1)
    return data.decode()[:-4]

# ====================================================================

class Game:
    # map socket -> Player obj
    players = {}

    # waiting players object queue
    w_players = queue.Queue()

    # map player id -> Player obj
    p_players = {}

    # map player id -> Player object
    r_players = {}

    # rooms
    rooms_min = 0
    rooms_max = 100
    # map room id -> room obj
    rooms = {}

    # max waiting time
    MAX_TIME = 15

    # constructor
    def __init__(self):
        # run reconnect players
        thr.start_new_thread(Game.reconnect, ())
        # run match players
        thr.start_new_thread(Game.match_maker, ())

    @staticmethod
    def match_maker():
        # constantly
        while True:
            # check if queue contains more than 1 player then put them to room
            if Game.w_players.qsize() > 1:
                try:
                    # get players
                    player1 = Game.w_players.get_nowait()
                    player2 = Game.w_players.get_nowait()

                    # create room id
                    room_id = random.randint(Game.rooms_min, Game.rooms_max)
                    while room_id in Game.rooms:
                        room_id = random.randint(Game.rooms_min, Game.rooms_max)

                    # set players room
                    player1.set_room(room_id)
                    player2.set_room(room_id)

                    # set players opponents
                    player1.set_opponent(player2)
                    player2.set_opponent(player1)

                    # add players to playing players map
                    Game.p_players[player1.id] = player1
                    Game.p_players[player2.id] = player2

                    # create room
                    Game.rooms[room_id] = Room(player1, player2, room_id)
                # in case of no players waiting
                except queue.Empty:
                    pass

    @staticmethod
    def reconnect():
        # constantly
        while True:
            try:
                # iterate every user that has been disconnected
                for rec_plr in Game.r_players:
                    # get Player obj
                    r_plr = Game.r_players[rec_plr]

                    # if user reconnected - don't check time
                    RECONNECTED = False

                    # iterate every logged in user
                    for log_plr in Game.players:
                        # get Player obj
                        l_plr = Game.players[log_plr]

                        # check if any logged in user is that user who lost connection
                        if r_plr.id == l_plr.id:

                            # get disconnected user's Player obj
                            g_plr = Game.p_players[r_plr.id]

                            # set new socket
                            g_plr.socket = l_plr.socket

                            # if this player socket has any input or output values
                            # put him into inputs or outputs
                            if socket_input_data[g_plr.id].qsize() > 0:
                                inputs.append(g_plr.socket)
                            if socket_output_data[g_plr.id].qsize() > 0:
                                outputs.append(g_plr.socket)

                            # get room
                            room = Game.rooms[g_plr.room]

                            # set new player obj to new socket
                            # it means put back to logged in players
                            Game.players[log_plr] = g_plr

                            # send info that reconnection was successful
                            send_to_player_direct("196 Return to game", g_plr.socket)

                            # send info who's turn
                            if g_plr.id == room.current.id:
                                send_to_player("195 Your turn!", g_plr.socket)
                            else:
                                send_to_player("194 Opponent turn!", g_plr.socket)

                            # remove player from reconnecting players
                            Game.r_players = {key: val for key, val in Game.r_players.items() if key != rec_plr}

                            # set flag to avoid time check
                            RECONNECTED = True

                            # send info to opponent that player reconnected
                            send_to_player("198 Opponent reconnection established", g_plr.opponent.socket)

                    # check if opponent left room too
                    if r_plr.opponent.socket not in Game.players:
                        # absolutely close room
                        # remove both players from playing and reconnecting players maps
                        Game.p_players = {key: val for key, val in Game.p_players.items() if key != r_plr.id}
                        Game.p_players = {key: val for key, val in Game.p_players.items() if key != r_plr.opponent.id}
                        Game.r_players = {key: val for key, val in Game.r_players.items() if key != r_plr.id}
                        Game.r_players = {key: val for key, val in Game.r_players.items() if key != r_plr.opponent.id}
                        # delete room obj
                        del Game.rooms[r_plr.get_room()]
                        # delete players objs
                        del r_plr.opponent
                        del r_plr
                    # check reconnection time if player is not reconnected
                    elif not RECONNECTED:
                        # get time and compare with player disconnection time
                        if (int(time.time()) - r_plr.get_disconnect()) > Game.MAX_TIME:
                            # send to opponent info about reconnection timeout and close room
                            send_to_player("197 Reconnection timeout", r_plr.opponent.socket)
                            # remove disconnected opponent from playing players
                            Game.p_players = {key: val for key, val in Game.p_players.items() if key != r_plr.opponent.id}
                            # remove disconnected player from playing and reconnecting players maps
                            Game.r_players = {key: val for key, val in Game.r_players.items() if key != r_plr.id}
                            Game.p_players = {key: val for key, val in Game.p_players.items() if key != r_plr.id}
                            # !!
                            # here could be resetting opponent room and opponent data
                            # but it is done while creating new game anyway
                            #
                            # destroy room
                            del Game.rooms[r_plr.get_room()]
                            # remove disconnected player Player obj
                            del r_plr
            # in case of Game.players or Game.r_players size change (as a result of removing from Game.r_players
            # or adding to Game.players)
            except RuntimeError:
                pass
            # in case of trying to send data to players opponent who has disconnected
            except KeyError:
                pass


class Room:
    # room id - randomized when room is being created
    id = None
    # game table 3x3
    table = None
    # player1
    player1 = None
    # player2
    player2 = None
    # current Player obj
    current = None
    # waiting Player obj
    other = None

    def __init__(self, player1, player2, room_id):
        self.id = room_id
        self.player1 = player1
        self.player2 = player2
        self.table = {
            'a1': None, 'a2': None, 'a3': None,
            'b1': None, 'b2': None, 'b3': None,
            'c1': None, 'c2': None, 'c3': None
        }
        self.current = player1
        self.other = player2
        thr.start_new_thread(Room.start_game, (self,))

    def start_game(self):
        # inform players that they are being put into match
        info = "101 Game begins"
        # send players message that game starts
        send_to_player(info, self.player1.socket, self.player2.socket)

        # send rules
        send_to_player("115 Rules: Type field using one of [a,b,c] and one of [1,2,3], i.e. a2",
                       self.player1.socket, self.player2.socket)

        # player 1 begins, send info to players
        send_to_player("110 You are Player 1 (O). Player 1 begins", self.player1.socket)
        send_to_player("111 You are Player 2 (X). Player 1 begins", self.player2.socket)

        # start game
        while True:
            field = rcv(self.current.id)
            # field_check returns None in case of closed room to avoid processing user's move
            field_check = Room.check_field(self.id, self.table, field)

            # if field_check is none - game is ended
            if field_check is None:
                return

            # while field is causing error
            while not field_check[1]:
                # send error message
                send_to_player(field_check[0], self.current.socket)
                # get field again
                field = rcv(self.current.id)
                # check
                field_check = Room.check_field(self.id, self.table, field)
                # if field_check is none - game is ended
                if field_check is None:
                    return

            # set field as used
            self.table[field] = self.current

            # send message to current player that his field is correct
            send_to_player("201 Correct field", self.current.socket)

            # send to other player current player's move
            while True:
                # in case of opponent disconnection - try sending message until he returns
                # or game closes because of reconnection timeout
                try:
                    send_to_player(f"108 Opponent chosen field {field}", self.other.socket)
                    break
                except KeyError:
                    pass

            # check for winner
            result = Room.check_end_game(self.table)
            # result contains (True/False - game ended, player/None - who wins)
            if result[0]:
                # get winner
                winner = result[1]

                # announce that game ended
                send_to_player("106 Game ended", self.player1.socket, self.player2.socket)

                # announce winner
                if winner == self.player1:
                    send_to_player("103 Player 1 won", self.player1.socket, self.player2.socket)
                elif winner == self.player2:
                    send_to_player("104 Player 2 won", self.player1.socket, self.player2.socket)
                else:
                    send_to_player("105 Draw", self.player1.socket, self.player2.socket)

                # reset players attributes
                Room.end_game(self.player1, self.player2)
                # delete room
                del self
                # break while loop
                break
            # game is not ended yet
            else:
                send_to_player("102 Game keeps going", self.player1.socket, self.player2.socket)

            # change player
            curr_player = self.current
            self.current = self.other
            self.other = curr_player
            send_to_player("300 Change player", self.player1.socket, self.player2.socket)

    @staticmethod
    def check_field(room_id, table, field):
        # if room is closed
        if room_id not in Game.rooms:
            return None
        # received field change to lower case A2 -> a2
        field = field.lower()
        # match pattern:
        # - 2 chars
        # - 1st is letter, 2nd is number
        # - letter is a or b or c
        # - number is 1 or 2 or 3
        if re.match("^[a-c][1-3]$", field):
            # check if field is not used yet
            if table[field] != None:
                return ("401 Field has been already used", False)
            # return message and flag
            return ("200 Ok", True)
        else:
            return ("400 Bad field name", False)

    @staticmethod
    def check_end_game(table):
        # check vertically
        for i in range(1, 3):
            if table.get("a" + str(i)) == table.get("b" + str(i)) == table.get("c" + str(i)) is not None:
                return (True, table.get("a" + str(i)))

        # check horizontally
        chars = ['a', 'b', 'c']
        for i in chars:
            if table.get(i + "1") == table.get(i + "2") == table.get(i + "3") is not None:
                return (True, table.get(i + "1"))

        # check diagonally
        if table.get("a1") == table.get("b2") == table.get("c3") is not None:
            return (True, table.get("a1"))
        if table.get("a3") == table.get("b2") == table.get("c1") is not None:
            return (True, table.get("a3"))

        # check if there is no fields available
        for field in table:
            if table.get(field) == None:
                return (False, None)

        # no finish match pattern found
        return (True, None)

    @staticmethod
    def end_game(player1, player2):
        # unset rooms
        player1.set_room(None)
        player2.set_room(None)

        # unset opponents
        player1.set_opponent(None)
        player2.set_opponent(None)

        # delete players from playing players map
        Game.p_players = {key: val for key, val in Game.p_players.items() if key != player1.id}
        Game.p_players = {key: val for key, val in Game.p_players.items() if key != player2.id}


class Player:
    # player id in database (primary key)
    id = None
    # currect room id
    room = None
    # current opponent Player object
    opponent = None
    # player socket
    socket = None
    # player addr
    addr = None
    # disconnection time
    disconnect_time = None

    def __init__(self, socket, addr):
        self.socket = socket
        self.addr = addr
        thr.start_new_thread(Player.authorize, (self,))

    def authorize(self):
        # connect to database
        db = database.DataBase()
        db.connect()

        try:
            # try authorizing player until data is correct
            while True:
                # store login, password and player id
                username = ""
                password = ""
                ID = 0

                # SEND_TO_PLAYER_DIRECTLY - it is used in case of player's socket not available in Game.players
                # more details in function declaration - line 20 - 30
                send_to_player_direct("180 Select 0 for sign up or 1 for sign in", self.socket)

                choice = rcv_direct(self.socket).split(" ")[0]

                # get username
                send_to_player_direct("181 Type username", self.socket)
                username = rcv_direct(self.socket)

                # get password
                send_to_player_direct("182 Type password", self.socket)
                password = rcv_direct(self.socket)

                # 331 code - register
                if choice == '331':
                    ID = db.register(username, password)

                    # check for error
                    if not ID:
                        send_to_player_direct("402 Username already exists", self.socket)
                    else:
                        send_to_player_direct("202 User successfully signed up", self.socket)
                # 332 code - log in
                elif choice == '332':
                    ID = db.login(username, password)

                    # check for error
                    if not ID:
                        send_to_player_direct("403 Bad credentials", self.socket)
                    # if player is already signed in - additionally reset ID because is being set
                    elif any(Game.players[player].id == ID for player in Game.players):
                        send_to_player_direct("404 Such user is already signed in", self.socket)
                        ID = 0
                    else:
                        send_to_player_direct("203 User successfully signed in", self.socket)

                # check if user ID is not 0 - user registered or logged in
                if ID:
                    break

        # separately handle this same exception as in main
        except socket.error:
            # disconnect player
            # remove player from inputs
            while self.socket in inputs:
                inputs.remove(self.socket)

            # remove player from outputs
            while self.socket in outputs:
                outputs.remove(self.socket)

            print(f"Disconnected from {self.socket.getsockname()}")

            # close socket
            self.socket.close()
            return

        # set player ID
        self.id = ID

        # close db connection
        db.close()

        # add user to players map
        Game.players[self.socket] = self

        # append player socket to inputs
        inputs.append(self.socket)

        if self.id not in Game.r_players:
            # create output data queue
            socket_output_data[self.id] = queue.Queue()
            # create input data queue
            socket_input_data[self.id] = queue.Queue()

            # send to player waiting info
            send_to_player("100 Waiting for opponent", self.socket)

            # add user to queue
            Game.w_players.put(self)

    # some useless getters and setters
    def set_room(self, room):
        self.room = room

    def get_room(self):
        return self.room

    def set_opponent(self, opponent):
        self.opponent = opponent

    def get_opponent(self):
        return self.opponent

    def set_disconnect(self, t):
        self.disconnect_time = t

    def get_disconnect(self):
        return self.disconnect_time


# == MAIN =============================================================

context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
context.verify_mode = ssl.CERT_REQUIRED
context.load_cert_chain(certfile=SERVER_CERT, keyfile=SERVER_KEY)
context.load_verify_locations(cafile=CLIENT_CERT)

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((HOST, PORT))
s.listen(5)

# lists of sockets to watch for input and output events
inputs = [s]
outputs = []
# mapping socket -> queue of data to send on that socket when feasible
socket_output_data = {}
# mapping socket -> queue of data received
socket_input_data = {}

# info server start
print("Server running...")

# create game object
game = Game()

# event-driven server part
try:
    while True:
        # create list of input and output sockets (exception is not used)
        # 4th param '0' avoids blocking select
        i, o, e = select.select(inputs, outputs, [], 0)

        # iterate inputs list
        for curr_socket in i:
            # if socket is server - accept new client
            if curr_socket is s:
                try:
                    client, addr = s.accept()

                    print("Connected: " + addr[0])

                    # wrap socket to SSL
                    client = context.wrap_socket(client, server_side=True)

                    # create new player
                    player = Player(client, addr)
                # in case of client multiple connection
                except Exception:
                    print("Unresolved client error")
            else:
                # get player object - could be used in a few places
                plr = Game.players[curr_socket]
                try:
                    # other input events mean data arrived, or disconnections
                    data = rcv_direct(curr_socket)
                    print(f"Received from {curr_socket.getsockname()} data: {data}")

                    # 320 code - disconnect request
                    if data.split(" ")[0] == "320":
                        # remove player from inputs
                        while curr_socket in inputs:
                            inputs.remove(curr_socket)

                        # remove player from outputs
                        while curr_socket in outputs:
                            outputs.remove(curr_socket)

                        # delete Player obj
                        del plr

                        # delete curr_socket from dict
                        Game.players = {key: val for key, val in Game.players.items() if key != curr_socket}

                        print(f"Disconnected from {curr_socket.getsockname()}")

                        # close socket
                        curr_socket.close()
                    # 310 code - play again request
                    elif data.split(" ")[0] == "310":
                        # send positive response
                        send_to_player("200 Ok", curr_socket)

                        # send waiting info to player
                        send_to_player("100 Waiting for opponent", curr_socket)

                        # put player again to queue
                        Game.w_players.put(Game.players[curr_socket])
                    # any other data received
                    else:
                        # add data to queue
                        socket_input_data[plr.id].put(data)
                # handle unexpected disconnection
                except socket.error:
                    # remove socket from inputs
                    while curr_socket in inputs:
                        inputs.remove(curr_socket)

                    # remove socket from outputs
                    while curr_socket in outputs:
                        outputs.remove(curr_socket)

                    # check if player is in playing players map - if true it means that player was playing
                    if plr.id in Game.p_players:

                        # set disconnection time
                        plr.set_disconnect(time.time())

                        # send to opponent that player lost connection
                        try:
                            send_to_player("199 Opponent disconnected, waiting for reconnection", plr.opponent.socket)
                        # in case of opponent disconnection, it is unavailable to send data to opponent
                        except KeyError:
                            pass

                        # add Player obj to reconnecting players map
                        Game.r_players[plr.id] = plr
                    else:
                        # remove all player data - remove player from waiting players queue
                        temp_queue = list(Game.w_players.queue)
                        if Game.players[curr_socket] in temp_queue:
                            temp_queue.remove(Game.players[curr_socket])
                            Game.w_players.queue = queue.deque(temp_queue)

                        # remove player input/output queues
                        socket_input_data = {key: val for key, val in socket_input_data.items() if key != plr.id}
                        socket_output_data = {key: val for key, val in socket_output_data.items() if key != plr.id}

                        # delete Player obj
                        del plr

                    # remove value from dict
                    Game.players = {key: val for key, val in Game.players.items() if key != curr_socket}

                    # a disconnect, give a message and clean up
                    print(f"Disconnected from {curr_socket.getsockname()}")

                    # close socket
                    curr_socket.close()

        for curr_socket in o:
            # get player object
            plr = Game.players[curr_socket]
            # output events always mean we can send some data
            try:
                # get message from queue
                send = socket_output_data[plr.id].get_nowait()
                # if send means send contains data
                if send:
                    data = curr_socket.sendall(send.encode() + b'\r\n\r\n')
                # check if queue still contains data
                if socket_output_data[plr.id].empty():
                    outputs.remove(curr_socket)
            # in case of empty queue when no data is available in queue (because was sent)
            except queue.Empty:
                pass
            # in case of player disconnection
            except socket.error:
                pass
# in case of any uncaught error
except socket.error:
    print("Error")
finally:
    s.close()
