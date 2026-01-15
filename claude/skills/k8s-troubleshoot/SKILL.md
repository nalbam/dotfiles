---
name: k8s-troubleshoot
description: Kubernetes troubleshooting guide. 쿠버네티스 트러블슈팅, 파드 오류, 서비스 접속 불가.
allowed-tools: Read, Bash, Grep, Glob
---

# Kubernetes Troubleshooting

## Quick Diagnosis
```bash
kubectl get pods -o wide
kubectl describe pod <name>
kubectl logs <pod> [--previous]
kubectl get events --sort-by='.lastTimestamp'
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
```
