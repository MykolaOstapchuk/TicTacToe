import sqlite3


class DataBase:
    # db name
    databaseName = 'test.db'
    # connection object
    con = None

    # queries
    q_create_table = '''
                CREATE TABLE users
                (id integer primary key autoincrement,
                login text,
                password text)
                '''
    q_remove_table = 'DROP TABLE IF EXISTS users'

    # methods:
    # create connection
    def connect(self):
        self.con = sqlite3.connect(self.databaseName)

    # commit db changes
    def commit(self):
        self.con.commit()

    # close connection
    def close(self):
        self.con.close()

    # create table
    def createTable(self):
        cur = self.con.cursor()
        cur.execute(self.q_create_table)

    # remove table
    def removeTable(self):
        cur = self.con.cursor()
        cur.execute(self.q_remove_table)

    # register user - returns user id or False
    def register(self, login, password):
        cur = self.con.cursor()
        if len(self.checkUser(login)):
            return False
        cur.execute(f"INSERT INTO users VALUES (NULL, '{login}', '{password}')")
        self.commit()
        return self.login(login, password)

    # check if user exists - returns tuple (id, password)
    def checkUser(self, login):
        cur = self.con.cursor()
        return cur.execute(f"SELECT id, password FROM users WHERE login = '{login}'").fetchall()

    # log in user - gets tuple, compares password and returns user id or False
    def login(self, login, password):
        user = self.checkUser(login)
        if len(user) != 0 and user[0][1] == password:
            return user[0][0]
        return False
