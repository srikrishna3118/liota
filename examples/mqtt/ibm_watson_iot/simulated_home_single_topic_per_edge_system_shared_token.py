# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------#
#  Copyright © 2015-2016 VMware, Inc. All Rights Reserved.                    #
#                                                                             #
#  Licensed under the BSD 2-Clause License (the “License”); you may not use   #
#  this file except in compliance with the License.                           #
#                                                                             #
#  The BSD 2-Clause License                                                   #
#                                                                             #
#  Redistribution and use in source and binary forms, with or without         #
#  modification, are permitted provided that the following conditions are met:#
#                                                                             #
#  - Redistributions of source code must retain the above copyright notice,   #
#      this list of conditions and the following disclaimer.                  #
#                                                                             #
#  - Redistributions in binary form must reproduce the above copyright        #
#      notice, this list of conditions and the following disclaimer in the    #
#      documentation and/or other materials provided with the distribution.   #
#                                                                             #
#  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"#
#  AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE  #
#  IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE #
#  ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE  #
#  LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR        #
#  CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF       #
#  SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS   #
#  INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN    #
#  CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)    #
#  ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF     #
#  THE POSSIBILITY OF SUCH DAMAGE.                                            #
# ----------------------------------------------------------------------------#

import random

import pint
from linux_metrics import cpu_stat

from liota.dccs.generic_mqtt import GenericMqtt
from liota.dcc_comms.mqtt_dcc_comms import MqttDccComms
from liota.lib.transports.mqtt import MqttMessagingAttributes, QoSDetails
from liota.entities.metrics.metric import Metric
from liota.entities.devices.simulated_device import SimulatedDevice
from liota.entities.edge_systems.dell5k_edge_system import Dell5KEdgeSystem
from liota.lib.utilities.utility import Credentials, TLSConf

# Getting IBM Platform related values from conf file
config = {}
execfile('samplePropSharedToken.conf', config)

# create a pint unit registry
ureg = pint.UnitRegistry()


#  Reading CPU Utilization.
def read_cpu_utilization(sample_duration_sec=1):
    cpu_pcts = cpu_stat.cpu_percents(sample_duration_sec)
    return round((100 - cpu_pcts['idle']), 2)


#  Random number generator, simulating living room temperature readings.
def living_room_temperature():
    return random.randint(10, 30)


#  Random number generator, simulating living room humidity readings.
def living_room_humidity():
    return random.randint(70, 90)


#  Random number generator, simulating living room luminous readings.
def living_room_luminance():
    # 0 - Lights Off, 1 - Lights On
    return random.randint(0, 1)

# ----------------------------------------------------------------------------------------------------------------
# In this example, we demonstrate how data for a simulated metric generating
# random numbers can be directed to GenericMqtt data center component using Liota.
#
# A Simulated DHT sensor with Temperature and Humidity Metrics and a Simulated
# Digital Light sensor with binary luminance Metrics are used.
#
#
#                                            Dell5kEdgeSystem
#                                                   |
#                                                   |
#                                                   |
#                     -----------------------------------------------------
#                    |                              |                      |
#                    |                              |                      |
#                    |                              |                      |
#                 DHT Sensor                 Digital Light Sensor    CPU Utilization
#                    |                              |                   Metric
#                    |                              |
#            ----------------                  Light Metric
#           |                |
#           |                |
#      Temperature        Humidity
#         Metric           Metric
#
# Developers can leverage the following options:
# ---------------------------------------------
#  a) Use single publish and subscribe topic generated by LIOTA for an EdgeSystem, its Devices and its Metrics.
#  b) Use custom single publish and subscribe topic for an EdgeSystem, its Devices and Metrics.
#
#  - In the above two cases, MQTT message's payload MUST be self-descriptive so that subscriber can subscribe
#    process accordingly to a single topic by parsing payload.
#
#  c) Use custom publish and subscribe topics for Metrics.
#  - In this case, MQTT message's payload need not be self-descriptive.  Subscribers can subscribe to
#    appropriate topics and process accordingly.
#
#  d) Use combination of (a) and (c) or (b) and (c).
#
# GenericMqtt DCC has enclose_metadata option.  It can be used to enclose EdgeSystem, Device and Metric names
# along with the sensor data payload of a Metric.
#
# This example showcases publishing Metrics using (b) with enclose_metadata.
# ------------------------------------------------------------------------------------------------------------------

