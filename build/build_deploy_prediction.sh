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
    --tag "us-central1-docker.pkg.dev/phase-predition/containers/${CKBASE}-ingest" \
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
echo "Build succeeded...not deploying."
exit 0

echo "Build succeeded...deploying."

# always have one production server running, but can scale down to zero for dev
if [ "$ENV" == "prod" ]; then MIN_INSTANCES=0; else MIN_INSTANCES=0; fi
gcloud run deploy ${CKBASE}-ingest \
  --image "us-central1-docker.pkg.dev/phase-prediction/containers/prediction_server" \
  --allow-unauthenticated \
  --region us-central1 \
  --labels "env=${ENV}" \
  --min-instances ${MIN_INSTANCES} \
  --max-instances 10 \
  --timeout 600 \
  --memory 2Gi \
  --set-env-vars "ENV=${ENV},GOOGLE_CLOUD_PROJECT=phase-prediction"

