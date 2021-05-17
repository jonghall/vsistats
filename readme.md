# **VSI STATS**

These scripts periodically capture data from hourly VSIs for IBM Cloud Classic Infrastructure during provisioning,
and use it to create a daily report on provisioning times for the previous day.

### Prereqs
* IBM Cloud Classic Infrastructure (Aka Softlayer) apiKey and username.  
* IBM Cloudant Multi-tenant Lite Tier instance (https://cloud.ibm.com/catalog/services/cloudant)
* Email Delivery, Powered by Sendgrid (https://cloud.ibm.com/catalog/infrastructure/email-delivery).
* A compute node (CentOS or Ubuntu recommended) with Python 3.8+ to run daily reports, and collect periodic provisioning data.  Compute Instance does not need to be in same account or even in the IBM Cloud, just needs to have access to the public SoftLayer API endpoint to collect data.

_Cloudant Database and periodic data collection process is only requried if expanded Datacenter and Image statistics are required._

### Configuration (config.ini)
* **[api]** section must include a valid IBM Cloud Classic Infrastructure credentials (aka SoftLayer)
  * The **userid** and **apikey** must have at least the following Classic Infrastructure permissions.
    * View Audit Log 
    * View Virtual Host Details
    * View Virtual Dedicated Host Details
    * Manage Public Images
  * **Userid** needs to also have the ability to view all existing and future virtual devices.
    * "Auto virtual server access" must be checked on permissions to allow script to read future provsioned VSI data.
* **[sendGrid]** section should contain your IBM Email Delivery powered by SendGrid credentials.
  * The **apiKey** should contain a valid sendGrid apiKey.
  * The **from** field must contain one valid email address.
  * The **to** field must contain at least one valid email address.  Multiple email addresses can be separated by a comma.
  * The **Subject** should specify the desired subject line of the nightly report emails.
* **[cloudant]** section should include your IBM Cloud for Databases Cloudant credentials.  If this section is left blank, the daily report will exclude provisioning statistics based on image template data and some columns in the excel file will be blank.
  * **username**  The username is the Cloudant instance name. 
  * **password**  The password is the ApiKey.  
  
[config.ini](sample.ini)
```bazaar
[api]
username=<USERNAME>
apikey=<SOFTLAYER APIKEY>

[sendGrid]
apiKey = <sendgrid API>
from=email@ibm.com
to=email1@ibm.com, email2@ibm.com
subject = 'Daily Provisioning Report'

[cloudant]
username = <cloudant user>
password = <cloudant apikey>
```
### Scheduling Scripts to run.
* If you wish to collect statistics on images templates used the [trackProvisioningEvents.sh](trackProvisioningEvents.sh)
  script should run periodically (every 10 minutes is recommended) to capture all provisioning requests.
  Additionally the [Cloudant] section must exist in the [config.ini](sample.ini), and have the
  required credentials to store this data in the Cloudant database.
* [generateDailyReport.sh](generateDailyReport.sh) should be scheduled to run each day after 3am eastern time to ensure that
  all the previous days provisioning requests are captured.
* The python script [generateDailyReport.py](generateDailyReport.py) can be used to run an adhoc report for a different 
  date by including --date mm/dd/yyyy 
  ````python generateDailyReport.py --date YYYY/MM/DD````
  
### Suggested CRONTAB settings
````bazaar
#!/usr/bin/env bash
*/10 * * * * /directory/trackProvisioningReport.sh >> /var/log/vsistats.log 2>&1
30 03 * * * /directory/generateDailyReport.sh  >> /var/log/vsistats.log 2>&1
````

### Python Requirements
* Python 3.8 or newer must be installed on the compute node used to run the scripts.
* It is recommended that _virtualenv_ be used. (https://virtualenv.pypa.io/en/latest/)
  * to create a virtual environment in directory where scripts is installed type ````virtualenv venv````
  * to activate virtual environment ````source venv/bin/activate````.  Note the shell scripts will activate the environment before execution.
* [requirements.txt](requirements.txt) contain all the Python package requirements.  To install packages ````pip install -r requirements.txt````
* Adjust directories in the shell scripts to reflect the locations of the scripts and virtualenv.

### Daily Report Email output sent via IBM Cloud Email Delivery (aka Sendgrid)
* A daily email will be sent by [generateDailyReport.py](generateDailyReport.py) if sendgrid credentials are included in 
  the [sendGrid] section of the [config.ini](sample.ini) file.
* In addition to the statistics summary included in the email, an Excel workbook with the detailed VSI data will be attached to the email. 
* Detailed data such as image template, vlan, router, and ip address will be blank unless running [trackProvisioningEvents.sh](trackProvisioningEvents.sh) 
  script via CRONTAB to periodically collect and store this data in the _Cloudant_ database.  The data for these columns is only available while the VSI
  is being provisioning and are not stored with the invoice data which is used to produce the daily report.  Additionally, because image
  template data is blank, provisioning statistics will only be provided at a datacenter level.

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

Datacenter & Image Statistics
		                        len 	          amin 	            average 	        std 	            amax
		                        ProvisionedDelta  ProvisionedDelta 	ProvisionedDelta 	ProvisionedDelta 	ProvisionedDelta
Datacenter 	Image 					
wdc01 	    SL.AMPB.2012R2.042  31.0              10.4              11.554839           0.589824 	        12.8
            SL.AMPB.2012R2.052  3.0               11.7              11.733333 	        0.057735 	        11.8
All                             34.0              10.4              11.570588 	        0.556528 	        12.8


````
### Excel Daily Output Example

![example-output](example-output.png)

### Logging
* [logging.json](logging.json) can be modified to suite logging needs for both scripts
* Both scripts log all informational status messages to _/var/log/vsistats.log_ as INFO, unexpected results as WARN, and errors as ERRORS.

````
[2021-05-16 12:08:07,457] INFO [generateDailyReport.py:345] Generating Statistics and formating email message.
[2021-05-16 12:08:07,551] INFO [generateDailyReport.py:387] Creating Excel File.
[2021-05-16 12:08:07,594] INFO [generateDailyReport.py:404] Sending report via email.
[2021-05-16 12:08:07,595] INFO [generateDailyReport.py:433] daily05152021.xlsx file successfully deleted.
[2021-05-16 12:08:08,081] INFO [generateDailyReport.py:439] Email Send status code = 202.
[2021-05-16 12:08:08,081] INFO [generateDailyReport.py:443] Finished Daily Provisioning Report Job for 05/15/2021.
````

**Links**
SoftLayer Python SDK documentation
* https://softlayer-api-python-client.readthedocs.io/en/latest/

IBM Classic API's used
* https://sldn.softlayer.com/reference/services/SoftLayer_Account/getInvoices/
* https://sldn.softlayer.com/reference/services/SoftLayer_Account/getHourlyVirtualGuests/
* https://sldn.softlayer.com/reference/services/SoftLayer_Event_Log/