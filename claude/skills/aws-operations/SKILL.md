---
name: aws-operations
description: AWS CLI operations and best practices. Use when working with AWS services, debugging AWS issues, or managing cloud resources.
---

# AWS Operations Guide

## Authentication

### Profile Management
```bash
# List profiles
aws configure list-profiles

# Use specific profile
export AWS_PROFILE=myprofile
aws s3 ls --profile myprofile

# Assume role
aws sts assume-role --role-arn arn:aws:iam::123456789:role/MyRole --role-session-name session1

# Get current identity
aws sts get-caller-identity
```

### SSO Login
```bash
aws sso login --profile myprofile
aws sso logout
```

## EC2

### Instance Management
```bash
# List instances
aws ec2 describe-instances --query 'Reservations[].Instances[].[InstanceId,State.Name,Tags[?Key==`Name`].Value|[0]]' --output table

# Start/Stop
aws ec2 start-instances --instance-ids i-xxxxx
aws ec2 stop-instances --instance-ids i-xxxxx

# Connect via SSM
aws ssm start-session --target i-xxxxx
```

### Troubleshooting
```bash
# Get console output
aws ec2 get-console-output --instance-id i-xxxxx

# Check instance status
aws ec2 describe-instance-status --instance-id i-xxxxx

# Get system logs
aws ec2 get-console-output --instance-id i-xxxxx --output text
```

## S3

### Basic Operations
```bash
# List buckets
aws s3 ls

# List objects
aws s3 ls s3://bucket/prefix/

# Copy files
aws s3 cp file.txt s3://bucket/
aws s3 cp s3://bucket/file.txt ./

# Sync directories
aws s3 sync ./local s3://bucket/prefix/
aws s3 sync s3://bucket/prefix/ ./local
```

### Advanced
```bash
# Presigned URL (1 hour)
aws s3 presign s3://bucket/file.txt --expires-in 3600

# Delete objects
aws s3 rm s3://bucket/file.txt
aws s3 rm s3://bucket/prefix/ --recursive

# Bucket size
aws s3 ls s3://bucket --recursive --summarize | tail -2
```

## EKS

### Cluster Access
```bash
# Update kubeconfig
aws eks update-kubeconfig --name cluster-name --region us-west-2

# List clusters
aws eks list-clusters

# Describe cluster
aws eks describe-cluster --name cluster-name
```

### Node Groups
```bash
# List node groups
aws eks list-nodegroups --cluster-name cluster-name

# Describe node group
aws eks describe-nodegroup --cluster-name cluster-name --nodegroup-name ng-name
```

## Lambda

### Function Management
```bash
# List functions
aws lambda list-functions --query 'Functions[].[FunctionName,Runtime,LastModified]' --output table

# Invoke function
aws lambda invoke --function-name my-function --payload '{"key":"value"}' output.json

# View logs
aws logs tail /aws/lambda/my-function --follow
```

### Deployment
```bash
# Update code
aws lambda update-function-code --function-name my-function --zip-file fileb://function.zip

# Update config
aws lambda update-function-configuration --function-name my-function --timeout 30
```

## CloudWatch

### Logs
```bash
# List log groups
aws logs describe-log-groups --query 'logGroups[].logGroupName'

# Tail logs
aws logs tail /aws/lambda/my-function --follow --since 1h

# Filter logs
aws logs filter-log-events --log-group-name /aws/lambda/my-function --filter-pattern "ERROR"
```

### Metrics
```bash
# Get metric data
aws cloudwatch get-metric-statistics \
  --namespace AWS/EC2 \
  --metric-name CPUUtilization \
  --dimensions Name=InstanceId,Value=i-xxxxx \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-02T00:00:00Z \
  --period 3600 \
  --statistics Average
```

## IAM

### Users & Roles
```bash
# List users
aws iam list-users --query 'Users[].[UserName,CreateDate]' --output table

# List roles
aws iam list-roles --query 'Roles[].[RoleName,Arn]' --output table

# Get role policy
aws iam get-role-policy --role-name MyRole --policy-name MyPolicy
```

### Policy Simulation
```bash
# Test if action is allowed
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::123456789:user/myuser \
  --action-names s3:GetObject \
  --resource-arns arn:aws:s3:::mybucket/*
```

## RDS

### Instance Management
```bash
# List instances
aws rds describe-db-instances --query 'DBInstances[].[DBInstanceIdentifier,DBInstanceStatus,Engine]' --output table

# Create snapshot
aws rds create-db-snapshot --db-instance-identifier mydb --db-snapshot-identifier mydb-snap

# Reboot
aws rds reboot-db-instance --db-instance-identifier mydb
```

## Secrets Manager

```bash
# List secrets
aws secretsmanager list-secrets --query 'SecretList[].[Name,LastChangedDate]' --output table

# Get secret value
aws secretsmanager get-secret-value --secret-id my-secret --query SecretString --output text

# Create secret
aws secretsmanager create-secret --name my-secret --secret-string '{"user":"admin","pass":"secret"}'
```

## Cost Management

```bash
# Get current month cost
aws ce get-cost-and-usage \
  --time-period Start=$(date -d "$(date +%Y-%m-01)" +%Y-%m-%d),End=$(date +%Y-%m-%d) \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=DIMENSION,Key=SERVICE
```

## Useful JMESPath Queries

```bash
# Filter by tag
--query 'Reservations[].Instances[?Tags[?Key==`Environment` && Value==`prod`]]'

# Select specific fields
--query '[].{Name:Tags[?Key==`Name`].Value|[0],ID:InstanceId}'

# Sort by field
--query 'sort_by(Instances, &LaunchTime)'
```

## Best Practices

### Security
- Use IAM roles over access keys
- Enable MFA for console access
- Use least privilege permissions
- Rotate credentials regularly

### Cost
- Use reserved instances for steady workloads
- Enable Cost Explorer
- Set up billing alerts
- Clean up unused resources

### Operations
- Use tags consistently
- Enable CloudTrail
- Set up CloudWatch alarms
- Use Infrastructure as Code (Terraform/CDK)
