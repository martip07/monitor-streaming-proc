import json, os
import subprocess
import boto3
import redis
import uuid
import datetime
import click
import time
from rethinkdb import RethinkDB
from rethinkdb.errors import RqlRuntimeError
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError
from charts import create_chartguardian


#### GENERAL CONFIG ####

with open('./config/config.json') as config_file:
    data_config = json.load(config_file)

with open('./config/streamConfig.json') as streamconfig_file:
    stream_config = json.load(streamconfig_file)

env_app = os.getenv('GUARDIAN_PROC_ENV')
#######


#### DYNAMODB CONFIG ####

dynamodb = boto3.resource('dynamodb', region_name=data_config[env_app]['AWS-REGION'])
table = dynamodb.Table(data_config[env_app]['DYNAMO-TABLE'])
#######


#### RETHINKDB CONFIG ####

drt = RethinkDB()
#connection = drt.connect(db=data_config[env_app]['RETHINK-DB'])
#######


#### REDIS CONFIG ####

rd = redis.Redis(
    host=data_config[env_app]['REDIS-HOST'],
    port=data_config[env_app]['REDIS-PORT'],
    decode_responses=True)
#######


#### STREAMING CONFIG ####

#######

def write_statusRDB(station, value_status, connec):

    ts = int(time.time())
    date_day = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
    #with drt.connect(db=data_config[env_app]['RETHINK-DB']) as conn:
    cursor = drt.table(data_config[env_app]['RETHINK-TABLE']).filter((drt.row["date"] == date_day) & (drt.row["station_id"] == stream_config[env_app][station]['station-id'])).count().run(connec)
        #print("================= CURSOR=======")
        #print(cursor)
        
    #station_name = stream_config[env_app][station]['station-name']
    #provider = stream_config[env_app][station]['provider']
    #mediatype = stream_config[env_app][station]['media-type']
    #stream_uri = stream_config[env_app][station]['uri-stream']
    id_station = stream_config[env_app][station]['station-id']
    status_array = list()
    status_arrayValue = dict()
    status = str()

    if value_status == 1:
        status = "up"
    else:
        status = "down"
        result_alert = create_chartguardian(id_station, station)
            #alert_error(status, station_name, provider, ts, mediatype, stream_uri, id_station, date_day, s3_key)
        print(result_alert)
        print("=========== Verify DynamoDB")

    status_arrayValue = {  'status': status, 'time': ts  }
    print(status_arrayValue)
    status_array = [status_arrayValue]

    print(status_array)

    if cursor == 0:
        try:
            Item = {
                'uid': str(uuid.uuid4()),
                'date': date_day,
                'timestamp': ts,
                'mediatype': stream_config[env_app][station]['media-type'],
                'station_name': stream_config[env_app][station]['station-name'],
                'station_id': stream_config[env_app][station]['station-id'],
                'stream_status': status,
                'status_array': status_array,
                'provider': stream_config[env_app][station]['provider']
            }
                #with drt.connect(db=data_config[env_app]['RETHINK-DB']) as conn:
            write_item = drt.table(data_config[env_app]['RETHINK-TABLE']).insert(Item).run(connec)
            print(write_item)
            #connection.close()
            return write_item
        except RqlRuntimeError as db_error:
            print(db_error)
            return db_error
    else:
        #with drt.connect(db=data_config[env_app]['RETHINK-DB']) as conn:
        cursor_update = drt.table(data_config[env_app]['RETHINK-TABLE']).filter((drt.row["date"] == date_day) & (drt.row["station_id"] == stream_config[env_app][station]['station-id'])).run(connec)
        id_item = str()
        status_array = list()
        for document in cursor_update:
            id_item = document['id']
            status_array = document['status_array']
                
            print(id_item)
            print(status_array)
            update_statusArray = status_array
            print(len(update_statusArray))
            print(update_statusArray.insert(len(update_statusArray), status_arrayValue))

        try:
            Item = {
                    'timestamp': ts,
                    'stream_status': status,
                    'status_array': status_array
            }
                    #with drt.connect(db=data_config[env_app]['RETHINK-DB']) as conn:
            update_item = drt.table(data_config[env_app]['RETHINK-TABLE']).filter(drt.row['id'] == id_item).update(Item).run(connec)
            print(update_item)
            #connection.close()
            return update_item
        except RqlRuntimeError as db_error:
            print(db_error)
            return db_error

