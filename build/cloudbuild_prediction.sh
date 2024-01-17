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
PROJECT_DIR="HEA_prediction_${ENV}"
echo "Building for environment: $ENV in directory: ${PROJECT_DIR}"

# Clone the repository from GitHub, create it if it doesn't exist
if [ ! -d "$PROJECT_DIR" ]; then
    echo "Cloning repository into ${PROJECT_DIR}"
    git clone https://github.com/nicholasjbeaver/HEA_prediction "$PROJECT_DIR"

    cd "$PROJECT_DIR"

    # Checkout the main branch
    git checkout main
    git pull origin main
else
    echo "Repository already exists, will build with existing files in ${PROJECT_DIR}"
    cd "$PROJECT_DIR"
fi

# Submit the build with the environment value as a substitution
gcloud builds submit --region=us-central1 --config "./build/cloudbuild_prediction.yaml" --substitutions=_ENV="$ENV" .

echo "Done"