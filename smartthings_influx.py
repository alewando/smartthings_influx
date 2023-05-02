#!/usr/bin/env python3 
import schedule
import requests
from influxdb import InfluxDBClient
import logging
import os
import time
import dateutil.parser

# Polls smartthings API and posts data to influxDB
# Attempting to mimick measurements, tags, and fields from old SmartThings influxDB-logger (for data 
# continuity) at
# https://github.com/codersaur/SmartThings/blob/master/smartapps/influxdb-logger/influxdb-logger.groovy


LOG_FORMAT = "%(asctime)-15s %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
#logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT)


# Get the API key from an environment variable. 
# If using the systemd service, you can put this in /etc/default/smartthings_influx (SMARTTHINGS_API_KEY=xxxx)
SMARTTHINGS_API_KEY = os.getenv("SMARTTHINGS_API_KEY", None)
if not SMARTTHINGS_API_KEY:
    logging.error(f"No SmartThings API key specified. Set the SMARTTHINGS_API_KEY environment variable. Obtain API key from https://account.smartthings.com/tokens")
    exit(1)

# SmartThings API expects an "Authentication" header with the value
# "Bearer: <api key>"
KEY = "Bearer " + SMARTTHINGS_API_KEY

# Influx configuration
INFLUX_HOST = os.getenv("INFLUX_NAME", "localhost")
INFLUX_DATABASE = os.getenv("INFLUX_DATABASE", "SmartThings")


class DeviceInfo(object):
    def __init__(self, device_data):
        self.device_id = device_data.get('deviceId')
        self.device_name = device_data.get('label')

def process_devices():
    logging.debug("Getting devices")
    r = requests.get(
        "https://api.smartthings.com/v1/devices", headers={"Authorization": KEY}
    )

    influx_data_points = []
    json = r.json()
    devices = json.get("items",[])
    for device in devices:
        new_device = DeviceInfo(device)

        logging.debug(f"device: {new_device.device_name}") 
        # Get device status
        status = requests.get(
            f"https://api.smartthings.com/v1/devices/{new_device.device_id}/status",
            headers={"Authorization": KEY},
        )
        status_data = status.json()
        #logging.debug(f"status_json={status_json}")
        device_data_points = device_status_to_influx_points(new_device, status_data)
        influx_data_points.extend(device_data_points)
        logging.debug("-------------------------------------------------")

    post_to_influx(influx_data_points)
    #logging.info(f"Completed run with {influx_counted}/{len(devices) - 1} sensors uploaded successfully")


def device_status_to_influx_points(device_info, status_data):
# Sample device status JSON:
# {
#   "components": {
#     "main": {
#       "relativeHumidityMeasurement": {
#         "humidity": {
#           "value": 35,
#           "unit": "%",
#           "timestamp": "2023-04-11T22:23:03.111Z"
#         }
#       },
#     }
# }
    points = []

    components = status_data.get('components', {}).get('main',{})
    for component_name, component_data in components.items():
        logging.debug(f"component: {component_name}; data: {component_data}")
        if component_name == "relativeHumidityMeasurement":
            measurement_data = component_data.get('humidity', {})
            value = measurement_data.get('value', None)
            time = measurement_data.get('timestamp', None)
            if value and value >= 0 and value <= 100:
                points.append(create_point(device_info, "humidity", value, time))
        if component_name == "temperatureMeasurement":
            measurement_data = component_data.get('temperature', {})
            value = measurement_data.get('value', None)
            time = measurement_data.get('timestamp', None)
            if value and value >= 0 and value <= 110:
                points.append(create_point(device_info, "temperature", value, time))
        if component_name == "battery":
            measurement_data = component_data.get('battery', {})
            value = measurement_data.get('value', None)
            time = measurement_data.get('timestamp', None)
            if value and value >=0 and value <= 100:
                points.append(create_point(device_info, "battery", value, time))
        if component_name == "switch":
            measurement_data = component_data.get('switch', {})
            value = measurement_data.get('value', None)
            time = measurement_data.get('timestamp', None)
            if value:
                if value == "on":
                    value = 1
                else:
                    value = 0
                points.append(create_point(device_info, "switch", value, time))
        if component_name == "switchLevel":
            measurement_data = component_data.get('level', {})
            value = measurement_data.get('value', None)
            time = measurement_data.get('timestamp', None)
            if value:
                points.append(create_point(device_info, "switchLevel", value, time))

    logging.debug(f"Created points: {points}")

    return points

def create_point(device, measurement_name, value, time=None):
    point = { 
        "measurement": measurement_name, 
        "tags": {
            "deviceId": device.device_id,
            "deviceName": device.device_name
        }, 
        "fields": {
            "value": value
        }
    }
    if time:
        converted_time = dateutil.parser.isoparse(time).strftime('%Y-%m-%dT%H:%M:%SZ')
        point["time"]=converted_time

    return point

#
# Writing to Influx using the Python API (https://influxdb-python.readthedocs.io/en/latest/api-documentation.html#influxdb.InfluxDBClient.write_points):
#  client = InfluxDBClient(INFLUX_HOST, 8086, database=INFLUX_DATABASE)
#  client.write_points([
#   {
#     "measurement": "myMeasurement",
#     "tags": {"deviceId": f"{xxx}"},
#     "fields": {
#         "xyz": "val"
#     },
#      "time": "2009-11-10T23:00:00Z"
#   },
#   ...
#  ]
# }
def post_to_influx(data_points):
    logging.info(f"Posting {len(data_points)} data points to {INFLUX_HOST}:{INFLUX_DATABASE}")
    client = InfluxDBClient(INFLUX_HOST, 8086, database=INFLUX_DATABASE)
    result = client.write_points(data_points, time_precision='s')
    if not result:
        logging.error(f"Write to influxdb failed. Points: {data_points}")
    logging.debug(f"Post complete")

process_devices()

schedule.every(5).minutes.do(process_devices)
# schedule.every(5).seconds.do(process_devices)
while True:
    schedule.run_pending()
    time.sleep(1)
