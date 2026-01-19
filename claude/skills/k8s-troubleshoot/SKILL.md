---
name: k8s-troubleshoot
description: Kubernetes troubleshooting guide. 쿠버네티스 트러블슈팅, 파드 오류, 서비스 접속 불가.
allowed-tools: Read, Bash, Grep, Glob
---

# Kubernetes Troubleshooting

## Quick Diagnosis
```bash
kubectl get pods -o wide
kubectl get pods -n <namespace>
kubectl get pods --all-namespaces
kubectl describe pod <name>
kubectl logs <pod> [--previous]
kubectl logs <pod> -c <container>  # multi-container pod
kubectl get events --sort-by='.lastTimestamp'
kubectl get events -n <namespace> --field-selector type=Warning
```

## Pod States

| Status | Cause | Check |
|--------|-------|-------|
| Pending | Resources/scheduling | Node resources, taints |
| ImagePullBackOff | Image issue | Image name, pull secrets |
| CrashLoopBackOff | App crash | Logs, entrypoint |
| OOMKilled | Memory exceeded | Memory limits |

## Debug
```bash
kubectl exec -it <pod> -- /bin/sh
kubectl debug -it <pod> --image=busybox
kubectl port-forward pod/<name> 8080:80
```

## Service Issues
```bash
kubectl get endpoints <service>
kubectl get pods -l <selector>
kubectl run test --rm -it --image=busybox -- nslookup <service>
kubectl get svc <service> -o yaml
```

## ConfigMap & Secret
```bash
# View ConfigMap
kubectl get configmap <name> -o yaml
kubectl describe configmap <name>

# View Secret (base64 decoded)
kubectl get secret <name> -o jsonpath='{.data}' | jq -r 'to_entries[] | "\(.key): \(.value | @base64d)"'
kubectl get secret <name> -o jsonpath='{.data.<key>}' | base64 -d

# Check if mounted correctly
kubectl exec <pod> -- cat /path/to/mounted/config
kubectl exec <pod> -- env | grep <ENV_VAR>
```

## Network Debugging
```bash
# DNS resolution
kubectl run test --rm -it --image=busybox -- nslookup kubernetes.default
kubectl run test --rm -it --image=busybox -- nslookup <service>.<namespace>.svc.cluster.local

# Network connectivity
kubectl run netshoot --rm -it --image=nicolaka/netshoot -- /bin/bash
# Inside: curl, ping, dig, tcpdump, netstat

# Check network policies
kubectl get networkpolicies -A
kubectl describe networkpolicy <name>

# Service mesh (Istio)
istioctl analyze
istioctl proxy-status
kubectl logs <pod> -c istio-proxy
```

## Resources
```bash
kubectl top nodes
kubectl top pods
kubectl describe node <name> | grep -A5 "Allocated"
```

## Rollout
```bash
kubectl rollout status deployment/<name>
kubectl rollout history deployment/<name>
kubectl rollout undo deployment/<name>
kubectl rollout restart deployment/<name>
```

## Common Fixes
```bash
# Force delete stuck pod
kubectl delete pod <name> --force --grace-period=0

# Restart deployment
kubectl rollout restart deployment/<name>

# Check logs of previous crash
kubectl logs <pod> --previous

# Scale deployment
kubectl scale deployment/<name> --replicas=3
```

## HPA & PDB
```bash
# Horizontal Pod Autoscaler
kubectl get hpa
kubectl describe hpa <name>
kubectl top pods  # Check current resource usage

# Pod Disruption Budget
kubectl get pdb
kubectl describe pdb <name>
# If blocked: check minAvailable/maxUnavailable settings
```

## Storage Issues
```bash
# PersistentVolume status
kubectl get pv
kubectl get pvc -A
kubectl describe pvc <name>

# Common PVC issues:
# - Pending: No matching PV, check storageClass
# - Lost: Underlying storage deleted
```
