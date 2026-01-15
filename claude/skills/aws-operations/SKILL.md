---
name: aws-operations
description: AWS CLI operations and best practices. AWS 작업, EC2, S3, EKS, Lambda.
allowed-tools: Read, Bash, Grep, Glob
---

# AWS Operations

## Auth
```bash
aws sts get-caller-identity
aws sso login --profile myprofile
export AWS_PROFILE=myprofile
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
```

## Tips
- Use IAM roles over access keys
- Use `--query` for filtering
- Use `--output table` for readability
