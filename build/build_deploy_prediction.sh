#!/usr/bin/env bash
#
# Build Corpus Keeper Docker image for ingestion server
#
set -x  # verbose echo mode on so can see expansion of variables etc.

# start from the corpuskeeper/rag/build directory
CK_INGEST_DIR="$(dirname $( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd ))"
CK_DIR="$(dirname "$CK_INGEST_DIR")"
ENV=${1:-dev}
if [ "$ENV" == "prod" ]; then CKBASE="corpuskeeper"; else CKBASE="ck${ENV}"; fi

echo $CK_INGEST_DIR
cp "$CK_INGEST_DIR/build/Dockerfile" "$CK_DIR/Dockerfile"

# shellcheck disable=SC1101
gcloud builds submit "$CK_DIR" \
  --tag "us-central1-docker.pkg.dev/gpt-funhouse/containers/${CKBASE}-ingest" \
  --region us-central1


# to test build locally:
#docker build -t "${CKBASE}-ingest" -f "$CK_INGEST_DIR/Dockerfile" "$CK_DIR"

BUILD_STATUS=$?

rm -f "$CK_DIR/Dockerfile"

# Check the exit status
if ! [ $BUILD_STATUS -eq 0 ]; then
    echo "Build failed...not deploying."
    exit 1
fi

echo "Build succeeded...deploying."

# always have one production server running, but can scale down to zero for dev
if [ "$ENV" == "prod" ]; then MIN_INSTANCES=0; else MIN_INSTANCES=0; fi
gcloud run deploy ${CKBASE}-ingest \
  --image "us-central1-docker.pkg.dev/gpt-funhouse/containers/${CKBASE}-ingest" \
  --allow-unauthenticated \
  --region us-central1 \
  --labels "env=${ENV}" \
  --min-instances ${MIN_INSTANCES} \
  --max-instances 10 \
  --timeout 600 \
  --memory 2Gi \
  --set-env-vars "ENV=${ENV},GOOGLE_CLOUD_PROJECT=gpt-funhouse"

