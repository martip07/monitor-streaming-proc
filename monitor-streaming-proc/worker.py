import json, os
import time
import redis
from rq import Queue, use_connection, Worker, Connection
from app import check_silence

#### GENERAL CONFIG ####

with open('./config/config.json') as config_file:
    data_config = json.load(config_file)

with open('./config/streamConfig.json') as streamconfig_file:
    stream_config = json.load(streamconfig_file)

env_app = os.getenv('GUARDIAN_PROC_ENV')
#######


#### REDIS CONFIG ####

r = redis.Redis(
    host=data_config[env_app]['REDIS-HOST'],
    port=data_config[env_app]['REDIS-PORT'],
    decode_responses=True)
#######


def station_list():
    station_list = []
    for station in stream_config[env_app]:
        station_list.append(station)
    print(station_list)
    return station_list

#use_connection()
#q = Queue('rpp-radio', connection=r)
#print(len(q))

#q.delete(delete_jobs=True)

def main():
    #use_connection()
    #qs = Queue('high', connection=r)
    stations = station_list()
    #for station in stations:
    with Connection():
        qs = stations

        w = Worker(qs)
        w.work()
#q.delete(delete_jobs=True)
if __name__ == '__main__':
    main()