#!/usr/bin/env bash
#
# Build and deploy Docker image for prediction_server
#
set -x  # verbose echo mode on so can see expansion of variables etc.

# see if first parameter is "cloud_build".  It will indicate whether to use remote build
if [ "$1" == "cloud_build" ]; then
    CLOUD_BUILD="true"
else
    CLOUD_BUILD="false"
fi

# see what ENV we are building, check ENV variable
if [ $ENV == "PROD" ]; then
  ENV="PROD"
else
  ENV="TEST"
fi

# find out the name of the directory containing this script
BUILD_DIR="$(dirname $( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd ))"
PROJECT_DIR="$(dirname "${BUILD_DIR}")"


echo $BUILD_DIR
cp "${BUILD_DIR}/build/Dockerfile" "${PROJECT_DIR}/Dockerfile"

# shellcheck disable=SC1101
if [ "$CLOUD_BUILD" == "true" ]; then
  gcloud builds submit "$PROJECT_DIR" \
    --tag "us-central1-docker.pkg.dev/phase-predition/containers/prediction-server-${ENV}" \
    --region us-central1
else
  # to test build locally:
  docker build -t "prediction-server-${ENV}" -f "./Dockerfile" "${PROJECT_DIR}"

  # push docker image to cloud artifact registry


fi

BUILD_STATUS=$?

rm -f "${PROJECT_DIR}/Dockerfile"

# Check the exit status
if ! [ $BUILD_STATUS -eq 0 ]; then
    echo "Build failed...not deploying."
    exit 1
fi

# if we get here, build succeeded, but do not auto deploy for now
echo "Build succeeded...ready to deploy."
exit 0

# eventually this will push out to instance group
