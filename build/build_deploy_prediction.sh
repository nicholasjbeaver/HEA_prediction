#!/usr/bin/env bash
#
# Build and deploy Docker image for prediction_server
#
# set -x  # verbose echo mode on so can see expansion of variables etc.

# see if first parameter is "cloud_build".  It will indicate whether to use remote build
if [ "$1" = "cloud_build" ]; then
    CLOUD_BUILD="true"
else
    CLOUD_BUILD="false"
fi

# see what ENV we are building, check ENV variable, default to TEST
if [ $ENV = "prod" ]; then
  ENV="prod"
else
  ENV="test"
fi

# find out the name of the directory containing this script (BUILD_DIR)
BUILD_DIR="$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1

# and the parent directory containing that (i.e., the PROJECT_DIR)
PROJECT_DIR="$(dirname $( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd ))"

echo "Using scripts from ${BUILD_DIR} to build ${DOCKER_IMAGE} using project files from ${PROJECT_DIR}"

DOCKER_IMAGE="prediction-server-${ENV}"
REPO_NAME="us-central1-docker.pkg.dev/phase-prediction/containers"

# shellcheck disable=SC1101
if [ "$CLOUD_BUILD" == "true" ]; then

  # cloud build requires a Dockerfile in the project directory
  cp ${BUILD_DIR}/Dockerfile "${PROJECT_DIR}"

  gcloud builds submit "$PROJECT_DIR" \
    --tag "${REPO_NAME}/${DOCKER_IMAGE}" \
    --region us-central1

  # get the exit status of the build
  BUILD_STATUS=$?

  # remove the temporary Dockerfile
  rm -f "${PROJECT_DIR}/Dockerfile"


else
  # to test build locally:
  docker build -t "${DOCKER_IMAGE}" -f "${BUILD_DIR}/Dockerfile" "${PROJECT_DIR}"

  # get the exit status of the build
  BUILD_STATUS=$?

  # push docker image to cloud artifact registry
  docker tag "${DOCKER_IMAGE} ${REPO_NAME}/${DOCKER_IMAGE}"
  docker push "${REPO_NAME}/${DOCKER_IMAGE}"

fi

# Check the exit status
if ! [ $BUILD_STATUS -eq 0 ]; then
    echo "Build failed...not deploying."
    # exit 1
fi

# if we get here, build succeeded, but do not auto deploy for now
echo "Build succeeded...ready to deploy."
# exit 0

# eventually this will push out to instance group
