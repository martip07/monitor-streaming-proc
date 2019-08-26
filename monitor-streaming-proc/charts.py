import os
import json
from rethinkdb import RethinkDB
import datetime
import leather
import time
import boto3
from datetime import date, timedelta
import cairosvg
import pygal
from pygal.style import Style
from pygal import Config
from alerts import alert_error
from slackalerts import streaming_alert

#### GENERAL CONFIG ####

with open('./config/config.json') as config_file:
    data_config = json.load(config_file)

with open('./config/streamConfig.json') as streamconfig_file:
    stream_config = json.load(streamconfig_file)

env_app = os.getenv('GUARDIAN_PROC_ENV')
#######


#### RETHINKDB CONFIG ####

drt = RethinkDB()
#connection = drt.connect(db='StreamingMonitor')
#######


#### S3 CONFIG ####

s3 = boto3.client('s3', region_name=data_config[env_app]['AWS-REGION'])
bucket_name = data_config[env_app]['S3-BUCKET']
#######


def create_chartguardian(id_station, station):

    data_status = dict()
    data_time = dict()
    list_status = list()
    list_time = list()
    station_name = str()
    station_id = str()
    data_down = list()
    data_up = list()
    data_label = list()
    last_problem = str()
    status_alert = str()
    provider_alert = str()
    mediatype_alert = str()
    streamuri_alert = str()
    stationid_alert = str()

    ts = int(time.time())
    date_query = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d')

    with drt.connect(db=data_config[env_app]['RETHINK-DB']) as conn:
        cursor_up = drt.table(data_config[env_app]['RETHINK-TABLE']).filter((drt.row["date"] == date_query) & (drt.row["station_id"] == id_station)).run(conn)
        cursor_down = drt.table(data_config[env_app]['RETHINK-TABLE']).filter((drt.row["date"] == date_query) & (drt.row["station_id"] == id_station)).run(conn)

        for document_down in cursor_down:
            station_name = document_down["station_name"]
            station_id = document_down["station_id"]
            if len(document_down["status_array"]) < 31:
                print("Size array status DOWN")
                print(len(document_down["status_array"]))
                start_point = 0
            else:
                start_point = len(document_down["status_array"]) - 31
            stat_array = document_down["status_array"]
            provider_alert = document_down["provider"]
            mediatype_alert = stream_config[env_app][station]['media-type']
            streamuri_alert =  stream_config[env_app][station]['uri-stream']
            stationid_alert = id_station
            for index, item in enumerate(stat_array[start_point:]):
                status_len = len(document_down["status_array"])
                ts = int(item["time"])
                date_down = datetime.datetime.fromtimestamp(ts).strftime('%H:%M:%S')
                #[None, None, None, None, None, None, {'value': 0, 'label': '10:10:10'}
                if item["status"] == "down":
                    item_down = {
                        'value': 0,
                        'label': date_down
                    }
                    item_label = date_down
                    data_down.append(item_down)
                    data_label.append(item_label)
                    last_problem = date_down
                    status_alert = item["status"]
                else:
                    item_none = None
                    data_down.append(item_none)
                    item_label = None
                    data_label.append(item_label)
                ts = int(item["time"])
                date_day = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
                data_status.update({ index: item["status"] })
                data_time.update({ index: date_day })
                list_status.append(item["status"])
                list_time.append(date_day)

        for document_up in cursor_up:
            print("==== document_up ===")
            print(document_up)
            station_name = document_up["station_name"]
            station_id = document_up["station_id"]
            if len(document_up["status_array"]) < 31:
                print("Size array status UP")
                len(document_up["status_array"])
                start_point = 0
            else:
                start_point = len(document_up["status_array"]) - 31
            stat_array = document_up["status_array"]
            for index, item in enumerate(stat_array[start_point:]):
                status_len = len(document_up["status_array"])
                #{'value': 1, 'label': ''}
                if item["status"] == "up":
                    print("====== ITEM STATUS =====")
                    print(item)
                    status_val = 1
                    status_label = "Sin Problemas"
                    item_up = {
                        'value': 1,
                        'label': ''
                    }
                    data_up.append(item_up)
                else:
                    status_val = 0
                    status_label = "Problemas"
                    item_down = None
                    data_up.append(item_down)

        try:
            custom_style = Style(
            opacity='.6',
            opacity_hover='.9',
            transition='400ms ease-in',
            label_font_family='Liberation Mono',
            label_font_size=8,
            major_label_font_size=10,
            colors=('#e74c3c', '#2980b9', '#e67e22', '#E87653', '#E89B53'))


            configpg = Config()
            configpg.human_readable = True
            configpg.fill = False
            configpg.x_title='Ultimo Problema: ' + last_problem
            configpg.show_y_labels=False
            configpg.legend_at_bottom_columns=False
            configpg.legend_at_bottom=True
            configpg.width=850
            configpg.height=400
            configpg.print_labels=False
            configpg.margin_bottom=30
            configpg.x_label_rotation=60
            configpg.range=(0, 1)
            configpg.show_y_labels=True
            configpg.pretty_print=True

            extra_args = {
                'ACL': 'public-read', 
                'CacheControl': 'no-cache, no-store, must-revalidate'
                }

            line_chart = pygal.Line(style=custom_style, config=configpg)
            line_chart.title = station_name + ' - ' + date_query
            line_chart.x_labels = (data_label)
            line_chart.x_labels_major = (data_label)
            line_chart.add('Problemas', data_down , allow_interruptions=True, dots_size=5, stroke_style={'width': 4, 'linecap': 'round', 'linejoin': 'round'})
            line_chart.add('Activo',data_up , allow_interruptions=True, show_dots=True, dots_size=5, stroke_style={'width': 4, 'linecap': 'round', 'linejoin': 'round'})
            line_chart.add('Rango: 30 minutos', None)
            line_chart.render_to_png(station_id + '-' + date_query + '.png')
            #connection.close()
            #connection.close()
            upload_s3 = s3.upload_file(station_id + '-' + date_query + '.png', bucket_name, env_app+'/'+station_id + '-' + str(ts) + '.png', ExtraArgs=extra_args)
            os.remove(station_id + '-' + date_query + '.png')
            print(last_problem)
            alert_data = {
                's3_key': env_app+'/'+station_id + '-' + str(ts) + '.png',
                'time_alert': last_problem
            }
            
            if status_alert == "down":
                #alert_error(status_alert, station_name, provider_alert, ts, mediatype_alert, streamuri_alert, stationid_alert, date_query, alert_data)
                streaming_alert(status_alert, station_name, provider_alert, ts, mediatype_alert, streamuri_alert, stationid_alert, date_query, alert_data)
                return alert_data
            else:
                message = "No se tiene data que mostrar"
                print(message)
                return message
        except IOError as e:
            print("Se tiene un problema")
            print(e)
            message = e
            return message

#create_chartguardian("tv-capital", "capital-tv")