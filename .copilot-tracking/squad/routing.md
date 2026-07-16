# Squad Routing Rules

| Request Pattern | Primary Role | Fallback Role | Notes |
|-----------------|--------------|---------------|-------|
| Architecture / Module boundaries / Contract design | MVP Product/Tech Integrator | Python Delivery Lead | Design-phase decisions |
| Security / Identity / OIDC / RBAC / Policy | Security/Identity + Governance Lead | DevOps + IaC Engineer | Governance baseline |
| Reliability / SLO / SLI / Alerts / Playbooks | Platform Reliability + SRE Lead | DevOps + IaC Engineer | Operability checks |
| Infrastructure / Bicep / IaC / Private networks | DevOps + IaC Engineer | Security/Identity + Governance Lead | Provisioning and config |
| CI/CD / Workflows / Delivery automation | DevOps + IaC Engineer | Python Delivery Lead | Build/test/promote |
| Core pipeline / Detector / Recommender / Orchestrator | Python Delivery Lead | MVP Product/Tech Integrator | Implementation |
| Evaluation / Red-team / Quality / Tests | Evaluation + Quality Engineer | Platform Reliability + SRE Lead | Validation gates |
| Integration / MVP feature assembly | MVP Product/Tech Integrator | Python Delivery Lead | Assembly phase |
| Operational runbooks / Release readiness | MVP Product/Tech Integrator | Platform Reliability + SRE Lead | Go-live phase |
| Emergency / Incident response | Platform Reliability + SRE Lead | MVP Product/Tech Integrator | On-call |
