# SmartThings to InfluxDB service

A simple python script (wrapped up as a systemd serivce) for recording data from SmartThings devices to InfluxDB.
It uses the SmartThings REST API to poll your devices' status. For specific device types (temperature/humidity sensors, etc),
data points will be published to an InfluxDB instance.

## Running as a service
* [Obtain a SmartThings API key](https://account.smartthings.com/tokens) (only needs read access)
* `/etc/default/smartthings_influx`:
  ```
  SMARTTHINGS_API_KEY=xxxxx
  INFLUX_HOSTNAME=localhost
  INFLUX_DATABASE=SmartThings
  ```
* Link systemd unit file
  ```sudo ln -s /usr/local/src/smarthings_influx/smartthings_influx.service /etc/systemd/system/smartthings_influx.service```
* Link logrotate config
  ```sudo ln -s /usr/local/src/smarthings_influx/smartthings_influx.logrotate /etc/logrotate.d/smartthings_influx```