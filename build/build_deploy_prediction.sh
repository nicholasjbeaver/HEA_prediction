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


# start from the corpuskeeper/rag/build directory
CK_INGEST_DIR="$(dirname $( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd ))"
CK_DIR="$(dirname "$CK_INGEST_DIR")"


echo $CK_INGEST_DIR
cp "$CK_INGEST_DIR/build/Dockerfile" "$CK_DIR/Dockerfile"

# shellcheck disable=SC1101
if [ "$CLOUD_BUILD" == "true" ]; then
  gcloud builds submit "$CK_DIR" \
    --tag "us-central1-docker.pkg.dev/phase-predition/containers/prediction-server-$CKBASE" \
    --region us-central1
else
  # to test build locally:
  docker build -t "${CKBASE}-ingest" -f "$CK_INGEST_DIR/Dockerfile" "$CK_DIR"

BUILD_STATUS=$?

rm -f "$CK_DIR/Dockerfile"

# Check the exit status
if ! [ $BUILD_STATUS -eq 0 ]; then
    echo "Build failed...not deploying."
    exit 1
fi

# if we get here, build succeeded, but do not auto deploy for now
echo "Build succeeded...ready to deploy."
exit 0

# eventually this will push out to instance group
