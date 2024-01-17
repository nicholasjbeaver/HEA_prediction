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

PROJECT_DIR="$(dirname $( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd ))"
# and the parent directory containing that (i.e., the PROJECT_DIR)
ROOT_DIR="$(dirname "${BUILD_DIR}")"

echo "Using scripts from ${BUILD_DIR} to build from ${PROJECT_DIR}"

# copy the Dockerfile from the build directory to the project directory...needs to be at top level
# cp "${BUILD_DIR}/Dockerfile" "${PROJECT_DIR}/Dockerfile"

# shellcheck disable=SC1101
if [ "$CLOUD_BUILD" == "true" ]; then
  gcloud builds submit "$PROJECT_DIR" \
    --tag "us-central1-docker.pkg.dev/phase-predition/containers/prediction-server-${ENV}" \
    --region us-central1
else

  DOCKER_IMAGE="prediction-server-${ENV}"
  REPO_NAME="us-central1-docker.pkg.dev/phase-predition/containers"
  # to test build locally:
  docker build -t "${DOCKER_IMAGE}" -f "${BUILD_DIR}/Dockerfile" "${PROJECT_DIR}"

  docker tag ${DOCKER_IMAGE} ${REPO_NAME}/${DOCKER_IMAGE}

  # push docker image to cloud artifact registry
  docker push "${REPO_NAME}/${DOCKER_IMAGE}"

fi

BUILD_STATUS=$?

# rm -f "${PROJECT_DIR}/Dockerfile"

# Check the exit status
if ! [ $BUILD_STATUS -eq 0 ]; then
    echo "Build failed...not deploying."
    # exit 1
fi

# if we get here, build succeeded, but do not auto deploy for now
echo "Build succeeded...ready to deploy."
# exit 0

# eventually this will push out to instance group
