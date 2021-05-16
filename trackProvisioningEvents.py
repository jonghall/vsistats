#!/usr/bin/env python3
# trackProvisioningEvents.py - A script to periodically capture VSI attributes during provisioning for use with generateDailyReport.py
# Author: Jon Hall
# Copyright (c) 2021
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
#################################################################################################

import SoftLayer, json, configparser, argparse, logging, logging.config, os
from cloudant.client import Cloudant

def setup_logging(
    default_path='logging.json',
    default_level=logging.INFO,
    env_key='LOG_CFG'):

    path = default_path
    value = os.getenv(env_key, None)
    if value:
        path = value
    if os.path.exists(path):
        with open(path, 'rt') as f:
            config = json.load(f)
        if "handlers" in config:
            if "logdna" in config["handlers"]:
                config["handlers"]["logdna"]["key"] = os.getenv("logdna_ingest_key")
        logging.config.dictConfig(config)
    else:
        logging.basicConfig(level=default_level)


## READ CommandLine Arguments and load configuration file
setup_logging()

parser = argparse.ArgumentParser(description="Capture and store provisioning data.")
parser.add_argument("-c", "--config", help="config.ini file to load")
args = parser.parse_args()


## READ CONFIGS TO Initialize SoftLayer API and Cloudant
if args.config != None:
    filename = args.config
else:
    filename = "config.ini"

config = configparser.ConfigParser()
config.read(filename)
client = SoftLayer.Client(username=config['api']['username'], api_key=config['api']['apikey'],timeout=240)


###########################################################
# define cloudant database to hold daily results
###########################################################

if 'cloudant' in config:
    if config['cloudant']['username'] != None:
        cloudant = Cloudant.iam(config['cloudant']['username'], config['cloudant']['password'], connect=True)
        cloudant.connect()
        vsistatsDb = cloudant["vsistats"]
    else:
        cloudant = None
        logging.warning("No cloudant username found in %s." % filename)
else:
    cloudant = None
    logging.warning("No cloudant section found in %s." % filename)

########################################
# Get details on all hourlyVirtualGuests
########################################

try:
    virtualGuests = client['Account'].getHourlyVirtualGuests(
        mask='id,provisionDate,hostname,datacenter.name,primaryBackendIpAddress,networkVlans,backendRouters,blockDeviceTemplateGroup')
except SoftLayer.SoftLayerAPIError as e:
    logging.error("Account::getHourlyVirtualGuests(): %s, %s" % (e.faultCode, e.faultString))
    quit()

logging.info('Found %s VirtualGuests.' % (len(virtualGuests)))

##############################
# Initiatlize Variables
#############################

for virtualGuest in virtualGuests:
    if virtualGuest['provisionDate'] == "":  ## Null indicates a job being provisioned
        guestId = virtualGuest['id']
        hostName = virtualGuest['hostname']

        if 'blockDeviceTemplateGroup' in virtualGuest:
            templateImage=virtualGuest['blockDeviceTemplateGroup']['name']
        else:
            templateImage=""

        if "networkVlans" in virtualGuest:
            if len(virtualGuest['networkVlans'])>0:
                vlan = virtualGuest['networkVlans'][0]['vlanNumber']
            else:
                vlan = virtualGuest['networkVlans']['vlanNumber']
        else:
            vlan=""

        if "backendRouters" in virtualGuest:
            if len(virtualGuest['backendRouters']) > 1:
                router=virtualGuest['backendRouters'][0]['hostname']
            else:
                router = virtualGuest['backendRouters']['hostname']
        else:
            router=""

        if "datacenter" in virtualGuest:
            datacenter=virtualGuest['datacenter']['name']
        else:
            datacenter=""


        if "primaryBackendIpAddress" in virtualGuest:
            primaryBackendIpAddress=virtualGuest['primaryBackendIpAddress']
        else:
            primaryBackendIpAddress=""


        logging.info('VSI %s using %s image behind %s on vlan %s.' % (guestId,templateImage,router,vlan))

        #add or update guestId in dictionary for historical view

        docid=str(guestId)
        provisioning_detail = {"_id": docid,
                                  "docType": "vsidata",
                                  "hostName": hostName,
                                  "templateImage": templateImage,
                                  "datacenter": datacenter,
                                  "router": router,
                                  "vlan": vlan,
                                  "primaryBackendIpAddress": primaryBackendIpAddress
                                }

        if cloudant != None:
            time.sleep(1)
            try:
                doc = vsistatsDb.create_document(provisioning_detail)
                logging.info("Wrote vsi detail record for guestId %s to Cloudant database." % (docid))
            except:
                logging.error("Error saving vsi detail record for guestId %s to Cloudant database. [%s]" % (docid, provisioning_detail))