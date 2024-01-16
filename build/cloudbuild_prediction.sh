#!/bin/bash

# Set the project for the gcloud command
gcloud config set project gpt-funhouse

# Clone the repository from Google Cloud Source Repositories if it doesn't exist
if [ ! -d "github_blestxventures_gpt-funhouse" ]; then
    gcloud source repos clone github_blestxventures_gpt-funhouse --project=gpt-funhouse
fi

cd github_blestxventures_gpt-funhouse
git checkout main
git pull origin main

# Navigate to correct directory
cd corpuskeeper/rag

# Check if a parameter was passed to the script
if [ $# -eq 0 ]; then
    echo "No environment value provided, creating dev version"
    ENV_VALUE="dev"
else
    # Use the first parameter as the environment value
    ENV_VALUE=$1
fi

# Submit the build with the environment value as a substitution
#gcloud builds submit --region=us-central1 --config cloudbuild_ingest.yaml --substitutions=_ENV="$ENV_VALUE" .

# call build_deploy-ingest.sh script with environment value as parameter
source ./build_deploy_ingest.sh "$ENV_VALUE"

