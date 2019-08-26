import json, os
import subprocess
import boto3
import redis
import uuid
import datetime
import click
import time
from botocore.exceptions import ClientError

#### GENERAL CONFIG ####

with open('./config/config.json') as config_file:
    data_config = json.load(config_file)

with open('./config/streamConfig.json') as streamconfig_file:
    stream_config = json.load(streamconfig_file)

env_app = os.getenv('GUARDIAN_PROC_ENV')
#######

#### SES CONFIG ####

sesclient = boto3.client('ses', region_name=data_config[env_app]['AWS-REGION'])
aws_region = data_config[env_app]['AWS-REGION']
charset = "UTF-8"
#######


def alert_error(status, station_name, provider, timestamp, mediatype, stream_uri, station_id, date_time, alert_data):
    print("Ready to alert silence")
    print(type(data_config[env_app]['SES-RECIPIENT']))
    ts = int(time.time())
    date_alert = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
    time_alert = alert_data['time_alert']
    print(time_alert)
    sender = data_config[env_app]['SES-SENDER']
    recipient = data_config[env_app]['SES-RECIPIENT']
    #https://s3.amazonaws.com/guardian-img-env/dev/radio-demo-2019-03-11.png
    image_chart = 'https://s3.amazonaws.com/guardian-img-env/'+ alert_data['s3_key']
    subject = f"Alerta streaming - {station_name}"
    body_html = f"""<html>
    <head></head>
    <body>
    <h2>Guardian Status Monitor</h2>
    <p><img src={image_chart} /></p>
    <p><strong>Estación: </strong> {station_name} - {mediatype} </p>
    <p><strong>Alerta: </strong> {status} - sin audio en el streaming</p>
    <p><strong>Fecha: </strong> {date_alert} {time_alert}</p>
    <p><strong>URL: </strong> {stream_uri}</p>
    </body>
    </html>
                """

    try:
        response = sesclient.send_email(
            Destination={
                'ToAddresses': recipient
            },
            Message={
                'Body': {
                    'Html': {
                        'Charset': charset,
                        'Data': body_html
                    }
                },
                'Subject': {
                    'Charset': charset,
                    'Data': subject
                }
            },
            Source=sender
           # ConfigurationSetName=confiuration_set
        )
    except ClientError as e:
        print("Error: " + e.response['Error']['Message'])
    else:
        print("Email sent, message id: " + response['MessageId'])