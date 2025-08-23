#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   ./seed-ssm.sh [path/to/.env.prod] [aws-profile] [aws-region]
# Defaults:
#   ENV_FILE=./backend/.env.prod
#   PROFILE=default
#   REGION=eu-central-1

ENV_FILE="${1:-./backend/.env.prod}"
PROFILE="${2:-default}"
REGION="${3:-eu-central-1}"

# Base SSM path namespace
BASE="/majidkhoshrou/prod"

# Which keys to push and their SSM types
#   String        -> unencrypted
#   SecureString  -> encrypted with KMS (recommended for secrets)
declare -A TYPES=(
  [SECRET_KEY]=SecureString
  [OPENAI_API_KEY]=SecureString
  [TURNSTILE_SITE_KEY]=String
  [TURNSTILE_SECRET]=SecureString
  [SMTP_USER]=String
  [SMTP_PASSWORD]=SecureString
  [REDIS_PASSWORD]=SecureString
)

# ------- helpers -------
die() { echo "ERROR: $*" >&2; exit 1; }

# simple dotenv loader that keeps quoted values intact
load_env() {
  [[ -f "$ENV_FILE" ]] || die "Env file not found: $ENV_FILE"
  # shellcheck disable=SC2163
  while IFS= read -r line || [[ -n "$line" ]]; do
    # skip comments/blank
    [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
    # allow KEY=VALUE (VALUE may contain =, handle quotes)
    key="${line%%=*}"
    val="${line#*=}"
    key="$(echo "$key" | xargs)" # trim
    # strip optional surrounding quotes
    if [[ "$val" =~ ^\".*\"$ ]]; then
      val="${val:1:${#val}-2}"
    elif [[ "$val" =~ ^\'.*\'$ ]]; then
      val="${val:1:${#val}-2}"
    fi
    export "$key=$val"
  done < "$ENV_FILE"
}

confirm() {
  echo "About to seed SSM in profile=$PROFILE region=$REGION under $BASE"
  echo "Keys: ${!TYPES[@]}"
  read -r -p "Continue? [y/N] " ans
  [[ "${ans:-}" =~ ^[Yy]$ ]] || die "Aborted."
}

put_param() {
  local name="$1" value="$2" type="$3"
  local path="$BASE/$name"
  if [[ -z "$value" ]]; then
    echo "⚠️  Skipping $name (empty value)"
    return
  fi
  echo "→ SSM put-parameter $path ($type)"
  aws --profile "$PROFILE" --region "$REGION" ssm put-parameter \
    --name "$path" \
    --type "$type" \
    --value "$value" \
    --overwrite >/dev/null
}

# ------- run -------
load_env
confirm

for key in "${!TYPES[@]}"; do
  # indirect expansion: get env var by name
  val="${!key-}"
  put_param "$key" "$val" "${TYPES[$key]}"
done

echo "✅ Done. Verify with:"
echo "aws --profile $PROFILE --region $REGION ssm get-parameters-by-path --path \"$BASE\" --with-decryption"
