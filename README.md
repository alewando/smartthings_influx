# SmartThings to InfluxDB service

A simple python script (wrapped up as a systemd serivce) for recording data from SmartThings devices to InfluxDB.
It uses the SmartThings REST API to poll your devices' status. For specific device types (temperature/humidity sensors, etc),
data points will be published to an InfluxDB instance.

