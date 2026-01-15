---
name: k8s-troubleshoot
description: Kubernetes troubleshooting and debugging guide. Use when diagnosing pod failures, networking issues, resource problems, or cluster errors.
---

# Kubernetes Troubleshooting

## Quick Diagnosis Flow

```
Pod not running?
  → kubectl describe pod <name>
  → kubectl logs <pod> [--previous]

Service not accessible?
  → kubectl get endpoints
  → kubectl describe svc <name>

Node issues?
  → kubectl describe node <name>
  → kubectl top nodes
```

## Pod Issues

### Check Pod Status
```bash
# Overview
kubectl get pods -o wide
kubectl get pods --field-selector=status.phase!=Running

# Detailed info
kubectl describe pod <pod-name>

# Events (recent issues)
kubectl get events --sort-by='.lastTimestamp'
```

### Common Pod States

| Status | Cause | Solution |
|--------|-------|----------|
| Pending | No resources / scheduling | Check node resources, taints |
| ImagePullBackOff | Wrong image / no access | Verify image name, pull secrets |
| CrashLoopBackOff | App crashes on start | Check logs, entry point |
| OOMKilled | Memory limit exceeded | Increase memory limit |
| CreateContainerError | Config issue | Check configmaps, secrets |

### Debug Containers
```bash
# Current logs
kubectl logs <pod> -c <container>

# Previous crash logs
kubectl logs <pod> --previous

# Follow logs
kubectl logs -f <pod>

# Exec into container
kubectl exec -it <pod> -- /bin/sh

# Debug with ephemeral container
kubectl debug -it <pod> --image=busybox
```

## Service & Networking

### Service Not Working
```bash
# Check endpoints exist
kubectl get endpoints <service>

# Verify selector matches pods
kubectl get pods -l <selector>

# Test DNS resolution
kubectl run test --rm -it --image=busybox -- nslookup <service>

# Test connectivity
kubectl run test --rm -it --image=busybox -- wget -qO- <service>:<port>
```

### Ingress Issues
```bash
# Check ingress status
kubectl describe ingress <name>

# Verify backend service
kubectl get svc <backend-service>

# Check ingress controller logs
kubectl logs -n ingress-nginx -l app.kubernetes.io/name=ingress-nginx
```

## Resource Issues

### Check Resource Usage
```bash
# Node resources
kubectl top nodes

# Pod resources
kubectl top pods

# Detailed node capacity
kubectl describe node <name> | grep -A5 "Allocated resources"
```

### Common Resource Problems

**Pod Pending - Insufficient Resources**
```bash
# Find nodes with available resources
kubectl describe nodes | grep -A5 "Allocated resources"

# Check resource requests
kubectl get pod <name> -o jsonpath='{.spec.containers[*].resources}'
```

**OOMKilled**
```bash
# Check memory limits
kubectl describe pod <name> | grep -A3 "Limits"

# Monitor memory usage
kubectl top pod <name>
```

## Storage Issues

### PVC Pending
```bash
# Check PVC status
kubectl describe pvc <name>

# Verify storage class exists
kubectl get storageclass

# Check PV availability
kubectl get pv
```

### Volume Mount Failures
```bash
# Check pod events for mount errors
kubectl describe pod <name> | grep -A10 Events

# Verify secret/configmap exists
kubectl get secret <name>
kubectl get configmap <name>
```

## Deployment Issues

### Rollout Stuck
```bash
# Check rollout status
kubectl rollout status deployment/<name>

# View rollout history
kubectl rollout history deployment/<name>

# Rollback
kubectl rollout undo deployment/<name>
```

### Scaling Issues
```bash
# Check HPA status
kubectl describe hpa <name>

# Verify metrics server
kubectl top pods
```

## Node Issues

### Node NotReady
```bash
# Check node conditions
kubectl describe node <name> | grep -A10 Conditions

# Check kubelet logs (on node)
journalctl -u kubelet -f

# Check system resources (on node)
df -h
free -m
```

## Useful Debug Commands

```bash
# Get all resources in namespace
kubectl get all -n <namespace>

# Watch resources
kubectl get pods -w

# Get YAML of running resource
kubectl get pod <name> -o yaml

# Diff against applied config
kubectl diff -f manifest.yaml

# Force delete stuck pod
kubectl delete pod <name> --force --grace-period=0

# Port forward for debugging
kubectl port-forward pod/<name> 8080:80
```

## Quick Reference

See [COMMANDS.md](COMMANDS.md) for extended command reference.
