REGION=eu-central-1
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
BUCKET="mk-analytics-${ACCOUNT_ID}-${REGION}"   # must be globally unique

# 1) create
aws s3api create-bucket \
  --bucket "$BUCKET" \
  --region "$REGION" \
  --create-bucket-configuration LocationConstraint="$REGION"

# 2) block all public access
aws s3api put-public-access-block \
  --bucket "$BUCKET" \
  --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

# 3) default encryption (SSE-S3)
aws s3api put-bucket-encryption \
  --bucket "$BUCKET" \
  --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'

# (optional) versioning
aws s3api put-bucket-versioning --bucket "$BUCKET" --versioning-configuration Status=Enabled
