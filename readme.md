# **VSI STATS FOR IBM CODE ENGINE**

This script will produce a daily provisioning statistics report for IBM Classic Virtual Servers.  

### Prereqs
* IBM Cloud Classic Infrastructure (Aka Softlayer) apiKey and username with at least the following Classic Infrastructure permissions.
    * View Audit Log 
    * View Virtual Host Details
    * View Virtual Dedicated Host Details
    * Manage Public Images
    * ability to view all existing and future virtual devices by enabling "Auto virtual server access" on permissions to allow script to read future provsioned VSI data.
* Email Delivery, Powered by Sendgrid (https://cloud.ibm.com/catalog/infrastructure/email-delivery).
* IBM Code Engine (https://cloud.ibm.com/codeengine/overview).  Code Engine does not need to be in same IBM Cloud account that the report is run against.


### Container Build Requirements

* Access to IBM Cloud or Docker Container Registry
* [requirements.txt](requirements.txt) contain all the Python package requirements.
* [Dockerfile](Dockerfile) contains the required container build parameters

### Daily Report Email output sent via IBM Cloud Email Delivery (aka Sendgrid)
* A daily email will be sent by
* In addition to the statistics summary included in the email, an Excel workbook with the detailed VSI data will be attached to the email.

````
Provisionings Statistics for 05/12/2021

Provisioning Statistics
	ProvisionedDelta
count 	34.000000
mean 	11.570588
std 	0.564897
min 	10.400000
25% 	11.250000
50% 	11.600000
75% 	11.900000
max 	12.800000

SLA Report
NotAllocatedIn30
0

Provisioning Time Distribution Report
Total	0to30	31-60	61-90	91-120	121-360	gt360
34      34      0       0       0       0       0

Datacenter Statistics
		     len 	          amin 	            average 	        std 	            amax
		    ProvisionedDelta  ProvisionedDelta 	ProvisionedDelta 	ProvisionedDelta 	ProvisionedDelta
Datacenter 					
wdc01 	     31.0              10.4              11.554839           0.589824 	        12.8
             3.0               11.7              11.733333 	        0.057735 	        11.8
All          34.0              10.4              11.570588 	        0.556528 	        12.8


````

### Logging
* [logging.json](logging.json) can be modified to suite logging needs.
* As configured logging is to console and will be picked up by IBM Log Analysis if logging is enabled for Code Engine project

````
[2021-05-16 12:08:07,457] INFO [generateDailyReport.py:345] Generating Statistics and formating email message.
[2021-05-16 12:08:07,551] INFO [generateDailyReport.py:387] Creating Excel File.
[2021-05-16 12:08:07,594] INFO [generateDailyReport.py:404] Sending report via email.
[2021-05-16 12:08:07,595] INFO [generateDailyReport.py:433] daily05152021.xlsx file successfully deleted.
[2021-05-16 12:08:08,081] INFO [generateDailyReport.py:439] Email Send status code = 202.
[2021-05-16 12:08:08,081] INFO [generateDailyReport.py:443] Finished Daily Provisioning Report Job for 05/15/2021.
````

### Setting up IBM Code Engine and building container
1. Create project, build job and job.
    1. Open the Code Engine [console](https://cloud.ibm.com/codeengine/overview)
    2. Select Start creating from Start from source code.
    3. Select Job
    4. Enter a name for the job such as _dailyreport_. Use a name for your job that is unique within the project.
    5. Select a project from the list of available projects of if this is the first one, create a new one. Note that you must have a selected project to deploy an app.
    6. Enter the URL for this GitHub repository and click specify build details.  Make adjustments if needed to URL and Branch name.  Click Next.
    7. Select Dockerfile for Strategy, Dockerfile for Dockerfile, 10m for Timeout, and Medium for Build resources. Click Next.
    8. Select a container registry location, such as IBM Registry, Dallas.
    9. Select Automatic for Registry access.
    10. Select an existing namespace or enter a name for a new one, for example, newnamespace.
    11. Enter a name for your image and optionally a tag.
    12. Click Done.
    13. Click Create.

2. Create configmaps and secrets.
    1. From [project list](https://cloud.ibm.com/codeengine/projects), choose newly created project.
    2. Select secrets and configmaps
    3. click create, choose config map, and give it a name.  Add the following key value pairs
      * **sendgrid_from** field must contain one valid email address.
      * **sendgrid_to** field must contain at least one valid email address.  Multiple email addresses can be separated by a comma.
      * **sendgrid_subject** hould specify the desired subject line of the nightly report emails.
    4. Select secrets and configmaps
    5. click create, choose secrets, and give it a name.  Add the following key value pairs
      * **sl_username** IBM Cloud classic username
      * **sl_apikey**  IBM Cloud classic apikey
      * **sendgrid_apikey** Sendgrid apikey

3. Make secrets and configmaps available to job.
    1. Choose the job previously created.
    2. Click on the Environment variables tab.
    3. Click add, choose reference to full configmap, and choose configmap created in previous step and click add.
    4. Click add, choose reference to full secret, and choose secrets created in previous step and click add.
 
4. Scheduling Code Engine job to run daily
   
   1.  Install IBM Cloud CLI and Code Engine Plugin (https://cloud.ibm.com/docs/codeengine?topic=codeengine-install-cli)
   2. Using IBM Cloud CLI configure a ping subscription to trigger the job.
      
   ````bazaar
   ibmcloud login --apikey <apikey>
   ibmcloud target -r us-south -g myresource-group
   ibmcloud ce project select --name vsistats
   ibmcloud ce sub ping create --name report-run --destination dailyreport --destination-type job  --schedule '30 08  * * *'    
   ibmcloud ce sub pring get --name report-run
   ````
   _schedule times are by default specified in UTC time._   

**Links**
**SoftLayer Python SDK documentation**
* https://softlayer-api-python-client.readthedocs.io/en/latest/

**IBM Classic API's used**
* https://sldn.softlayer.com/reference/services/SoftLayer_Account/getInvoices/
* https://sldn.softlayer.com/reference/services/SoftLayer_Account/getHourlyVirtualGuests/
* https://sldn.softlayer.com/reference/services/SoftLayer_Event_Log/

**IBM Code Engine**
* https://cloud.ibm.com/docs/codeengine
