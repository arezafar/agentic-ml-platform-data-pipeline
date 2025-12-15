# Physical View Cloud Architect Checklist

## Control Plane Isolation
- [ ] Management cluster in dedicated VPC
- [ ] Can reach Target VPC Control Plane only
- [ ] Cannot reach Data Plane

## Agent RBAC
- [ ] Least Privilege enforced
- [ ] Short-lived OIDC tokens, no long-lived keys
- [ ] Credential rotation via Vault
