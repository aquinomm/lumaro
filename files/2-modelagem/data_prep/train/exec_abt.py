import os
import sqlalchemy
from sqlalchemy import text

TRAIN_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PREP_DIR = os.path.dirname(TRAIN_DIR)
BASE_DIR = os.path.dirname(DATA_PREP_DIR)
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(BASE_DIR)), 'files','data')

engine = sqlalchemy.create_engine("sqlite:///" + os.path.join(DATA_DIR, 'banco_de_dados.db'))

with open(os.path.join(TRAIN_DIR, 'abt.sql'), 'r') as open_file:
    query = open_file.read()


with engine.connect() as con:
    for i in query.split(';')[:-1]:
        if i.strip(): 
            con.execute(text(i))
            con.commit()
