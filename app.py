#!/usr/bin/env python3

from datetime import datetime
from flask import Flask, request, stream_with_context
from hashlib import sha256
import json
import secrets
import sqlite3
import threading
import time

lock = threading.Lock()

db = sqlite3.connect('database.db', check_same_thread=False)

dbc = db.cursor()

dbc.execute('''
    CREATE TABLE IF NOT EXISTS mutexes (
        id TEXT PRIMARY KEY,
        password TEXT NOT NULL,
        expiration TEXT NOT NULL,
        taken INTEGER DEFAULT 1
    );
    ''')
db.commit()



app = Flask(__name__)

def get_status(req_id, req_password):
    hashed_password = sha256(req_password.encode()).hexdigest()
    with lock:
        dbc.execute('''SELECT taken FROM mutexes
                       WHERE id = ? AND password = ?''',
                       (req_id, hashed_password))
        records = dbc.fetchall()
    if len(records) == 1:
        return {'status': 'ok', 'taken': records[0][0]}

    return {'status': 'fail'}


@app.route('/status', methods=['GET', 'POST'])
def status():
    data = request.get_json(silent=True) or request.values
    req_id = data.get('id')
    req_password = data.get('password')

    status = get_status(req_id, req_password)
    return status, 200 if status['status'] == 'ok' else 401


@app.route('/monitor', methods=['GET', 'POST'])
def monitor():
    # TODO: flask supports websockets, maybe use that instead?

    # TODO: maybe change this into a subscribe_and_grab that takes an endpoint
    #       to contact when the mutex is released and grabs it for you?
    #       or maybe keep a separate monitor api just for observabiilty

    data = request.get_json(silent=True) or request.values
    req_id = data.get('id')
    req_password = data.get('password')

    def loop():
        while True:
            yield json.dumps(get_status(req_id, req_password)) + '\n'
            time.sleep(1)
    return stream_with_context(loop())


# TODO: implement auto expiration
#       check with datetime.fromisoformat() or sqlite's datetime()?
#       also, how to wake up monitors?

# TODO: user-settable/resettable expiration date?
#       maybe a keep_alive endpoint that autoexpires if no contact for a while?


@app.route('/grab', methods=['POST'])
def grab():
    data = request.get_json(silent=True) or request.values
    req_id = data.get('id')
    req_password = data.get('password')

    if req_id in [None, 'new']:
        while True:
            req_id = secrets.token_hex(16)
            req_password = secrets.token_hex(16)
            hashed_password = sha256(req_password.encode()).hexdigest()
            with lock:
                dbc.execute('''INSERT INTO mutexes (id, password, expiration)
                               VALUES (?, ?, ?)
                               ON CONFLICT(id) DO NOTHING''',
                               (req_id, hashed_password, datetime.now().isoformat()))
                db.commit()
                if dbc.rowcount == 1:
                    break
        return {'id': req_id, 'password': req_password}

    if req_password is not None:
        # TODO: loop and wait for thing to be unlocked?

        # TODO: password must be changed every time, otherwise
        #       - user1 grabs mutex
        #       - user1 forgets to unlock
        #       - mutex expires
        #       - user2 grabs mutex
        #       - user1 decides to unlock
        #       - user1 unlocks user2's mutex!
        #       solution: generate a new password
        hashed_password = sha256(req_password.encode()).hexdigest()
        with lock:
            dbc.execute('''INSERT INTO mutexes (id, password, expiration)
                           VALUES (?, ?, ?)
                           ON CONFLICT(id) DO NOTHING''',
                           (req_id, hashed_password, datetime.now().isoformat()))
            db.commit()
    return {'status': 'fail'}, 400


@app.route('/release', methods=['POST'])
def release():
    data = request.get_json(silent=True) or request.values
    req_id = data.get('id')
    req_password = data.get('password')

    if req_id is not None and req_password is not None:
        hashed_password = sha256(req_password.encode()).hexdigest()
        with lock:
            dbc.execute('''UPDATE mutexes SET taken = 0 WHERE id = ? AND password = ?''',
                        (req_id, hashed_password))
            db.commit()
            if dbc.rowcount == 1:
                return {'status': 'ok'}

    return {'status': 'fail'}, 400


if __name__ == '__main__':
   app.run(debug=True)
