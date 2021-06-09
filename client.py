import socket
import re
import ssl
import sys

# INFO: MAIN function on the very bottom

# == GLOBALS =================================

HOST, PORT = '127.0.0.3', 1796

SERVER_COMMON_NAME = 'example.com'
SERVER_CERT = 'certs/server.crt'
CLIENT_CERT = 'certs/client.crt'
CLIENT_KEY = 'certs/client.key'

# == HELPER FUNCTIONS ========================

def rcv(socket):
    # in case of codes 197-199 receive constantly
    while True:
        # receive data
        data = b''
        while b'\r\n\r\n' not in data:
            data += socket.recv(1)
        data = data.decode()[:-4]

        # if server sent 199 code - opponent disconnected unexpectedly
        if data.split(" ")[0] == '199':
            print(data)
        # if 198 code - connection established
        elif data.split(" ")[0] == '198':
            print(data)
            print("** Continue game **")
        # if 197 code - reconnection timeout
        elif data.split(" ")[0] == '197':
            print(data)
            print("You won!")
            # decide to play again or exit
            if not end_game(s):
                disconnect(s)
            else:
                start_game(s)
        # received ordinary data - return
        else:
            return data


def authorize(s):
    # until user not authorized
    while True:
        print(rcv(s))

        # decide to log in or sign in
        choice = str(input())
        while choice != '0' and choice != '1':
            print("Bad data, try again")
            choice = input()

        if choice == '0':
            s.sendall('331 Register'.encode() + b'\r\n\r\n')
        elif choice == '1':
            s.sendall('332 Log in'.encode() + b'\r\n\r\n')

        # Get username
        print(rcv(s))
        # If empty username
        temp = input()
        while len(temp) == 0:
            temp = input("Try again: ")
        s.sendall(temp.encode() + b'\r\n\r\n')

        # Get password
        print(rcv(s))
        # If empty password
        temp = input()
        while len(temp) == 0:
            temp = input("Try again: ")
        s.sendall(temp.encode() + b'\r\n\r\n')

        info = rcv(s)
        print(info)
        # if response is 2xx code (accept code) - authorization success
        if re.match("^2", info):
            break


def new_game(s):
    # CONSTANTS
    ME = 2
    OPPONENT = 1

    current_player = OPPONENT
    waiting_player = ME

    # flag indicates if user returned to match
    flg_reconnected = False

    # if info contains code 196 - player returned to game, change flag
    info = rcv(s)
    if info.split(" ")[0] == '196':
        flg_reconnected = True
    print(info)

    if not flg_reconnected:
        # wait for add to room
        print(rcv(s))

        # print rules
        print(rcv(s))

        # get info about starting player
        response = rcv(s)
        # default starting player is opponent
        # code 110 means that this player is starting
        if response.split(" ")[0] == "110":
            current_player = ME
            waiting_player = OPPONENT
        print(response)
    # if reconnected - get info who begins and skip to this point
    else:
        # get server response about beginning player
        continuing_player = rcv(s)

        # code 195 - this player is starting
        if continuing_player.split(" ")[0] == '195':
            current_player = ME
            waiting_player = OPPONENT
        print(continuing_player)

    # playing game - while not ended
    while True:
        if current_player == ME:
            # type field
            field = input("Type field: ")
            # send field
            s.sendall(field.encode() + b'\r\n\r\n')
            # get result
            result = rcv(s)

            # check if typed field is in range of error numbers
            while int(result.split(" ")[0]) in range(400, 499):
                print(result)
                # type field
                field = input("Type field again: ")
                s.sendall(field.encode() + b'\r\n\r\n')
                # get result
                result = rcv(s)
            # finally print result
            print(result)

            # get info if game is ended or not
            game_result = rcv(s)
            print(game_result)
            # if game ended
            if game_result.split(" ")[0] == "106":
                # print winner
                results = rcv(s)
                # check for draw
                print(results)
                if results.split(" ")[0] != "105":
                    winner = int(results[11])
                    if winner == waiting_player:
                        print("Congratulations!")
                    else:
                        print("Don't give up. Try again!")
                else:
                    print("Try again!")
                # break outermost while loop
                break

            # wait for change players
            print(rcv(s))
            # change
            current_player = OPPONENT
            waiting_player = ME

        elif current_player == OPPONENT:
            print("Wait for opponent move")
            # wait for opponent move
            print(rcv(s))

            # get info if game is ended or not
            game_result = rcv(s)
            print(game_result)
            # if game ended
            if game_result.split(" ")[0] == "106":
                # print winner
                results = rcv(s)
                # check for draw
                print(results)
                if results.split(" ")[0] != "105":
                    winner = int(results[11])
                    # print proper info for winner and loser and in draw case
                    if winner == waiting_player:
                        print("Congratulations!")
                    else:
                        print("Don't give up. Try again!")
                else:
                    print("Try again!")
                # break outermost while loop
                break

            # wait for change players
            print(rcv(s))
            # change
            current_player = ME
            waiting_player = OPPONENT
    # after exiting while loop process end game
    return end_game(s)


def end_game(s):
    # ask whether user want to play again
    print("Would you like to play again?")
    choice = input("[Yes/No] ").lower()

    # choice
    while choice != "no" and choice != "yes":
        choice = input("[Yes/No] ").lower()

    # send choice
    if choice == "no":
        return False
    else:
        s.sendall("310 Play again\r\n\r\n".encode())
        print(rcv(s))
        return True


def disconnect(s):
    # if user don't want to play again - disconnect
    s.sendall("320 Disconnect\r\n\r\n".encode())
    print("Disconnected")
    s.close()
    sys.exit()


def start_game(s):
    while True:
        # new game
        if not new_game(s):
            break

# == MAIN ===========================================

context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=SERVER_CERT)
context.load_cert_chain(certfile=CLIENT_CERT, keyfile=CLIENT_KEY)

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s = context.wrap_socket(s, server_side=False, server_hostname=SERVER_COMMON_NAME)

# in case of WinError 10061 (Multiple connections in short time)
while True:
    try:
        s.connect((HOST, PORT))
        break
    except ConnectionRefusedError:
        pass

print("********************")
print("Connected to server!")
print("********************\n")

try:
    # login
    authorize(s)

    # run loop of new games
    start_game(s)

    # if returned - disconnect
    disconnect(s)
except socket.error:
    print("Error")
