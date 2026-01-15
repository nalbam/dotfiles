# Kubernetes Command Reference

## Context & Namespace

```bash
# Switch context
kubectl config use-context <context>

# Set default namespace
kubectl config set-context --current --namespace=<ns>

# List contexts
kubectl config get-contexts
```

## Resource Management

```bash
# Apply manifests
kubectl apply -f <file.yaml>
kubectl apply -k <kustomize-dir>

# Delete resources
kubectl delete -f <file.yaml>
kubectl delete pod <name> --grace-period=0 --force

# Patch resources
kubectl patch deployment <name> -p '{"spec":{"replicas":3}}'

# Scale
kubectl scale deployment <name> --replicas=5
```

## Logs & Events

```bash
# Pod logs
kubectl logs <pod> -c <container> --tail=100
kubectl logs -f <pod> --since=1h
kubectl logs -l app=myapp --all-containers

# Events
kubectl get events --sort-by='.lastTimestamp'
kubectl get events --field-selector type=Warning
```

## Exec & Debug

```bash
# Execute command
kubectl exec <pod> -- <command>
kubectl exec -it <pod> -- /bin/sh

# Copy files
kubectl cp <pod>:<path> <local-path>
kubectl cp <local-path> <pod>:<path>

# Port forward
kubectl port-forward <pod> 8080:80
kubectl port-forward svc/<service> 8080:80
```

## Resource Inspection

```bash
# Get with details
kubectl get pods -o wide
kubectl get pods -o yaml
kubectl get pods -o jsonpath='{.items[*].metadata.name}'

# Describe
kubectl describe pod <name>
kubectl describe node <name>

# Resource usage
kubectl top nodes
kubectl top pods --containers
```

## Labels & Selectors

```bash
# Filter by label
kubectl get pods -l app=myapp
kubectl get pods -l 'app in (web,api)'

# Add label
kubectl label pod <name> env=prod

# Remove label
kubectl label pod <name> env-
```

## Rollout Management

```bash
# Status
kubectl rollout status deployment/<name>

# History
kubectl rollout history deployment/<name>

# Undo
kubectl rollout undo deployment/<name>
kubectl rollout undo deployment/<name> --to-revision=2

# Restart
kubectl rollout restart deployment/<name>
```

## Secrets & ConfigMaps

```bash
# Create secret
kubectl create secret generic <name> --from-literal=key=value
kubectl create secret generic <name> --from-file=<path>

# View secret (decoded)
kubectl get secret <name> -o jsonpath='{.data.key}' | base64 -d

# Create configmap
kubectl create configmap <name> --from-file=<path>
```

## Network Debugging

```bash
# DNS test
kubectl run test --rm -it --image=busybox -- nslookup kubernetes

# HTTP test
kubectl run test --rm -it --image=curlimages/curl -- curl -v <url>

# Network policy test
kubectl run test --rm -it --image=nicolaka/netshoot -- bash
```

## Cluster Info

```bash
# Cluster info
kubectl cluster-info
kubectl get nodes -o wide

# API resources
kubectl api-resources
kubectl api-versions

# Explain resource
kubectl explain pod.spec.containers
```
