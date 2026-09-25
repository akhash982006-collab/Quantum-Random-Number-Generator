import json
import sqlite3
from pathlib import Path
import numpy as np

DEFAULT_DB=Path(__file__).resolve().parents[1]/'data'/'sessions.sqlite3'

def connect(path=DEFAULT_DB):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    con=sqlite3.connect(path)
    con.execute('CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, timestamp TEXT, name TEXT, payload TEXT)')
    return con

def save(result,path=DEFAULT_DB,bits=None):
    with connect(path) as con:
        con.execute('INSERT OR REPLACE INTO sessions VALUES (?,?,?,?)',(result['session_id'],result['timestamp'],result['metadata'].get('name','Dataset'),json.dumps(result,allow_nan=False)))
    if bits is not None:
        folder=Path(path).parent/'retained'; folder.mkdir(exist_ok=True)
        np.save(folder/(result['session_id']+'.npy'),bits)

def sessions(path=DEFAULT_DB):
    with connect(path) as con:
        return [dict(id=r[0],timestamp=r[1],name=r[2]) for r in con.execute('SELECT id,timestamp,name FROM sessions ORDER BY timestamp DESC')]

def load(session_id,path=DEFAULT_DB):
    with connect(path) as con:
        row=con.execute('SELECT payload FROM sessions WHERE id=?',(session_id,)).fetchone()
    return json.loads(row[0]) if row else None
