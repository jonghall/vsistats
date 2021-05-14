# **VSI STATS**

These scripts periodically capture VSI data during provisioning, and use it to create a daily report on provisioning
for IBM Cloud Classic Virtual Servers (VSIs).



**Prereq**
* IBM Cloud Classic (Aka Softlayer) Username and ApiKey.  User must have access to account billing and virtual server provisioning records (all VSIs must be visible)
* IBM Cloud Database - Cloudant Multitenant Lite tier instance (https://cloud.ibm.com/catalog/services/cloudant) with IAM ApiKey and instance username with Manager access.
* Email Delivery, Powered by Sendgrid (https://cloud.ibm.com/catalog/infrastructure/email-delivery) with ApiKey.
* A compute node to run daily report, and periodic data collection job (every 10 minutes).  Instance does not need to be in same account or even in the IBM Cloud, just needs to have access
to the SoftLayer API endpoint.

_Cloudant Database and periodic data collection process is only requried if expanded Datacenter and Image statistics are required._

### Configuration (config.ini)
*API section should include the IBM Cloud Classic (aka SoftLayer) userid and apikey.   This user must have at least the following Classic Infrastructure permissions.  Additionally user should have
ability to view all virtual devices and "Auto virtual server access" should be checked.
** View Audit Log
** View Virtual Host Details
** View Virtual Dedicated Host Details
** Manage Public Images
*sendGrid section should include your IBM Email Delivery powered by SendGrid apikey, a to field with at least one email address.  Multiple email addresses should be separated by a comma, and the Subject should specify the desired subject line of the nightly report emails.
* cloudant section should include your Cloudand username and password.   For IAM enabled cloudant databases these are found under credentials.  The username is the Cloudant instance name.  The password is the ApiKey.  If this section is left blank, the daily report will only build statistics for the provisioning times and not capture image or vlan data.

```bazaar
[api]
username=<USERNAME>
apikey=<SOFTLAYER APIKEY>

[sendGrid]
apiKey = <sendgrid API>
to=email1@ibm.com, email2@ibm.com
subject = 'Daily Provisioning Report'

[cloudant]
username = <cloudant user>
password = <cloudant apikey>



```
### Scheduling Scripts to run.
* If you wish to collect statistics on images and vlan information the script requires a Cloudant instance and the credentials to be included in the [Cloudant] section of config.ini.
because this data is only available while the instance is being provisioned or running it is recommended that this script be run atleast every 10-15 minutes.
* The daily report should be run nightly, after 3am eastern time to ensure that it captures all the previous days provisioning events.  If the [Cloudant] section is left blank or
the trackProvisioningEvents script isn't run regularly the Datacenter and Image Statistics will be blank.

####Suggested CRONTAB settings
````bazaar
#!/usr/bin/env bash
*/15 * * * * /directory/trackProvisioningReport.sh >> /var/log/events.log 2>&1
30 03 * * * /directory/generateDailyReport.sh  >> /var/log/daily.log 2>&1
````

### Daily Report Email output sent via IBM Cloud Email Delivery (aka Sendgrid)
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
34	34	0	0	0	0	0

Datacenter & Image Statistics
		len 	amin 	average 	std 	amax
		ProvisionedDelta 	ProvisionedDelta 	ProvisionedDelta 	ProvisionedDelta 	ProvisionedDelta
Datacenter 	Image 					
wdc01 	SL.AMPB.2012R2.0421 	31.0 	10.4 	11.554839 	0.589824 	12.8
SL.AMPB.2012R2.0521 	3.0 	11.7 	11.733333 	0.057735 	11.8
All 		34.0 	10.4 	11.570588 	0.556528 	12.8


````
Text based Log output
````

````
Meta Data Logged with output.  (Power On virtualServer01.Jonathan-Hall-s-Account.cloud)
````

````

**Links**
SoftLayer Python SDK documentation
* https://softlayer-api-python-client.readthedocs.io/en/latest/

IBM Classic API's used
* https://sldn.softlayer.com/reference/services/SoftLayer_Account/getVirtualGuests/
* https://sldn.softlayer.com/reference/services/SoftLayer_Hardware_Server/