# **VSI STATS**

These scripts periodically capture data from hourly VSIs for IBM Cloud Classic Infrastructure during provisioning,
and use it to create a daily report on provisioning times for the previous day.

### Prereqs
* IBM Cloud Classic Infrastructure (Aka Softlayer) apiKey and username.
* Email Delivery, Powered by Sendgrid (https://cloud.ibm.com/catalog/infrastructure/email-delivery).
* IBM Code Engine instance to run daily report.  Code Engine does not need to be in same IBM Cloud account that the report is run against.


### Environment Variables and Secrets
  * **sl_username** and **sl_apikey** must have at least the following Classic Infrastructure permissions.
    * View Audit Log 
    * View Virtual Host Details
    * View Virtual Dedicated Host Details
    * Manage Public Images
    * ability to view all existing and future virtual devices by enabling "Auto virtual server access" on permissions to allow script to read future provsioned VSI data.
  * The **sendgrid_apikey** should contain a valid sendGrid apiKey.
  * The **sendgrid_from** field must contain one valid email address.
  * The **sendgrid_to** field must contain at least one valid email address.  Multiple email addresses can be separated by a comma.
  * The **sendgrid_subject** should specify the desired subject line of the nightly report emails.

 
### Scheduing Code Engine job to run daily
````bazaar
ibmcloud ce sub ping create --name report-run --destination dailyreport --destination-type job  --schedule '30 03  * * *'    
````

### Container Build Requirements

* Python 3.9 or newer must be installed on the compute node used to run the scripts.
* [requirements.txt](requirements.txt) contain all the Python package requirements.
* [Dockerfile](Dockerfile) contains the required container build parameters

### Daily Report Email output sent via IBM Cloud Email Delivery (aka Sendgrid)
* A daily email will be sent by [generateDailyReport.py](generateDailyReport.py) 
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
### Excel Daily Output Example

![example-output](example-output.png)

### Logging
* [logging.json](logging.json) can be modified to suite logging needs.

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