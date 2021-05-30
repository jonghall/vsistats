# Each instruction in this file generates a new layer that gets pushed to your local image cache

FROM python:3.9.5-buster

#
# Identify the maintainer of an image
LABEL maintainer="jonhall@us.ibm.com"

#
# Install NGINX to test.
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
CMD python generateDailyReport.py
pyth