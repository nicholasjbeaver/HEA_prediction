#
#
# Build this Dockerfile from the corpuskeeper directory:
#
# docker build -t ingestion_pipeline -f ./ingestion_pipeline/Dockerfile .
#
# run the container locally:
#
# docker run -e PORT=9999 --env-file .env ingestion_pipeline
#
FROM python:3.9-slim

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y git && \
    rm -rf /var/lib/apt/lists/*
    
# Allow statements and log messages to immediately appear in the Knative logs
ENV PYTHONUNBUFFERED True

# Copy local code to the container image.
ENV APP_HOME /app
WORKDIR $APP_HOME

# Add ingestion_pipeline to PYTHONPATH
ENV PYTHONPATH "${PYTHONPATH}:${APP_HOME}/rag"

# Copy application dependency manifests to the container image.
# Copying this separately prevents re-running pip install on every code change.
COPY requirements.txt $APP_HOME/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# COPY ./ingestion_pipeline/requirements.txt $APP_HOME/ingestion_pipeline/requirements.txt
# RUN pip install --no-cache-dir -r ./ingestion_pipeline/requirements.txt

# COPY ./ingestion_pipeline/sharders/requirements.txt $APP_HOME/ingestion_pipeline/sharders/requirements.txt
# RUN pip install --no-cache-dir -r ./ingestion_pipeline/sharders/requirements.txt

COPY . $APP_HOME

# Run the web service on container startup.
# Use gunicorn webserver with one worker process and 8 threads.
# For environments with multiple CPU cores, increase the number of workers
# to be equal to the cores available.
# Timeout is set to 0 to disable the timeouts of the workers to allow Cloud Run to handle instance scaling.
# CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 rag
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 "rag:create_app()"
