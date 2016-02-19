FROM python:2.7-slim
ADD . /src
WORKDIR /src
RUN apt-get update && apt-get install libpng12-dev libfreetype6-dev && pip install -r requirements.txt
CMD make run
