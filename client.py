import socket
import re
import ssl
import sys
import os.path as path

# INFO: MAIN function on the very bottom

# == GLOBALS =================================

HOST, PORT = '127.0.0.3', 1796

SERVER_COMMON_NAME = 'example.com'
SERVER_CERT = """-----BEGIN CERTIFICATE-----
MIIDqTCCApGgAwIBAgIUf/d+Pd5O3F9BvokVeRF/R73KrV8wDQYJKoZIhvcNAQEL
BQAwZDELMAkGA1UEBhMCUEwxEjAQBgNVBAgMCUx1YmVsc2tpZTEPMA0GA1UEBwwG
THVibGluMQwwCgYDVQQKDANNTUoxDDAKBgNVBAsMA21tajEUMBIGA1UEAwwLZXhh
bXBsZS5jb20wHhcNMjEwNjAyMTUyMDEwWhcNMjIwNjAyMTUyMDEwWjBkMQswCQYD
VQQGEwJQTDESMBAGA1UECAwJTHViZWxza2llMQ8wDQYDVQQHDAZMdWJsaW4xDDAK
BgNVBAoMA01NSjEMMAoGA1UECwwDbW1qMRQwEgYDVQQDDAtleGFtcGxlLmNvbTCC
ASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBAMliU05pFBCl62bN58Mf+cEA
u0+SQkIV2IfTpY2Ge4GbtL0rJ7cuHtr9trisEVT5NNmCptRz2EeN7GdarTew1LXx
tTQJdzCivfKUpXOLBHoJb3ve7qUPqtRubhSHwbuWmVEF7IivVhX6cyeI/p7VDXpz
PvwXJtZD//52tsRkEiR1mfjeve92UtIubwQqRhpqLpPEqoBtWF1tuAETN3Z7EPVt
SSWbrvzRgfUYqxAOJDSbJ9oqj23o1ZFc2rrY+yK1y+NwRycGLsjyNR3DmKNGoY54
nP3dp5ght/mjUQb9yBg8zHfMWbAGzoVvog2SHgXo+CYszcYCE6Wi5VzqvZSXYF8C
AwEAAaNTMFEwHQYDVR0OBBYEFO5wJA7ftfG15IxBmZPLrYEhExcVMB8GA1UdIwQY
MBaAFO5wJA7ftfG15IxBmZPLrYEhExcVMA8GA1UdEwEB/wQFMAMBAf8wDQYJKoZI
hvcNAQELBQADggEBABE1iYEaA3U4+WIF0K0CYW7LgCYZdpGA4W7yCySdmCSgj5L3
0YL8ENYIkgnsxSBxtB0ys6HyQebSMjXWzCBwruBUzn0GksxkX/0dMsit0O9eWauh
BAD4/qNH+hf8djnvFiEcCEJ9hHfpuYQC+HmwvWVbeLEQeFavQNm1g0p9mAlOw1VA
F0m6Qv00mJz6c/aD0Rd/6zOpvemvaKaELysTbGC66a6XN4karRjWBFXUA/v4NI3Y
7yZLm738/ok+rf06HiwhT81lkMW5MFLypdnT/Qcmsgx+J4hvVogXpds5UGY6EX37
N1JCqW9baLWU9J+NHInCxzpYDdIypUVLhP3RANU=
-----END CERTIFICATE-----"""
CLIENT_CERT = 'certs/client.crt'
CLIENT_KEY = 'certs/client.key'

SERVER_TEMP = 'server.crt'

# user uuid WITHOUT 'ID_' part
USER_UUID = ""

# == HELPER FUNCTIONS ========================

def strtoassoc(data):
    dict = {}
    parts = data.split("\r\n")
    for part in parts:
        subparts = part.split(":")
        dict[subparts[0]] = subparts[1]
    dict['Message'] = dict['Code'] + ' ' + dict['Data']
    return dict

def rcv_direct(socket):
    data = b''
    while b'\r\n\r\n' not in data:
        data += socket.recv(1)
    return data.decode()[:-4]

