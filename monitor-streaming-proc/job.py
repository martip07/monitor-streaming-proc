import json, os
import time
import redis
from rq import Queue, use_connection
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

def main():
    #use_connection()
    #qs = Queue('registerstatus', connection=r)
    stations = station_list()
    for station in stations:
        qs = Queue(station, connection=r)
        #qs_job = qs.enqueue(check_silence, station)
        try:
            qs_job = qs.enqueue_call(func=check_silence, args=(station,), timeout=360)
            print(qs_job)
        except IOError as qs_error:
            print(qs_error)
            pass

        #print(qs_job)
    time.sleep(60)

if __name__ == '__main__':
    main()
