import os
import json
import datetime
import subprocess
import time
import boto3
import sys
import shlex
import requests
import redis
import netifaces as ni
from rethinkdb import RethinkDB
from datetime import date, timedelta

#### GENERAL CONFIG ####

with open('./config/config.json') as config_file:
    data_config = json.load(config_file)

with open('./config/stationConfig.json') as station_file:
    station_config = json.load(station_file)

with open('./config/streamConfig.json') as streamconfig_file:
    stream_config = json.load(streamconfig_file)

env_app = os.getenv('GUARDIAN_PROC_ENV')
#######

#### REDIS CONFIG ####

rd = redis.Redis(
    host=data_config[env_app]['REDIS-HOST'],
    port=data_config[env_app]['REDIS-PORT'],
    decode_responses=True)
#######

#### RETHINKDB CONFIG ####

drt = RethinkDB()
#connection = drt.connect(db='StreamingMonitor')
#######


def streaming_alert(status, station_name, provider, timestamp, mediatype, stream_uri, station_id, date_time, alert_data):

	ts = int(time.time())
	date_alert = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
	time_alert = alert_data['time_alert']
	date_now = datetime.datetime.fromtimestamp(ts).strftime('%Y%m%d')

	try:
		print("Ready to send Alert!")
		payload = {
			"blocks": [
				{
					"type": "context",
					"elements": [
						{
			                "type": "mrkdwn",
			                "text": "*Problemas en AUDIOWATCH*"
						}
					]
				},
				{
					"type": "divider"
				},
				{
					"type": "section",
					"text": {
						"type": "mrkdwn",
						"text": "*Tipo:* " + status + " sin audio en el streaming\n*Estación:* " + station_name + " - " + mediatype + "\n *Fecha:* " + date_alert + " " + time_alert + "\n *Streaming Url:* " + stream_uri
					},
					"accessory": {
						"type": "image",
						"image_url": "https://ftp-extras.s3.amazonaws.com/bots/images/001-exclamation-mark.png",
						"alt_text": "Error !!"
					}
				}
			]
		}
		headers = {'Content-Type': 'application/json'}
		url = 'https://hooks.slack.com/services/' + data_config[env_app]['SLACK-CHANNEL']
		r = requests.post(url, data=json.dumps(payload), headers=headers)
		print(r)
		return "Slack Alert"
	except Exception as e:
		print(e)
		raise e