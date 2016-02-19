FROM python:2.7-slim
ADD . /src
WORKDIR /src
RUN apt-get update && apt-get --yes --force-yes install libpng12-dev libfreetype6-dev && pip install -r requirements.txt
CMD make run