if __name__ == '__main__':

    #  Creating EdgeSystem
    edge_system = Dell5KEdgeSystem(config['EdgeSystemName'])

    #  Encapsulates Credentials
    credentials = Credentials(config['broker_root_ca_cert'], username=config["broker_username"],
                              password=config["broker_password"], cert_file=None, key_file=None)

    # Encapsulate TLS parameters
    tls_conf = TLSConf(config['cert_required'], config['tls_version'], config['cipher'])

    # Encapsulate QoS related parameters
    qos_details = QoSDetails(config['in_flight'], config['queue_size'], config['retry'])

    # Generate the MQTT Messaging attribute per edge system.
    msg_attr = MqttMessagingAttributes(pub_topic=config['SingleEdgeSystemPubTopic'])

    """
     Custom single publish topic for an EdgeSystem
     IBM Watson MQTT support documentation link:
     https://console.ng.bluemix.net/docs/services/IoT/reference/mqtt/index.html
     Gateway devices connectivity with IBM Watson Platform
     https://console.ng.bluemix.net/docs/services/IoT/gateways/mqtt.html
     Connecting to IBM Watson IoT
     Initializing GenericMqtt using MqttDccComms
    """
    ibm = GenericMqtt(MqttDccComms(edge_system.name, config['BrokerURL'], config['BrokerPort'],
                                     credentials=credentials, tls_conf=tls_conf, qos_details=qos_details,
                                     client_id=config["gateway_device_client_id"], clean_session=False,
                                     userdata=config['userdata'], protocol=config['protocol'],
                                     transport=['transport'],
                                     conn_disconn_timeout=config['ConnectDisconnectTimeout'],
                                     mqtt_msg_attr=msg_attr, enable_authentication=True),
                      enclose_metadata=True)

    #  Registering EdgeSystem
    reg_edge_system = ibm.register(edge_system)

    #  Creating CPU Metric
    cpu_utilization = Metric(
        name="CPUUtilization",
        unit=None,
        interval=10,
        aggregation_size=2,
        sampling_function=read_cpu_utilization
    )
    #  Registering Metric and creating Parent-Child relationship
    reg_cpu_utilization = ibm.register(cpu_utilization)
    ibm.create_relationship(reg_edge_system, reg_cpu_utilization)

    #  Publishing Registered CPU Utilization Metric to IBM Watson
    reg_cpu_utilization.start_collecting()

    #  Creating Simulated Device
    dht_sensor = SimulatedDevice("SimulatedDHTSensor")
    #  Registering Device and creating Parent-Child relationship
    reg_dht_sensor = ibm.register(dht_sensor)
    ibm.create_relationship(reg_edge_system, reg_dht_sensor)
    #  Creating Temperature Metric
    temp_metric = Metric(
        name="LivingRoomTemperature",
        entity_type="Metric",
        unit=ureg.degC,
        interval=1,
        aggregation_size=5,
        sampling_function=living_room_temperature
    )
    #  Registering Metric and creating Parent-Child relationship
    reg_temp_metric = ibm.register(temp_metric)
    ibm.create_relationship(reg_dht_sensor, reg_temp_metric)

    #  Publishing Registered Temperature Metric to IBM Watson
    reg_temp_metric.start_collecting()

    #  Creating Humidity Metric
    hum_metric = Metric(
        name="LivingRoomHumidity",
        entity_type="Metric",
        unit=None,
        interval=1,
        aggregation_size=5,
        sampling_function=living_room_humidity
    )
    #  Registering Metric and creating Parent-Child relationship
    reg_hum_metric = ibm.register(hum_metric)
    ibm.create_relationship(reg_dht_sensor, reg_hum_metric)

    #  Publishing Registered Humidity Metric to IBM Watson
    reg_hum_metric.start_collecting()

    #  Creating Simulated Device
    light_sensor = SimulatedDevice("SimDigLightSensor")
    #  Registering Device and creating Parent-Child relationship
    reg_light_sensor = ibm.register(light_sensor)
    ibm.create_relationship(reg_edge_system, reg_light_sensor)

    #  Creating Light Metric
    light_metric = Metric(
        name="LivingRoomLight",
        entity_type="Metric",
        unit=None,
        interval=10,
        aggregation_size=1,
        sampling_function=living_room_luminance
    )
    #  Registering Metric and creating Parent-Child relationship
    reg_light_metric = ibm.register(light_metric)
    ibm.create_relationship(reg_light_sensor, reg_light_metric)

    #  Publishing Registered Light Metric to IBM Watson
    reg_light_metric.start_collecting()

