#!/usr/bin/env python3

from datetime import datetime
import flask
import json
import secrets
import sqlite3
import time

# FIXME: check_same_thread=False is not a solution! sync somewhere else!
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



app = flask.Flask(__name__)

def get_status(req_id, req_password):
    dbc.execute('''SELECT taken FROM mutexes
                   WHERE id = ? AND password = ?''',
                   (req_id, req_password))
    records = dbc.fetchall()
    if len(records) == 1:
        return {'status': 'ok', 'taken': records[0][0]}

    return {'status': 'fail'}


@app.route('/status')
def status():
    req_id = flask.request.values.get('id')
    req_password = flask.request.values.get('password')

    status = get_status(req_id, req_password)
    return status, 200 if status['status'] == 'ok' else 401


@app.route('/monitor', methods=['GET'])
def monitor():
    # TODO: flask supports websockets, maybe use that instead?

    # TODO: check if this keeps things busy

    # TODO: maybe change this into a subscribe_and_grab that takes an endpoint
    #       to contact when the mutex is released and grabs it for you?
    #       or maybe keep a separate monitor api just for observabiilty

    req_id = flask.request.values.get('id')
    req_password = flask.request.values.get('password')

    def loop():
        while True:
            yield json.dumps(get_status(req_id, req_password)) + '\n'
            time.sleep(1)
    return flask.stream_with_context(loop())


# TODO: implement auto expiration
#       check with datetime.fromisoformat() or sqlite's datetime()?
#       also, how to wake up monitors?

# TODO: user-settable/resettable expiration date?
#       maybe a keep_alive endpoint that autoexpires if no contact for a while?


@app.route('/grab', methods=['POST'])
def grab():
    req_id = flask.request.values.get('id')

    if req_id in [None, 'new']:
        while True:
            req_id = secrets.token_hex(16)
            req_password = secrets.token_hex(16)
            dbc.execute('''INSERT INTO mutexes (id, password, expiration)
                           VALUES (?, ?, ?)
                           ON CONFLICT(id) DO NOTHING''',
                           (req_id, req_password, datetime.now().isoformat()))
            db.commit()
            if dbc.rowcount == 1:
                break
        return flask.jsonify({'id': req_id, 'password': req_password})

    req_password = flask.request.values.get('password')

    if req_password is not None:
        dbc.execute('''INSERT INTO mutexes (id, password, expiration)
                       VALUES (?, ?, ?)
                       ON CONFLICT(id) DO NOTHING''',
                       (req_id, req_password, datetime.now().isoformat()))
        db.commit()
    return flask.jsonify({'status': 'fail'}), 400


@app.route('/release', methods=['POST'])
def release():
    req_id = flask.request.values.get('id')
    req_password = flask.request.values.get('password')

    if req_id is not None and req_password is not None:
        dbc.execute('''UPDATE mutexes SET taken = 0 WHERE id = ?, password = ?''',
                    (req_id, req_password))
        db.commit()
        if dbc.rowcount == 1:
            return flask.jsonify({'status': 'ok'})

    return flask.jsonify({'status': 'fail'}), 400


if __name__ == '__main__':
   app.run(debug=True)
