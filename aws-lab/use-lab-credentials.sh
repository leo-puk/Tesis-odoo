#!/usr/bin/env bash
# Source this script to set temporary credentials in the current Bash session.
if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  echo 'Run: source aws-lab/use-lab-credentials.sh' >&2
  exit 1
fi

tesis_use_lab_credentials() {
  local lab_access_key lab_secret_key lab_session_token
  read -r -s -p 'AWS Details access key ID: ' lab_access_key || return 1
  printf '\n'
  read -r -s -p 'AWS Details secret access key: ' lab_secret_key || return 1
  printf '\n'
  read -r -s -p 'AWS Details session token: ' lab_session_token || return 1
  printf '\n'
  if [[ -z "$lab_access_key" || -z "$lab_secret_key" || -z "$lab_session_token" ]]; then
    echo 'All three values are required. Retry with the current AWS Details credentials.' >&2
    return 1
  fi
  AWS_ACCESS_KEY_ID="$lab_access_key" AWS_SECRET_ACCESS_KEY="$lab_secret_key" \
    AWS_SESSION_TOKEN="$lab_session_token" AWS_EC2_METADATA_DISABLED=true \
    aws sts get-caller-identity --region us-east-1 --no-cli-pager || return 1
  export AWS_ACCESS_KEY_ID="$lab_access_key" AWS_SECRET_ACCESS_KEY="$lab_secret_key"
  export AWS_SESSION_TOKEN="$lab_session_token" AWS_EC2_METADATA_DISABLED=true
  export AWS_DEFAULT_REGION=us-east-1
  echo 'Temporary credentials loaded in this shell. Run python3 aws-lab/ec2.py doctor.'
}

tesis_use_lab_credentials
tesis_credentials_status=$?
unset -f tesis_use_lab_credentials
return "$tesis_credentials_status"
