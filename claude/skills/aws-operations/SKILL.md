---
name: aws-operations
description: AWS CLI operations and best practices. AWS 작업, EC2, S3, EKS, Lambda.
allowed-tools: Read, Bash, Grep, Glob
---

# AWS Operations

**IMPORTANT: 모든 설명과 요약은 한국어로 작성하세요. 단, 코드 예시와 명령어는 원문 그대로 유지합니다.**

## Auth with AWS Vault
```bash
# Login and execute command
export AWS_VAULT= && aws-vault exec <profile> -- <command>

# Examples
export AWS_VAULT= && aws-vault exec daangn-alpha -- aws sts get-caller-identity
export AWS_VAULT= && aws-vault exec daangn-prod -- kubectl get pods

# Start subshell with credentials
export AWS_VAULT= && aws-vault exec daangn-alpha

# List profiles
aws-vault list

# Clear cached credentials
aws-vault clear <profile>
```

## Auth & Profile
```bash
# Check current identity
aws sts get-caller-identity

# SSO login (without aws-vault)
aws sso login --profile myprofile
export AWS_PROFILE=myprofile

# List configured profiles
aws configure list-profiles
```

## EC2
```bash
aws ec2 describe-instances --query 'Reservations[].Instances[].[InstanceId,State.Name,Tags[?Key==`Name`].Value|[0]]' --output table
aws ec2 start-instances --instance-ids i-xxxxx
aws ec2 stop-instances --instance-ids i-xxxxx
aws ssm start-session --target i-xxxxx
```

## S3
```bash
aws s3 ls s3://bucket/prefix/
aws s3 cp file.txt s3://bucket/
aws s3 sync ./local s3://bucket/prefix/
aws s3 presign s3://bucket/file.txt --expires-in 3600
```

## EKS
```bash
aws eks update-kubeconfig --name cluster-name --region us-west-2
aws eks list-clusters
aws eks describe-cluster --name cluster-name
```

## Lambda
```bash
aws lambda list-functions --query 'Functions[].[FunctionName,Runtime]' --output table
aws lambda invoke --function-name my-func --payload '{}' out.json
aws logs tail /aws/lambda/my-func --follow
```

## Secrets Manager
```bash
aws secretsmanager list-secrets
aws secretsmanager get-secret-value --secret-id name --query SecretString --output text
```

## CloudWatch
```bash
aws logs tail /aws/lambda/my-func --follow --since 1h
aws logs filter-log-events --log-group-name name --filter-pattern "ERROR"
aws cloudwatch get-metric-statistics --namespace AWS/EC2 --metric-name CPUUtilization \
  --start-time 2024-01-01T00:00:00Z --end-time 2024-01-02T00:00:00Z \
  --period 3600 --statistics Average --dimensions Name=InstanceId,Value=i-xxxxx
```

## IAM
```bash
# Users and roles
aws iam list-users --query 'Users[].[UserName,CreateDate]' --output table
aws iam list-roles --query 'Roles[].[RoleName,Arn]' --output table
aws iam get-role --role-name MyRole

# Policies
aws iam list-attached-role-policies --role-name MyRole
aws iam get-policy --policy-arn arn:aws:iam::aws:policy/ReadOnlyAccess
aws iam simulate-principal-policy --policy-source-arn arn:aws:iam::123456789012:user/myuser \
  --action-names s3:GetObject --resource-arns arn:aws:s3:::mybucket/*
```

## VPC & Network
```bash
# VPC info
aws ec2 describe-vpcs --query 'Vpcs[].[VpcId,CidrBlock,Tags[?Key==`Name`].Value|[0]]' --output table
aws ec2 describe-subnets --query 'Subnets[].[SubnetId,VpcId,CidrBlock,AvailabilityZone]' --output table

# Security groups
aws ec2 describe-security-groups --group-ids sg-xxxxx
aws ec2 describe-security-group-rules --filter Name=group-id,Values=sg-xxxxx

# Network debugging
aws ec2 describe-network-interfaces --filters Name=subnet-id,Values=subnet-xxxxx
```

## RDS
```bash
aws rds describe-db-instances --query 'DBInstances[].[DBInstanceIdentifier,DBInstanceStatus,Engine]' --output table
aws rds describe-db-clusters --query 'DBClusters[].[DBClusterIdentifier,Status,Engine]' --output table
aws rds describe-db-snapshots --db-instance-identifier mydb --query 'DBSnapshots[].[DBSnapshotIdentifier,SnapshotCreateTime]'
```

## Cost
```bash
# Current month cost
aws ce get-cost-and-usage --time-period Start=$(date -u +%Y-%m-01),End=$(date -u +%Y-%m-%d) \
  --granularity MONTHLY --metrics BlendedCost --group-by Type=DIMENSION,Key=SERVICE

# Cost forecast
aws ce get-cost-forecast --time-period Start=$(date -u +%Y-%m-%d),End=$(date -u +%Y-%m-01 -d "+1 month") \
  --metric BLENDED_COST --granularity MONTHLY
```

## Troubleshooting
```bash
# Debug API calls
aws sts get-caller-identity --debug 2>&1 | head -50

# Check service quotas
aws service-quotas list-service-quotas --service-code ec2

# Common errors
# - ExpiredToken: Re-authenticate with `aws sso login`
# - AccessDenied: Check IAM permissions with `simulate-principal-policy`
# - InvalidParameterValue: Verify resource exists in correct region
```

## Tips
- Use IAM roles over access keys
- Use `--query` for JMESPath filtering
- Use `--output table` for readability, `json` for scripting
- Use `--dry-run` for EC2 operations to test permissions
- Set `AWS_PAGER=""` to disable pagination
