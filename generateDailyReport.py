#!/usr/bin/env python3
# generateDailyReport.py - A script to generate daily provisioning statistics for IBM Cloud Classic Virtual Servers
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
#
#################################################################################################


import time,  SoftLayer, argparse, pytz, logging, logging.config, base64, os, json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, tzinfo
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (
    Mail, Personalization, Email, Attachment, FileContent, FileName,
    FileType, Disposition, ContentId)

def convertTimeDelta(duration):
    days, seconds = duration.days, duration.seconds
    hours = days * 24 + seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    totalminutes = round((days * 1440) + (hours * 60) + minutes + (seconds/60),1)
    return totalminutes

def convertTimestamp(sldate):
    formatedDate = datetime.fromisoformat(sldate)
    return formatedDate.astimezone(central)

def getDescription(categoryCode, detail):
    for item in detail:
        if item['categoryCode']==categoryCode:
            return item['description']
    return "Not Found"

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

############################################################
## READ CommandLine Arguments and load configuration file
############################################################
if __name__ == "__main__":
    setup_logging()
    parser = argparse.ArgumentParser(description="Generate report for daily provisioning statistics.")
    parser.add_argument("-d", "--date", help="Date to generate report for (mm/dd/yyyy).")

    args = parser.parse_args()

    if args.date == None:
        reportdate = datetime.now() - timedelta(days=1)
    else:
        reportdate=datetime.strptime(args.date+" 0:0:0","%m/%d/%Y %H:%M:%S")

    username=os.environ['sl_username']
    apikey=os.environ['sl_apikey']

    outputname="daily"+datetime.strftime(reportdate, "%m%d%Y")+".xlsx"
    central = pytz.timezone("US/Central")
    startdate = datetime.strftime(reportdate, "%m/%d/%Y") + " 0:0:0"
    enddate = datetime.strftime(reportdate,"%m/%d/%Y") + " 23:59:59"
    logging.info('Running Daily Provisioning Report for %s.' % (datetime.strftime(reportdate, "%m/%d/%Y")))

    ######################################
    # Connect to SoftLayer API
    ######################################
    client = SoftLayer.Client(username=username, api_key=apikey, timeout=240)

    ######################################
    # set Script Behavior Flags
    ######################################
    lookupPowerOn = True
    createExcel = True

    ######################################
    # Notification Variables
    ######################################


    sendEmails = True
    sendGridApi = os.environ['sendgrid_apiKey']
    sendGridTo = os.environ['sendgrid_to'].split(",")
    sendGridFrom = os.environ['sendgrid_from']
    sendGridSubject = os_environ['sendgrid_subject']



    df=pd.DataFrame()
    logging.info('Getting invoice list for Account from %s.' % (datetime.strftime(reportdate, "%m/%d/%Y")))
    InvoiceList=""
    while InvoiceList == "":
        try:
            InvoiceList = client['Account'].getInvoices(mask='createDate,typeCode, id, invoiceTotalAmount', filter={
                'invoices': {
                    'createDate': {
                        'operation': 'betweenDate',
                        'options': [
                             {'name': 'startDate', 'value': [startdate]},
                             {'name': 'endDate', 'value': [enddate]}
                             ],
                        },
                    'typeCode': {
                        'operation': 'in',
                        'options': [
                            {'name': 'data', 'value': ['ONE-TIME-CHARGE', 'NEW']}
                        ]
                        },
                    }
                })
        except SoftLayer.SoftLayerAPIError as e:
            logging.error("Account::getInvoices: %s, %s" % (e.faultCode, e.faultString))
            df = pd.DataFrame()

    for invoice in InvoiceList:
        invoiceID = invoice['id']
        invoicedetail=""
        logging.info('Looking up InvoiceId %s.' % (invoiceID))
        while invoicedetail == "":
            try:
                time.sleep(1)
                invoicedetail = client['Billing_Invoice'].getObject(id=invoiceID, mask="closedDate, invoiceTopLevelItems, invoiceTopLevelItems.product,invoiceTopLevelItems.location")
            except SoftLayer.SoftLayerAPIError as e:
                logging.error("Billing_Invoice::getObject: %s, %s" % (e.faultCode, e.faultString))
                time.sleep(5)

        invoiceTopLevelItems=invoicedetail['invoiceTopLevelItems']
        invoiceDate=convertTimestamp(invoicedetail["closedDate"])
        for item in invoiceTopLevelItems:
            if item['categoryCode']=="guest_core":
                itemId = item['id']
                billingItemId = item['billingItemId']
                location=item['location']['name']
                hostName = item['hostName']+"."+item['domainName']
                createDateStamp = convertTimestamp(item['createDate'])
                product=item['description']
                cores=""

                if 'product' in item:
                    product=item['product']['description']
                    cores=item['product']['totalPhysicalCoreCount']

                billing_detail=""
                logging.info('Looking up billing Invoice Detail for %s.' % (itemId))

                while billing_detail == "":
                    try:
                        time.sleep(1)
                        billing_detail = client['Billing_Invoice_Item'].getObject(id=itemId,
                                                                                  mask="filteredAssociatedChildren.product," \
                                                                                       "filteredAssociatedChildren.categoryCode," \
                                                                                       "filteredAssociatedChildren.description," \
                                                                                       "billingItem.cancellationDate, " \
                                                                                       "billingItem.provisionTransaction")
                    except SoftLayer.SoftLayerAPIError as e:
                        logging.error("Billing_Invoice_Item::getObject(%s): %s, %s" % (itemId,e.faultCode, e.faultString))
                        time.sleep(5)


                filteredAssociatedChildren=billing_detail['filteredAssociatedChildren']
                billingItem=billing_detail['billingItem']

                vsios=getDescription("os", filteredAssociatedChildren)
                memory=getDescription("ram", filteredAssociatedChildren)
                disk=getDescription("guest_disk0", filteredAssociatedChildren)

                if 'provisionTransaction' in billingItem:
                    provisionTransaction = billingItem['provisionTransaction']
                    provisionId = provisionTransaction['id']
                    guestId = provisionTransaction['guestId']
                    provisionDateStamp = convertTimestamp(provisionTransaction['modifyDate'])
                else:
                    provisionTransaction = "0"
                    provisionId = "0"
                    guestId = "0"
                    provisionDateStamp = convertTimestamp(item['createDate'])

                eventdate = provisionDateStamp
                powerOnDateStamp = provisionDateStamp

                # FORMAT DATE & TIME STAMPS AND DELTAS FOR CSV
                createDate = datetime.strftime(createDateStamp, "%Y-%m-%d")
                createTime = datetime.strftime(createDateStamp, "%H:%M:%S")
                provisionDate = datetime.strftime(provisionDateStamp, "%Y-%m-%d")
                provisionTime = datetime.strftime(provisionDateStamp, "%H:%M:%S")
                provisionDelta = convertTimeDelta(provisionDateStamp - createDateStamp)

                found=0
                if lookupPowerOn == True:
                    logging.info('Searching event Log for POWERON detail for guestId %s.' % (guestId))
                    # GET OLDEST POWERON EVENT FROM EVENTLOG FOR GUESTID AS INITIAL RESOURCE ALLOCATION TIMESTAMP

                    events=""
                    try:
                        time.sleep(1)
                        events = client['Event_Log'].getAllObjects(mask="objectId,eventName,eventCreateDate",filter={
                                                                'eventName': {'operation': 'Power On'},
                                                                'objectId': {'operation': guestId}})
                    except SoftLayer.SoftLayerAPIError as e:
                        logging.error("Event_Log::getAllObjects: %s, %s" % (e.faultCode, e.faultString))

                    for event in events:
                        if event['eventName']=="Power On":
                            eventdate = event["eventCreateDate"]
                            eventdate = eventdate[0:29]+eventdate[-2:]
                            eventdate = datetime.strptime(eventdate, "%Y-%m-%dT%H:%M:%S.%f%z")
                            if eventdate<powerOnDateStamp:
                                powerOnDateStamp = eventdate
                                found=1

                    # Calculate poweron if found
                    if found==1:
                        logging.info('POWERON detail for guestId %s FOUND.' % (guestId))
                        powerOnDateStamp=powerOnDateStamp.astimezone(central)
                        powerOnDate=datetime.strftime(powerOnDateStamp,"%Y-%m-%d")
                        powerOnTime=datetime.strftime(powerOnDateStamp,"%H:%M:%S")
                        powerOnDelta=convertTimeDelta(powerOnDateStamp - createDateStamp)
                    else:
                        logging.warning('POWERON detail for guestId %s NOT FOUND.' % (guestId))
                        powerOnDate="Not Found"
                        powerOnTime="Not Found"
                        powerOnDelta=0
                else:
                    powerOnDate = "Not Found"
                    powerOnTime = "Not Found"
                    powerOnDelta = 0


                ######################################
                # Get VSI detail from Cloudant database
                ######################################

                row = {'InvoiceId': invoiceID,
                       'BillingItemId': billingItemId,
                       'GuestId': guestId,
                       'Datacenter': location,
                       'Product': product,
                       'Cores': cores,
                       'OS': vsios,
                       'Memory': memory,
                       'Disk': disk,
                       'Hostname': hostName,
                       'CreateDate': createDate,
                       'CreateTime': createTime,
                       'PowerOnDate': powerOnDate,
                       'PowerOnTime': powerOnTime,
                       'PowerOnDelta': powerOnDelta,
                       'ProvisionedDate': provisionDate,
                       'ProvisionedTime': provisionTime,
                       'ProvisionedDelta': provisionDelta
                       }
                df = df.append(row, ignore_index=True)

    if len(InvoiceList)>0:
        ########################################################
        ## Generate Statisitics & Create HTML for message
        #########################################################
        logging.info("Generating Statistics and formating email message.")
        header_html = ("<p><center><b>Provisioning Statistics for %s</b></center></br></p>" % ((datetime.strftime(reportdate, "%m/%d/%Y"))))

        ########################################################
        ##  Describe Overall Provisioning Statistics
        ########################################################
        stats=(df["ProvisionedDelta"].describe())
        stats_html= "<p><b>Provisioning Statistics</b></br>"+(stats.to_frame().to_html())+"</p>"

        ########################################################
        # Create Pivot Table for Datacenter & Image Statistiics
        ########################################################
        imagePivot = pd.pivot_table(df,index=['Datacenter'], values='ProvisionedDelta', aggfunc=[len, np.min, np.average, np.std, np.max],margins=True)
        imagePivot_html= "<p><b>Datacenter Statistics</b></br>"+imagePivot.to_html()+"</p>"

        # Create Time Distribution
        provisionRequests=len(df)
        notAllocated=len(df[(df.PowerOnDelta >30)])
        distribution0=len(df[df.ProvisionedDelta.between(0,30.99,inclusive=True)])
        distribution30=len(df[df.ProvisionedDelta.between(31,60.99,inclusive=True)])
        distribution60=len(df[df.ProvisionedDelta.between(61,90.99,inclusive=True)])
        distribution90=len(df[df.ProvisionedDelta.between(91,120.99,inclusive=True)])
        distribution120=len(df[df.ProvisionedDelta.between(121,360.99,inclusive=True)])
        distribution360=len(df[df.ProvisionedDelta.between(361,999999,inclusive=True)])

        noalloc_html = ('<p><b>SLA Report</b></br><table width="100" border="1" class="dataframe"><tr>' \
                   '<th>NotAllocatedIn30</th></tr><tr><td style="text-align: center;">%s</td></tr></table></p>' % (notAllocated))

        distribution_html=('<p><b>Provisioning Time Distribution Report</b></br><table width="400" border="1" class="dataframe"><tr>' \
                   '<th>Total</th><th>0to30</th><th>31-60</th><th>61-90</th><th>91-120</th><th>121-360</th><th>gt360</th></tr><tr>' \
                   '<td style="text-align: center;">%s</td><td style="text-align: center;">%s</dh><td style="text-align: center;">%s</td>' \
                   '<td style="text-align: center;">%s</td><td style="text-align: center;">%s</td><td style="text-align: center;">%s</td><td style="text-align: center;">%s</td>' \
                   '</tr></table></p>' % (provisionRequests,distribution0, distribution30, distribution60, distribution90, distribution120, distribution360))

        html=header_html+stats_html+noalloc_html+distribution_html+imagePivot_html


        ##########################################
        # Write Output to Excel
        ##########################################

        if createExcel == True:
            logging.info("Creating Excel File.")
            writer = pd.ExcelWriter(outputname, engine='xlsxwriter')
            df.to_excel(writer,'Detail')
            imagePivot.to_excel(writer,'Image_Pivot')
            writer.save()
    else:
        logging.warning('No invoices found for %s.' % (datetime.strftime(reportdate, "%m/%d/%Y")))
        header_html = ("<p><center><b>Provisioning Statistics for %s</b></center></br></p>" % (
            (datetime.strftime(reportdate, "%m/%d/%Y"))))
        message_html = ("<p><b>No Invoices found for this date.</b></p>")
        html = header_html + message_html


    #########################################
    # FORMAT & SEND EMAIL VIA SENDGRID ACCOUNT
    ##########################################
    if sendEmails == True:
        logging.info("Sending report via email.")

        to_list = Personalization()
        for email in sendGridTo:
            to_list.add_to(Email(email))

        message = Mail(
            from_email=sendGridFrom,
            subject=sendGridSubject,
            html_content=html
        )

        message.add_personalization(to_list)

        if len(InvoiceList) > 0:
            file_path = os.path.join("./", outputname)
            with open(file_path, 'rb') as f:
                data = f.read()
                f.close()
            encoded = base64.b64encode(data).decode()
            attachment = Attachment()
            attachment.file_content = FileContent(encoded)
            attachment.file_type = FileType('application/xlsx')
            attachment.file_name = FileName(outputname)
            attachment.disposition = Disposition('attachment')
            attachment.content_id = ContentId('daily file')
            message.attachment = attachment
            try:
                os.remove(file_path)
                logging.info("%s file successfully deleted." % outputname)
            except OSError as e:
                logging.error("%s could not be deleted. (%s)" % (outputname,e))
        try:
            sg = SendGridAPIClient(sendGridApi)
            response = sg.send(message)
            logging.info("Email Send status code = %s." % response.status_code)
        except Exception as e:
            logging.error("Email Send Error = %s." % e.to_dict)

    logging.info('Finished Daily Provisioning Report Job for %s.' % (datetime.strftime(reportdate, "%m/%d/%Y")))
