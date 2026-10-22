import asyncio
import json
from datetime import datetime, timedelta, timezone
from app.core.db import prisma

async def seed():
    await prisma.connect()
    print("Connected to PostgreSQL via Prisma.")

    # 1. Organization
    org = await prisma.organization.find_first()
    if not org:
        org = await prisma.organization.create(data={"name": "Sentinel Enterprise Corp"})
        print(f"Created organization: {org.name} ({org.id})")
    else:
        print(f"Found existing organization: {org.name} ({org.id})")

    # 2. Cluster
    cluster = await prisma.cluster.find_first(where={"organizationId": org.id})
    if not cluster:
        cluster = await prisma.cluster.create(
            data={
                "organizationId": org.id,
                "name": "us-east-1-prod-cluster",
                "region": "us-east-1",
                "provider": "AWS EKS",
            }
        )
        print(f"Created cluster: {cluster.name} ({cluster.id})")
    else:
        print(f"Found existing cluster: {cluster.name} ({cluster.id})")

    # 3. Namespaces
    for ns_name in ["default", "sock-shop", "kube-system"]:
        existing_ns = await prisma.namespace.find_first(where={"clusterId": cluster.id, "name": ns_name})
        if not existing_ns:
            await prisma.namespace.create(data={"clusterId": cluster.id, "name": ns_name})
    ns_sockshop = await prisma.namespace.find_first(where={"clusterId": cluster.id, "name": "sock-shop"})
    ns_default = await prisma.namespace.find_first(where={"clusterId": cluster.id, "name": "default"}) or ns_sockshop

    # 4. Nodes
    nodes = []
    node_configs = [
        {"name": "k8s-control-plane-01", "cpuCores": 8, "memoryBytes": 32 * 1024**3, "status": "Ready"},
        {"name": "k8s-worker-node-01", "cpuCores": 16, "memoryBytes": 64 * 1024**3, "status": "Ready"},
        {"name": "k8s-worker-node-02", "cpuCores": 16, "memoryBytes": 64 * 1024**3, "status": "Ready"},
        {"name": "k8s-worker-node-03", "cpuCores": 16, "memoryBytes": 64 * 1024**3, "status": "Ready"},
    ]
    for cfg in node_configs:
        node = await prisma.node.find_first(where={"clusterId": cluster.id, "name": cfg["name"]})
        if not node:
            node = await prisma.node.create(
                data={
                    "clusterId": cluster.id,
                    "name": cfg["name"],
                    "status": cfg["status"],
                    "cpuCores": cfg["cpuCores"],
                    "memoryBytes": cfg["memoryBytes"],
                }
            )
        nodes.append(node)
    print(f"Configured {len(nodes)} cluster nodes.")

    # 5. Microservices matching GraphSAGE (7 Sock Shop nodes + core services)
    services_meta = [
        ("frontend", "Customer-facing web & mobile API gateway [Tier: Tier 1 - Mission Critical]"),
        ("carts", "In-memory session cart & checkout state orchestrator [Tier: Tier 1 - Mission Critical]"),
        ("orders", "Transactional order placement & checkout workflow [Tier: Tier 1 - Mission Critical]"),
        ("payment", "Payment authorization & settlement gateway [Tier: Tier 1 - Mission Critical]"),
        ("catalogue", "Product catalogue, inventory search & metadata [Tier: Tier 2 - Business Essential]"),
        ("user", "User authentication, profile & credentials store [Tier: Tier 2 - Business Essential]"),
        ("shipping", "Fulfillment dispatch & tracking carrier updates [Tier: Tier 3 - Standard Support]"),
    ]
    services = {}
    for s_name, desc in services_meta:
        svc = await prisma.service.find_first(where={"organizationId": org.id, "name": s_name})
        if not svc:
            svc = await prisma.service.create(
                data={
                    "organizationId": org.id,
                    "clusterId": cluster.id,
                    "name": s_name,
                    "description": desc,
                }
            )
        else:
            await prisma.service.update(where={"id": svc.id}, data={"description": desc})
        services[s_name] = svc

        # Pods per service
        for i in range(1, 4):
            pod_name = f"{s_name}-pod-0{i}"
            assigned_node = nodes[i % len(nodes)]
            existing_pod = await prisma.pod.find_first(where={"serviceId": svc.id, "name": pod_name})
            if not existing_pod:
                await prisma.pod.create(
                    data={
                        "namespaceId": ns_sockshop.id if ns_sockshop else ns_default.id,
                        "nodeId": assigned_node.id,
                        "serviceId": svc.id,
                        "name": pod_name,
                        "status": "Running",
                        "restarts": 0,
                    }
                )
    print(f"Configured {len(services)} microservices with attached pods.")

    # 6. Deployments & Risk Scores
    deployments_data = [
        ("frontend", "v2.4.1", "DEPLOYED", 0.12, [{"feature": "deployment_size", "contribution": 10.0}, {"feature": "rollback_count", "contribution": -5.0}]),
        ("orders", "v1.9.0", "CANARY", 0.48, [{"feature": "code_churn", "contribution": 35.0}, {"feature": "files_changed", "contribution": 15.0}]),
        ("payment", "v2.0.0-rc1", "PENDING", 0.78, [{"feature": "service_dependency_count", "contribution": 45.0}, {"feature": "previous_incident_count", "contribution": 30.0}]),
        ("carts", "v1.8.4", "DEPLOYED", 0.15, [{"feature": "developer_experience", "contribution": -12.0}, {"feature": "deployment_time", "contribution": 8.0}]),
    ]
    for s_name, ver, status, score, factors in deployments_data:
        svc = services[s_name]
        dep = await prisma.deployment.find_first(where={"serviceId": svc.id, "version": ver})
        if not dep:
            dep = await prisma.deployment.create(
                data={
                    "serviceId": svc.id,
                    "version": ver,
                    "status": status,
                    "deployedAt": datetime.now(timezone.utc) - timedelta(hours=2),
                }
            )
            await prisma.riskscore.create(
                data={
                    "deploymentId": dep.id,
                    "score": score,
                    "factors": json.dumps(factors),
                }
            )
    print("Configured deployments and live risk scores.")

    # 7. Kubernetes Change Events
    k8s_events = [
        ("DeploymentRollout", "Successfully rolled out frontend v2.4.1 replicas across 3 availability zones", "frontend", "Normal", "sock-shop", 15),
        ("ConfigMapUpdated", "Updated payment-gateway-config timeouts: connect=5s, read=10s", "payment", "Normal", "sock-shop", 45),
        ("NodeScaleUp", "Cluster autoscaler provisioned k8s-worker-node-03 following CPU threshold", "k8s-worker-node-03", "Normal", "kube-system", 90),
        ("HPA_Triggered", "HorizontalPodAutoscaler scaled orders deployment from 2 to 4 pods", "orders", "Normal", "sock-shop", 120),
        ("PodRestart", "Container carts restarted following health check readiness probe timeout", "carts", "Warning", "sock-shop", 180),
        ("OOMKilled", "Container carts-pod-01 exceeded 1.5Gi memory ceiling; terminated and restarted", "carts", "Warning", "sock-shop", 210),
    ]
    for reason, msg, obj, ev_type, ns, mins_ago in k8s_events:
        existing_event = await prisma.k8sevent.find_first(where={"clusterId": cluster.id, "reason": reason, "involvedObject": obj})
        if not existing_event:
            await prisma.k8sevent.create(
                data={
                    "clusterId": cluster.id,
                    "namespace": ns,
                    "involvedObject": obj,
                    "reason": reason,
                    "message": msg,
                    "type": ev_type,
                    "timestamp": datetime.now(timezone.utc) - timedelta(minutes=mins_ago),
                }
            )
    print("Configured Kubernetes change events.")

    # 8. Incidents & Alerts
    incidents_data = [
        ("Cascading Latency in Checkout API", "High end-to-end latency during user checkout transactions", "CRITICAL", "INVESTIGATING", "frontend"),
        ("Carts Redis Memory Saturation", "Memory limit exceeded causing session drops and key eviction", "HIGH", "OPEN", "carts"),
    ]
    created_incidents = {}
    for title, desc, sev, status, s_name in incidents_data:
        svc = services[s_name]
        inc = await prisma.incident.find_first(where={"organizationId": org.id, "title": title})
        if not inc:
            inc = await prisma.incident.create(
                data={
                    "organizationId": org.id,
                    "serviceId": svc.id,
                    "title": title,
                    "description": desc,
                    "severity": sev,
                    "status": status,
                }
            )
        created_incidents[title] = inc

    alerts_data = [
        ("frontend", "High HTTP 500 error rate on /checkout endpoint", "HTTP 500 error rate exceeded 8.5% over a 3-minute sliding window", "CRITICAL", created_incidents["Cascading Latency in Checkout API"].id, 10),
        ("carts", "Redis cart session timeout latency > 1200ms", "Redis session query latency spiked to 1420ms exceeding 200ms SLO", "CRITICAL", created_incidents["Cascading Latency in Checkout API"].id, 12),
        ("payment", "Payment gateway timeout on credit card authorization", "Third-party payment gateway authorization endpoint timed out for 14 requests", "HIGH", created_incidents["Cascading Latency in Checkout API"].id, 14),
        ("orders", "Connection pool exhaustion on order-db", "Postgres connection pool reached 98% saturation with 45 queries in queue", "HIGH", created_incidents["Cascading Latency in Checkout API"].id, 15),
        ("carts", "Pod OOMKilled on carts-pod-01", "Container carts terminated with exit code 137 (OOMKilled)", "HIGH", created_incidents["Carts Redis Memory Saturation"].id, 30),
        ("catalogue", "Catalogue search query p99 latency > 450ms", "Elasticsearch catalogue query p99 latency elevated to 510ms", "MEDIUM", None, 45),
        ("user", "Elevated bcrypt authentication latency", "User login hash verification taking > 350ms per transaction", "MEDIUM", None, 50),
        ("shipping", "Carrier tracking webhook retry queue backpressure", "UPS/FedEx carrier webhook webhook delivery queue length > 500", "WARNING", None, 60),
    ]
    for s_name, title, desc, sev, inc_id, mins_ago in alerts_data:
        svc = services[s_name]
        existing_alert = await prisma.alert.find_first(where={"organizationId": org.id, "title": title})
        if not existing_alert:
            await prisma.alert.create(
                data={
                    "organizationId": org.id,
                    "serviceId": svc.id,
                    "incidentId": inc_id,
                    "title": title,
                    "description": desc,
                    "severity": sev,
                    "status": "OPEN",
                    "firedAt": datetime.now(timezone.utc) - timedelta(minutes=mins_ago),
                }
            )
    print("Configured realistic open alerts.")

    # 9. Situations & Alert Clusters
    situations_data = [
        {
            "title": "Cascading Checkout & Payment Latency Spike",
            "summary": "Correlated alerts across frontend, carts, payment, and orders indicate cascading latency and session timeouts during checkout flow.",
            "severity": "CRITICAL",
            "status": "OPEN",
            "affectedServices": "frontend, carts, payment, orders",
            "clusters": [
                {
                    "title": "Cluster 1: Checkout API Latency",
                    "summary": "Grouped 2 alerts relating to HTTP 500 errors and Redis session timeouts",
                    "representativeAlert": "High HTTP 500 error rate on /checkout endpoint",
                    "affectedServices": "frontend, carts",
                    "severity": "CRITICAL",
                    "confidence": 0.96,
                },
                {
                    "title": "Cluster 2: Downstream Payment & Order Bottleneck",
                    "summary": "Grouped 2 alerts relating to payment timeouts and database connection pools",
                    "representativeAlert": "Payment gateway timeout on credit card authorization",
                    "affectedServices": "payment, orders",
                    "severity": "HIGH",
                    "confidence": 0.92,
                }
            ]
        },
        {
            "title": "Carts Pod Memory Pressure & Restarts",
            "summary": "Repeated OOMKilled events and memory saturation on the carts microservice pods.",
            "severity": "HIGH",
            "status": "OPEN",
            "affectedServices": "carts, k8s-worker-node-02",
            "clusters": [
                {
                    "title": "Cluster 3: Container Memory Ceiling",
                    "summary": "Grouped memory limit termination and container restart alerts",
                    "representativeAlert": "Pod OOMKilled on carts-pod-01",
                    "affectedServices": "carts",
                    "severity": "HIGH",
                    "confidence": 0.89,
                }
            ]
        }
    ]
    for sit_info in situations_data:
        existing_sit = await prisma.situation.find_first(where={"title": sit_info["title"]})
        if not existing_sit:
            sit = await prisma.situation.create(
                data={
                    "title": sit_info["title"],
                    "summary": sit_info["summary"],
                    "severity": sit_info["severity"],
                    "status": sit_info["status"],
                    "affectedServices": sit_info["affectedServices"],
                }
            )
            for c_info in sit_info["clusters"]:
                await prisma.alertcluster.create(
                    data={
                        "situationId": sit.id,
                        "title": c_info["title"],
                        "summary": c_info["summary"],
                        "status": "OPEN",
                        "representativeAlert": c_info["representativeAlert"],
                        "affectedServices": c_info["affectedServices"],
                        "severity": c_info["severity"],
                        "confidence": c_info["confidence"],
                    }
                )
    print("Configured situations and alert clusters.")

    # 10. Policies
    policies_data = [
        (
            "remediation_safety.rego",
            "Guardrails governing automated host remediation and process termination.",
            """package aiops.remediation

default allow = false

# Allow automated termination only for non-protected, high-CPU processes
allow {
    input.action == "TERMINATE_PROCESS"
    not is_protected_process(input.process_name)
    input.cpu_percent >= 20.0
}

is_protected_process(name) {
    protected := ["system", "registry", "smss.exe", "csrss.exe", "services.exe", "lsass.exe", "winlogon.exe"]
    protected[_] == lower(name)
}
"""
        ),
        (
            "canary_blast_radius.rego",
            "Prevents automated canary promotion if ML deployment risk score exceeds 0.40.",
            """package aiops.deployment

default allow_promotion = false

allow_promotion {
    input.risk_score <= 0.40
    input.previous_incidents == 0
}
"""
        ),
        (
            "slo_budget_freeze.rego",
            "Freezes non-emergency production deployments when service error budget drops below 10%.",
            """package aiops.governance

default allow_deploy = true

allow_deploy = false {
    input.error_budget_remaining_percent < 10.0
    input.is_emergency == false
}
"""
        )
    ]
    for p_name, p_desc, p_rules in policies_data:
        existing_p = await prisma.policy.find_first(where={"organizationId": org.id, "name": p_name})
        if not existing_p:
            await prisma.policy.create(
                data={
                    "organizationId": org.id,
                    "name": p_name,
                    "description": p_desc,
                    "rules": p_rules,
                    "isEnabled": True,
                }
            )
    print("Configured Rego policies.")

    # 11. Playbooks
    playbooks_data = [
        (
            "Restart Pod in CrashLoopBackOff",
            "Gracefully deletes a pod experiencing CrashLoopBackOff to trigger a fresh Kubernetes replica spin-up.",
            "Pod CrashLoopBackOff detected for > 3 restarts",
            json.dumps(["Verify pod restart count > 3", "Drain connections gracefully", "Issue kubectl delete pod with grace-period=15"]),
        ),
        (
            "Auto-scale Deployment Replicas",
            "Temporarily scales the target deployment by +2 replicas during unexpected telemetry traffic bursts.",
            "HPA utilization > 90% for 5 minutes",
            json.dumps(["Check node CPU headroom", "Scale deployment replicas by 2", "Monitor p95 latency for 5 minutes"]),
        ),
        (
            "Flush Redis Session Cache",
            "Clears expired session keys from in-memory Redis cluster when memory usage exceeds 85%.",
            "Redis memory usage > 85%",
            json.dumps(["Verify slave replication lag == 0", "Issue redis-cli MEMORY PURGE", "Confirm memory dropped below 70%"]),
        ),
    ]
    for pb_name, pb_desc, pb_pattern, pb_steps in playbooks_data:
        existing_pb = await prisma.playbook.find_first(where={"organizationId": org.id, "name": pb_name})
        if not existing_pb:
            await prisma.playbook.create(
                data={
                    "organizationId": org.id,
                    "name": pb_name,
                    "description": pb_desc,
                    "steps": pb_steps,
                }
            )
    print("Configured remediation playbooks.")

    # 12. Service Level Objectives
    slos_data = [
        ("Host CPU Availability Headroom", "Ensures CPU usage remains bounded below 80% across 24-hour evaluation window", "cpu_usage", 80.0, 99.0, 24),
        ("Host Memory Safe Operating Margin", "Maintains host memory utilization below 85% to prevent OS paging and thrashing", "memory_usage", 85.0, 99.5, 24),
        ("Storage Volume Headroom", "Guarantees primary disk space utilization remains under 90%", "disk_usage", 90.0, 99.9, 168),
    ]
    for slo_name, slo_desc, slo_metric, slo_thresh, slo_target, slo_win in slos_data:
        existing_slo = await prisma.servicelevelobjective.find_first(where={"name": slo_name})
        if not existing_slo:
            await prisma.servicelevelobjective.create(
                data={
                    "name": slo_name,
                    "description": slo_desc,
                    "metric": slo_metric,
                    "threshold": slo_thresh,
                    "targetPercent": slo_target,
                    "windowHours": slo_win,
                }
            )
    print("Configured Service Level Objectives.")

    await prisma.disconnect()
    print("Seeding complete! Database is 100% populated.")

if __name__ == "__main__":
    asyncio.run(seed())
