# **VSI STATS**

These scripts periodically capture VSI data during provisioning, and use it to create a daily report on provisioning
for IBM Cloud Classic Virtual Servers (VSIs).

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
* If you wish to collect statistics on images used the script must be run periodically (every 10 minutes is recommended).  The image template data is only available while the instance is provisioning so the script captures and stores the data in the Cloudant database for access by the daily script.
* The daily report should be run nightly, after 3am eastern time to ensure that it captures all the previous days provisioning events.  If the [Cloudant] section is left blank or
the trackProvisioningEvents script isn't run the Image Statistics will be missing.
* The daily report can be run adhoc by running directly.   ````python generateDailyReport.py --date YYYY/MM/DD````
* If no date is specified the script will default to running the report using the previous days data.

### Suggested CRONTAB settings
````bazaar
#!/usr/bin/env bash
*/10 * * * * /directory/trackProvisioningReport.sh >> /var/log/events.log 2>&1
30 03 * * * /directory/generateDailyReport.sh  >> /var/log/daily.log 2>&1
````

### Python Requirements
* Python 3.8 or newer must be installed on the compute node  which will run the scripts.
* It is recommended that _virtualenv_ be used. (https://virtualenv.pypa.io/en/latest/)
  * to create a virtual environment in directory where scripts is installed type ````virtualenv venv````
  * to activate virtual environment ````source venv/bin/activate````.  Note the shell scripts will activate the environment before execution.
* [requirements.txt](requirements.txt) contain all the Python package requirements.  To install packages ````pip install -r requirements.txt````
* Adjust directories in the shell scripts to reflect the locations of the scripts and virtualenv.

### Daily Report Email output sent via IBM Cloud Email Delivery (aka Sendgrid)
* A daily email will be sent by [generateDailyReport.py](generateDailyReport.py) if sendgrid credentials are included in config.ini.
* In addition to the statistics summary, an excel workbook with the detailed VSI data will be attached to the email. 
* Detailed data such as image template, vlan, router, and primaryBackendIp address will be blank unless running [trackProvisioningEvents.py](trackProvisioningEvents.py) 
  to periodically collect and store this data in the _Cloudant_ database.  The data for these columns are only available while the VSI is provisioning
  and are not stored with the invoice data which is used to produce the daily report.

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
34      34      0       0	    0	    0	    0

Datacenter & Image Statistics
		                        len 	          amin 	            average 	        std 	            amax
		                        ProvisionedDelta  ProvisionedDelta 	ProvisionedDelta 	ProvisionedDelta 	ProvisionedDelta
Datacenter 	Image 					
wdc01 	    SL.AMPB.2012R2.042  31.0 	          10.4 	            11.554839 	        0.589824 	        12.8
            SL.AMPB.2012R2.0521 3.0 	          11.7 	            11.733333 	        0.057735 	        11.8
All 		                    34.0 	          10.4 	            11.570588 	        0.556528 	        12.8


````
### Excel Daily Output Example

![example-output](example-output.png)

### Logging
* [logging.json](logging.json) can be modified to suite logging needs for both scripts
* Both scripts log all informational status messages as INFO, unexpected results as WARN, and errors as ERRORS.

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