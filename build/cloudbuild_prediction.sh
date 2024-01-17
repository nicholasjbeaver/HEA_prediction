#!/usr/bin/env bash
#
# Use cloudbuild to build and deploy the prediction service
#

# set -x

# Clone the repository from GitHub, create it if it doesn't exist
if [ ! -d "HEA_prediction_build" ]; then
    echo "Cloning repository"
    git clone https://github.com/nicholasjbeaver/HEA_prediction HEA_prediction_build
fi

cd HEA_prediction_build

# Checkout the main branch
git checkout main
git pull origin main

# Navigate to correct directory
cd build

# Submit the build with the environment value as a substitution
# gcloud builds submit --region=us-central1 --config cloudbuild_ingest.yaml --substitutions=_TESTING="$TESTING" .

# call build_deploy-ingest.sh script with environment value as parameter
# source ./build_deploy_prediction.sh "TESTING"=$TESTING
echo "Done"