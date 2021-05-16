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

import SoftLayer, json, configparser, argparse, logging, time, pytz
from datetime import datetime, timedelta
from cloudant.client import Cloudant

def convert_timedelta(duration):
    days, seconds = duration.days, duration.seconds
    hours = days * 24 + seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    totalminutes = round((days * 1440) + (hours * 60) + minutes + (seconds / 60), 1)
    return totalminutes

def convert_timestamp(sldate):
    formatedDate = sldate
    formatedDate = formatedDate[0:22]+formatedDate[23:26]
    formatedDate = datetime.strptime(formatedDate, "%Y-%m-%dT%H:%M:%S%z")
    return formatedDate.astimezone(central)

def getDescription(categoryCode, detail):
    for item in detail:
        if item['categoryCode'] == categoryCode:
            return item['description']
    return "Not Found"

## READ CommandLine Arguments and load configuration file
parser = argparse.ArgumentParser(description="Check Audit Log for VSI.")
parser.add_argument("-u", "--username", help="SoftLayer API Username")
parser.add_argument("-k", "--apikey", help="SoftLayer APIKEY")
parser.add_argument("-c", "--config", help="config.ini file to load")
args = parser.parse_args()


## READ CONFIGS TO Initialize SoftLayer API and Cloudant

if args.username == None and args.apikey == None:
    if args.config != None:
        filename = args.config
    else:
        filename = "config.ini"
    config = configparser.ConfigParser()
    config.read(filename)
    client = SoftLayer.Client(username=config['api']['username'], api_key=config['api']['apikey'],timeout=240)
else:
    client = SoftLayer.Client(username=args.username, api_key=args.apikey,timeout=240)

###########################################################
# define cloudant database to hold daily results
###########################################################

if config['cloudant']['username'] != None:
    cloudant = Cloudant.iam(config['cloudant']['username'], config['cloudant']['password'], connect=True)
    cloudant.connect()
    vsistatsDb = cloudant["vsistats"]
else:
    cloudant = None


central = pytz.timezone("US/Central")
today = central.localize(datetime.now())
logging.basicConfig( filename='/var/log/events.log', format='%(asctime)s %(message)s', datefmt='%Y-%m-%d %I:%M:%S %p',level=logging.WARNING)

########################################
# Get details on all hourlyVirtualGuests
########################################

try:
    virtualGuests = client['Account'].getHourlyVirtualGuests(
        mask='id, provisionDate, hostname, maxMemory, maxCpu, fullyQualifiedDomainName, lastTransaction, activeTransaction, activeTransactions,datacenter, datacenter.name,serverRoom, primaryBackendIpAddress, networkVlans, backendRouters,blockDeviceTemplateGroup')
except SoftLayer.SoftLayerAPIError as e:
    logging.warning("Account::getHourlyVirtualGuests(): %s, %s" % (e.faultCode, e.faultString))
    quit()

logging.warning('Found %s VirtualGuests.' % (len(virtualGuests)))

##############################
# Initiatlize Variables
#############################

for virtualGuest in virtualGuests:
    if virtualGuest['provisionDate'] == "":  ## Null indicates a job being provisioned
        Id = virtualGuest['id']
        numTransactions=len(virtualGuest['activeTransactions'])
        guestId = virtualGuest['activeTransaction']['guestId']
        createDate = virtualGuest['activeTransactions'][numTransactions-1]['createDate']
        createDateStamp = convert_timestamp(createDate)
        currentDateStamp = central.localize(datetime.now())
        delta = convert_timedelta(currentDateStamp - createDateStamp)
        hostName = virtualGuest['hostname']
        fullyQualifiedDomainName = virtualGuest['fullyQualifiedDomainName']
        maxCpu = virtualGuest['maxCpu']
        maxMemory = virtualGuest['maxMemory']

        if 'blockDeviceTemplateGroup' in virtualGuest:
            templateImage=virtualGuest['blockDeviceTemplateGroup']['name']
        else:
            templateImage="Stock Image"

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

        if "serverRoom" in virtualGuest:
            serverRoom=virtualGuest['serverRoom']['longName']
        else:
            serverRoom=""

        if "primaryBackendIpAddress" in virtualGuest:
            primaryBackendIpAddress=virtualGuest['primaryBackendIpAddress']
        else:
            primaryBackendIpAddress=""

        # Look at active transaction to get stats on current status of provisioning job
        transactionStatus = virtualGuest['activeTransaction']['transactionStatus']['name']
        statusDuration = round(virtualGuest['activeTransaction']['elapsedSeconds']/60,1)
        if 'averageDuration' in virtualGuest['activeTransaction']['transactionStatus']:
            averageDuration=virtualGuest['activeTransaction']['transactionStatus']['averageDuration']
        else:
            averageDuration=1

        logging.warning('VSI %s using %s image behind %s on vlan %s. (delta=%s, duration=%s, request=%s).' % (guestId,templateImage,router, vlan,delta,statusDuration,datetime.strftime(createDateStamp, "%H:%M:%S%z")))

        #add or update guestId in dictionary for historical view

        docid=str(guestId)
        provisioning_detail = {"_id": docid,
                                  "docType": "vsidata",
                                  "hostName": hostName,
                                  "templateImage": templateImage,
                                  "datacenter": datacenter,
                                  "serverRoom": serverRoom,
                                  "router": router,
                                  "vlan": vlan,
                                  "maxMemory": maxMemory,
                                  "maxCpu": maxCpu,
                                  "primaryBackendIpAddress": primaryBackendIpAddress,
                                  "createDateStamp": str(createDateStamp),
                                  "delta": delta,
                                  "transactionStatus": transactionStatus,
                                  "statusDuration": statusDuration}


        if cloudant != None:
            time.sleep(1)
            try:
                doc = vsistatsDb.create_document(provisioning_detail)
                logging.warning("Wrote new vsi detail record for guestId %s to database." % (docid))
            except:
                doc = vsistatsDb[docid]
                doc["hostName"] = hostName
                doc["templateImage"] = templateImage
                doc["datacenter"] = datacenter
                doc["serverRoom"] = serverRoom
                doc["router"] = router
                doc["vlan"] =  vlan
                doc["maxMemory"] = maxMemory
                doc["maxCpu"] = maxCpu
                doc["primaryBackendIpAddress"] = primaryBackendIpAddress
                doc["createDateStamp"] = str(createDateStamp)
                doc["delta"] = delta
                doc["transactionStatus"] = transactionStatus
                doc["statusDuration"] = statusDuration

                try:
                    doc.save()
                    logging.warning("Updating vsi detail record for guestId %s in database." % (docid))
                except:
                    logging.warning("Error adding detail record for guestId %s in database." % (docid))