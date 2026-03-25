#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${REPO_ROOT}/deploy/ec2/aws-stack.env"
TEMPLATE_FILE="${REPO_ROOT}/deploy/ec2/cloudformation/trading-pro-single-host.yaml"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing ${ENV_FILE}. Copy deploy/ec2/aws-stack.env.example to aws-stack.env and fill it in first." >&2
  exit 1
fi

if [[ ! -f "${TEMPLATE_FILE}" ]]; then
  echo "Missing CloudFormation template at ${TEMPLATE_FILE}." >&2
  exit 1
fi

if ! command -v aws >/dev/null 2>&1; then
  echo "AWS CLI is required to launch the EC2 stack." >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

: "${AWS_REGION:?AWS_REGION must be set}"
: "${STACK_NAME:?STACK_NAME must be set}"
: "${INSTANCE_NAME:?INSTANCE_NAME must be set}"
: "${VPC_ID:?VPC_ID must be set}"
: "${SUBNET_ID:?SUBNET_ID must be set}"
: "${KEY_PAIR_NAME:?KEY_PAIR_NAME must be set}"
: "${ADMIN_CIDR:?ADMIN_CIDR must be set}"
: "${INSTANCE_TYPE:?INSTANCE_TYPE must be set}"
: "${ROOT_VOLUME_GB:?ROOT_VOLUME_GB must be set}"
: "${AMI_PARAMETER:?AMI_PARAMETER must be set}"

aws cloudformation deploy \
  --region "${AWS_REGION}" \
  --stack-name "${STACK_NAME}" \
  --template-file "${TEMPLATE_FILE}" \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    InstanceName="${INSTANCE_NAME}" \
    VpcId="${VPC_ID}" \
    SubnetId="${SUBNET_ID}" \
    KeyPairName="${KEY_PAIR_NAME}" \
    AdminCidr="${ADMIN_CIDR}" \
    InstanceType="${INSTANCE_TYPE}" \
    RootVolumeSize="${ROOT_VOLUME_GB}" \
    UbuntuAmiId="${AMI_PARAMETER}"

echo
echo "Stack deployed. Outputs:"
aws cloudformation describe-stacks \
  --region "${AWS_REGION}" \
  --stack-name "${STACK_NAME}" \
  --query 'Stacks[0].Outputs[].{Key:OutputKey,Value:OutputValue}' \
  --output table

echo
echo "Next steps:"
echo "  1. Point your external DNS A records to the Elastic IP output."
echo "  2. SSH into the instance with your EC2 key pair."
echo "  3. Configure the GitHub deploy key on the host."
echo "  4. Clone the repo to /srv/trading-pro/app."
echo "  5. Copy deploy/ec2/trading-pro.env.example to /etc/trading-pro/trading-pro.env and fill in real values."
echo "  6. Run scripts/ec2/bootstrap_ec2.sh, then scripts/ec2/deploy_ec2.sh."