def rcv(socket):
    # in case of codes 197-199 receive constantly
    while True:
        # receive data
        data = b''
        while b'\r\n\r\n' not in data:
            data += socket.recv(1)
        data = data.decode()[:-4]

        # split data string to associative array
        dict = strtoassoc(data)

        # Invalid session ID - server side
        if dict['Code'] == '405':
            print(dict['Message'])
            print("The program will be closed for security reasons")
            s.close()
            sys.exit()
        # if server sent 199 code - opponent disconnected unexpectedly
        elif dict['Code'] == '199':
            print(dict['Message'])
        # if 198 code - connection established
        elif dict['Code'] == '198':
            print(dict['Message'])
            print("** Continue game **")
        # if 197 code - reconnection timeout
        elif dict['Code'] == '197':
            print(dict['Message'])
            print("You won!")
            # decide to play again or exit
            if not end_game(s):
                disconnect(s)
            else:
                start_game(s)
        # 120 uuid data code - return uuid to set globally
        elif dict['Code'] == '120':
            return dict['Data']
        # received ordinary data - return
        else:
            return dict['Message']

def send_to_server(info, s):
    msg_code = info.split(" ")[0]
    msg_data = info[len(msg_code) + 1:]
    message = f"UUID:{USER_UUID}\r\nCode:{msg_code}\r\nData:{msg_data}"
    s.sendall(message.encode() + b'\r\n\r\n')

def send_to_server_direct(info, s):
    s.sendall(info.encode() + b'\r\n\r\n')

def authorize(s):
    # until user not authorized
    while True:
        print(rcv_direct(s))

        # decide to log in or sign in
        choice = str(input())
        while choice != '0' and choice != '1':
            print("Bad data, try again")
            choice = input()

        if choice == '0':
            send_to_server_direct('331 Register', s)
        elif choice == '1':
            send_to_server_direct('332 Log in', s)

        # Get username
        print(rcv_direct(s))
        # If empty username
        temp = input()
        while len(temp) == 0:
            temp = input("Try again: ")
        send_to_server_direct(temp, s)

        # Get password
        print(rcv_direct(s))
        # If empty password
        temp = input()
        while len(temp) == 0:
            temp = input("Try again: ")
        send_to_server_direct(temp, s)

        info = rcv_direct(s)
        print(info)
        # if response is 2xx code (accept code) - authorization success
        if re.match("^2", info):
            return rcv(s)

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
            send_to_server(f"121 {field}", s)
            # get result
            result = rcv(s)

            # check if typed field is in range of error numbers
            while int(result.split(" ")[0]) in range(400, 499):
                print(result)
                # type field
                field = input("Type field again: ")
                send_to_server(f"121 {field}", s)
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
                    elif winner == current_player:
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
                    elif winner == current_player:
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
        send_to_server_direct("310 Play again", s)
        print(rcv(s))
        return True

def disconnect(s):
    # if user don't want to play again - disconnect
    send_to_server_direct("320 Disconnect", s)
    print("Disconnected")
    s.close()
    sys.exit()

def start_game(s):
    while True:
        # new game
        if not new_game(s):
            break

# == MAIN ===========================================
if __name__ == "__main__":

    print("Starting...")
    if len(sys.argv) == 3:
        cert_path = str(sys.argv[1])
        key_path = str(sys.argv[2])
        if not path.isfile(cert_path):
            sys.stderr.write('incorrect cert path')
            exit(1)
        elif not path.isfile(key_path):
            sys.stderr.write('incorrect key path')
            exit(1)

        if not cert_path.endswith(".crt"):
            sys.stderr.write('first file must be cert')
            exit(1)
        elif not key_path.endswith(".key"):
            sys.stderr.write('second file must be key')
            exit(1)

        CLIENT_CERT = cert_path
        CLIENT_KEY = key_path
        print("** Used user certificate **")
    elif len(sys.argv) == 2 or len(sys.argv) > 3:
        sys.stderr.write('usage: client.py < .crt path> < .key path>')
        exit(1)

    # in case of WinError 10061 (Multiple connections in short time)
    while True:
        try:
            f = open(SERVER_TEMP, 'w')
            f.write(SERVER_CERT)
            f.close()

            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((HOST, PORT))

            cert_file = open(CLIENT_CERT)
            s.sendall(cert_file.read().encode())
            s.close()

            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((HOST, PORT))

            context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=SERVER_TEMP)
            context.load_cert_chain(certfile=CLIENT_CERT, keyfile=CLIENT_KEY)
            s = context.wrap_socket(s, server_side=False, server_hostname=SERVER_COMMON_NAME)
            break
        except ConnectionRefusedError:
            pass

    print("********************")
    print("Connected to server!")
    print("********************\n")

    try:
        # login
        USER_UUID = authorize(s)

        # run loop of new games
        start_game(s)

        # if returned - disconnect
        disconnect(s)
    except socket.error:
        print("Error")