def get_volumeStatus(station):
    print("Get Volume Status=========")
    print(station)
    volume_status = rd.get("volume_lastStatus_"+station)
    if volume_status is None:
        print("It is none")
        volume_status = 1
        return volume_status
    else:
        print(volume_status)
        return volume_status
    #print(volume_status)
    #print(type(volume_status))
    #return volume_status

def check_regexVolume(out_value):
    for volume_i in out_value:
        if "mean_volume" in volume_i:
            print(volume_i)
            return volume_i

def ffmpeg_checkaudio(station, audio_uri):
    cmd = ["ffmpeg", "-t", "10", "-i", audio_uri, "-af", "'volumedetect'", "-f", 'null', "\/dev\/null"]

    try:
        monitor_exec = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        out = str(monitor_exec).split("\\n")
        #out_data = out[38].split(" ")
        new_volume_arr = check_regexVolume(out)
        out_data = new_volume_arr.split(" ")
        out_value = out_data[4]
        print(out_value)
        #return out_value
        #out_value = str(-60)
        check_data = check_volume(station, out_value)
        return check_data
    except IOError as proc_error:
        print(proc_error)
        pass


def check_volume(station, volume_value):
    print(volume_value)
    if float(volume_value) > float(-50):
        volume_status = 1
        #Compare volume_status with previously stored volume_status (It is False)
        last_volumeStatus = get_volumeStatus(station)
        print("======= FIRST")
        print(last_volumeStatus)
        print(type(str(last_volumeStatus)))
        if volume_status == int(last_volumeStatus):
            print("======= FIRST IF")
            message = "Volume status: " + str(volume_status) + ". Valores correctos. El valor actual es de " + volume_value
            print(message)
            rd.set("volume_lastStatus_"+station, volume_status)
            with drt.connect(db=data_config[env_app]['RETHINK-DB']) as conn:
                write_statusRDB(station, volume_status, conn)
                #print(write_s)
                return message
            #return message
        else:
            # Save error status on DB
            print("======= FIRST ELSE")
            last_volumeStatus = get_volumeStatus(station)
            print(last_volumeStatus)
            volume_status = 1
            message = "Volume status: " + str(volume_status) + ". Valores correctos. El valor actual es de " + volume_value
            print(message)
            with drt.connect(db=data_config[env_app]['RETHINK-DB']) as conn:
                write_statusRDB(station, volume_status, conn)
                #print(write_s)
                return message
    else:
        volume_status = 0
        last_volumeStatus = get_volumeStatus(station)

        if volume_status == int(last_volumeStatus):
            print("======= SECOND IF")
            message = "Volume status: " + str(volume_status) + ". Silencio, no se tiene audio. El valor actual es de " + volume_value
            print(message)
            rd.set("volume_lastStatus_"+station, volume_status)
            with drt.connect(db=data_config[env_app]['RETHINK-DB']) as conn:
                write_statusRDB(station, volume_status, conn)
                #print(write_s)
                return message
        else:
            print("======= SECOND ELSE")
            message = "Volume status: " + str(volume_status) + ". Silencio, no se tiene audio. El valor actual es de " + volume_value
            print(message)
            rd.set("volume_lastStatus_"+station, volume_status)
            with drt.connect(db=data_config[env_app]['RETHINK-DB']) as conn:
                write_statusRDB(station, volume_status, conn)
                #print(write_s)
                return message

#@click.command()
#@click.option('--station', help='Nombre configurado en el archivo streamConfig.json')
def check_silence(station):

    try:
        print(stream_config[env_app][station]['uri-stream'])
        ffmpeg_checkaudio(station, stream_config[env_app][station]['uri-stream'])
    except IOError as e:
        print(e)


#check_silence()
#if __name__ == '__main__':
#    check_silence()