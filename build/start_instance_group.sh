###### WIP DO NOT USE ######

#!/bin/bash

# See if PRODUCTION env variable is set, if so, set to prod
if [ -z "$PRODUCTION" ]; then
  ENV=prod
else
  ENV=test
fi


# Define variables
PROJECT_ID="phase-prediction"
INSTANCE_GROUP_NAME="prediction-server-group"
TEMPLATE_NAME="prediction-server-${ENV}-e2-standard-2-spot-template-1"
ZONE="us-central1-c"
REGION="us-central1"
TARGET_SIZE=1  # Set the target size of the instance group

# Set the GCP project
gcloud config set project $PROJECT_ID

# Create the instance group based on the template
gcloud compute instance-groups managed create $INSTANCE_GROUP_NAME \
    --template $TEMPLATE_NAME \
    --size $TARGET_SIZE \
    --region $REGION
    --target=balanced

echo "Instance group $INSTANCE_GROUP_NAME created based on template $TEMPLATE_NAME in region $REGION."


gcloud compute instance-groups managed set-autoscaling MIG_NAME \
  --max-num-replicas=MAX_INSTANCES \
  --min-num-replicas=MIN_INSTANCES \
  --update-stackdriver-metric=pubsub.googleapis.com/subscription/num_undelivered_messages \
  --stackdriver-metric-filter="resource.type=\"pubsub_subscription\" AND resource.labels.subscription_id=\"SUBSCRIPTION_ID\"" \
  --stackdriver-metric-single-instance-assignment=NUMBER_OF_MESSAGES_TO_ASSIGN_TO_EACH_VM


  gcloud beta compute instance-groups managed create prediction-server-group-1 --project=phase-prediction --base-instance-name=prediction-server-group-1 --size=1 --description=a\ cluster\ of\ prediction_servers --template=projects/phase-prediction/regions/us-central1/instanceTemplates/prediction-server-test-e2-standard-2-spot-template-1 --zone=us-central1-c --list-managed-instances-results=PAGELESS --no-force-update-on-repair --default-action-on-vm-failure=repair --standby-policy-mode=manual

  gcloud beta compute instance-groups managed create prediction-server-group-1 --project=phase-prediction --base-instance-name=prediction-server-group-1 --size=1 --description=a\ cluster\ of\ prediction_servers --template=projects/phase-prediction/regions/us-central1/instanceTemplates/prediction-server-test-e2-standard-2-spot-template-1 --zone=us-central1-c --list-managed-instances-results=PAGELESS --no-force-update-on-repair --default-action-on-vm-failure=repair --standby-policy-mode=manual && gcloud beta compute instance-groups managed set-autoscaling prediction-server-group-1 --project=phase-prediction --zone=us-central1-c --cool-down-period=60 --max-num-replicas=3 --min-num-replicas=1 --mode=on --stackdriver-metric-filter=resource.type\ =\ pubsub_subscription\ AND\ resource.labels.subscription_id\ =\ \"prediction_topic-prediction_server\" --update-stackdriver-metric=pubsub.googleapis.com/subscription/num_undelivered_messages --stackdriver-metric-single-instance-assignment=1.0