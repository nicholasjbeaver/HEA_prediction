#!/usr/bin/env bash
#
# Use cloudbuild to build and deploy the prediction service
#

# set -x

# Set the environment variable
ENV=$1

# if it is set and is equal to "PROD", set it to "PROD", else set it to TEST
if [ "$ENV" = "prod" ]; then
    ENV="prod"
else
    ENV="test"
fi

# Set the build directory so it is unique for each environment
BUILD_DIR="HEA_prediction_${ENV}"
echo "Building for environment: $ENV in directory: ${BUILD_DIR}"


# Clone the repository from GitHub, create it if it doesn't exist
if [ ! -d "$BUILD_DIR" ]; then
    echo "Cloning repository"
    git clone https://github.com/nicholasjbeaver/HEA_prediction "$BUILD_DIR"

    cd "$BUILD_DIR"

    # Checkout the main branch
    git checkout main
    git pull origin main
else
    echo "Repository already exists, will build with existing files"
fi

cd "$BUILD_DIR"

# Submit the build with the environment value as a substitution
# gcloud builds submit --region=us-central1 --config cloudbuild_ingest.yaml --substitutions=_ENV="$ENV" .

# call build_deploy-ingest.sh script with environment value as parameter
# source ./build_deploy_prediction.sh
echo "Done"