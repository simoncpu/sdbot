FROM python:2.7-slim
ADD . /src
WORKDIR /src
RUN apt-get install libpng12-dev tk-dev build-essential && pip install -r requirements.txt
CMD make run
