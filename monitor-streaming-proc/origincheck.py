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
from datetime import date, timedelta

#### GENERAL CONFIG ####

with open('./config/config.json') as config_file:
    data_config = json.load(config_file)

with open('./config/stationConfig.json') as station_file:
    station_config = json.load(station_file)

env_app = os.getenv('GUARDIAN_PROC_ENV')
#######

#### REDIS CONFIG ####

rd = redis.Redis(
    host=data_config[env_app]['REDIS-HOST'],
    port=data_config[env_app]['REDIS-PORT'],
    decode_responses=True)
#######


def check_status(station, timevalue, fileuri, datefile):

	cmd = 'ffprobe -i ' + fileuri + ' -show_entries format=duration -v quiet -of csv="p=0"'
	argscmd = shlex.split(cmd)
	ts = int(time.time())
	date_message = datetime.datetime.fromtimestamp(ts).strftime('%Y - %m - %d')
	time.sleep(60)
	verify_time = check_audio(argscmd)
	print("======= VERIFY TIME")
	print(verify_time)
	ip = ni.ifaddresses('eth0')[ni.AF_INET][0]['addr']
	origin_status = rd.get("origin-status-"+station+ip)
	print("======= ORIGIN STATUS")
	print(origin_status)
	date_now = datetime.datetime.fromtimestamp(ts).strftime('%Y%m%d')

	if date_now == datefile:
		if float(verify_time) == float(origin_status):
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
							"text": "*Tipo:* Origen de Audio\n*Estación:* " + station_config[env_app][station]['station-name'] + "\n *Fecha:* " + date_message + "\n *Archivo:* " + fileuri + "\n *Archivo Tiempo:* " + str(float(timevalue)/3600) + "\n*Commentario:* \"Revisar servidor: " + ip + " - pro-cutter-proc en AWS!\""
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
			print("===== REC AUDIO")
			cmdrec = 'python36 /opt/cutter/cutterapp/cutter_rec.py -s ' + station_config[env_app][station]['proc-id'] + ' -r audio -d ' + station_config[env_app][station]['dir-audio']
			argsrec = shlex.split(cmdrec)
			print(argsrec)
			rec_back = subprocess.Popen(argsrec, stderr=subprocess.STDOUT).decode('utf-8')
			print(rec_back)
			return "Slack Alert"
		else:
			return "No problems at all"
	else:
		return "Not the same date"

def check_audio(audiodata):

	monitor_exec = subprocess.check_output(audiodata, stderr=subprocess.STDOUT).decode('utf-8')
	out = json.loads(monitor_exec)
	print(out)
	return out

def ffprobe_checkaudio(station, originaudio):

	ts = int(time.time())
	date_file = datetime.datetime.fromtimestamp(ts).strftime('%Y%m%d')
	audio_file = originaudio + 'http-' + date_file + '.mp3'
	cmd = 'ffprobe -i ' + audio_file + ' -show_entries format=duration -v quiet -of csv="p=0"'

	args = shlex.split(cmd)
	print(audio_file)
	print(args)

	try:
		ip = ni.ifaddresses('eth0')[ni.AF_INET][0]['addr']
		audio_check = check_audio(args)
		rd.set("origin-status-"+station+ip, audio_check)
		status = check_status(station, audio_check, audio_file, date_file)
		print(status)

	except IOError as proc_error:
		print(proc_error)
		return proc_error


def main(station):
	print("===== AUDIO ORIGIN CHECK")
	print(station)
	try:
		print(station_config[env_app][station]['dir-audio'])
		ffprobe_checkaudio(station, station_config[env_app][station]['dir-audio'])
	except IOError as e:
		print(e)

if __name__ == '__main__':
    main(sys.argv[1])