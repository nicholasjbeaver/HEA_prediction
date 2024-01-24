#
#
# Build this Dockerfile from the HEA_prediction directory:
#
# docker build -t prediction_server -f ./build/Dockerfile .
#
# run the container locally:
#
# docker run -e PORT=9999 --env-file .env prediction_server
#
FROM python:3.10-slim

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y git && \
    rm -rf /var/lib/apt/lists/*
    
# Allow statements and log messages to immediately appear in the Knative logs
ENV PYTHONUNBUFFERED True

# Copy local code to the container image.
ENV APP_HOME /app
WORKDIR $APP_HOME

# Add gcp_utils to PYTHONPATH, so it will look for modules there.
ENV PYTHONPATH "${PYTHONPATH}:${APP_HOME}/gcp_utils"

# Hard code the project id
ENV GOOGLE_CLOUD_PROJECT phase-prediction

# Copy application dependency manifests to the container image.
# Copying this separately prevents re-running pip install on every code change.
COPY requirements.txt $APP_HOME/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy all files including subdirectories in to the home directory in the container
COPY . $APP_HOME

# Run the prediction_server on container startup.
CMD ["python", "prediction_server"]
