import asyncio
import random
import uuid
from datetime import datetime, timedelta
from app.core.db import prisma


async def seed_data():
    print("Connecting to database...")
    try:
        await prisma.connect()
    except Exception as e:
        print(
            f"Warning: Could not connect to database. Is PostgreSQL running? Error: {e}"
        )
        return

    print("Clearing old data...")
    # Clean up old data to prevent conflicts
    await prisma.pod.delete_many()
    await prisma.node.delete_many()
    await prisma.namespace.delete_many()
    await prisma.k8sevent.delete_many()
    await prisma.log.delete_many()
    await prisma.metric.delete_many()
    await prisma.trace.delete_many()
    await prisma.alert.delete_many()
    await prisma.incident.delete_many()
    await prisma.service.delete_many()
    await prisma.cluster.delete_many()
    await prisma.organization.delete_many()

    print("Creating Organization & Cluster...")
    org = await prisma.organization.create(data={"name": "Sentinel Enterprise Corp"})

    cluster = await prisma.cluster.create(
        data={
            "organizationId": org.id,
            "name": "us-east-1-prod-cluster",
            "region": "us-east-1",
            "provider": "AWS",
        }
    )

    print("Creating K8s Topology (Namespaces, Nodes)...")
    ns_default = await prisma.namespace.create(
        data={"clusterId": cluster.id, "name": "default"}
    )
    await prisma.namespace.create(
        data={"clusterId": cluster.id, "name": "kube-system"}
    )

    nodes = []
    for i in range(3):
        nodes.append(
            await prisma.node.create(
                data={
                    "clusterId": cluster.id,
                    "name": f"ip-10-0-1-{10+i}.ec2.internal",
                    "status": "Ready",
                    "cpuCores": 8,
                    "memoryBytes": 32 * 1024 * 1024 * 1024,
                }
            )
        )

    print("Creating Services and Pods...")
    service_names = [
        "checkout-service",
        "auth-api",
        "inventory-db",
        "payment-gateway",
        "frontend-ui",
    ]
    services = []
    pods = []

    for s_name in service_names:
        svc = await prisma.service.create(
            data={
                "organizationId": org.id,
                "clusterId": cluster.id,
                "name": s_name,
                "description": f"Core {s_name} microservice",
            }
        )
        services.append(svc)

        # Create 3 pods per service
        for i in range(3):
            pod = await prisma.pod.create(
                data={
                    "namespaceId": ns_default.id,
                    "nodeId": random.choice(nodes).id,
                    "serviceId": svc.id,
                    "name": f"{s_name}-{uuid.uuid4().hex[:8]}",
                    "status": (
                        "Running" if random.random() > 0.1 else "CrashLoopBackOff"
                    ),
                    "restarts": random.randint(0, 15),
                }
            )
            pods.append(pod)

    print("Generating Telemetry (Metrics, Logs, Traces)...")
    now = datetime.utcnow()

    for svc in services:
        # Generate CPU & Memory metrics for the last 60 minutes
        for minute in range(60):
            timestamp = now - timedelta(minutes=minute)

            # Simulate CPU spike for checkout-service
            cpu_val = random.uniform(10.0, 40.0)
            if svc.name == "checkout-service" and minute < 10:
                cpu_val = random.uniform(85.0, 99.0)  # Spike

            await prisma.metric.create(
                data={
                    "serviceId": svc.id,
                    "name": "cpu_usage_percent",
                    "value": cpu_val,
                    "timestamp": timestamp,
                    "tags": '{"env": "prod"}',
                }
            )

            await prisma.log.create(
                data={
                    "serviceId": svc.id,
                    "level": "ERROR" if cpu_val > 90 else "INFO",
                    "message": f"Processing request in {svc.name} - CPU {cpu_val:.1f}%",
                    "timestamp": timestamp,
                }
            )

    print("Generating Incidents & Alerts...")
    checkout_svc = next(s for s in services if s.name == "checkout-service")

    incident = await prisma.incident.create(
        data={
            "organizationId": org.id,
            "serviceId": checkout_svc.id,
            "title": "Cascading Latency in Checkout API",
            "description": "Checkout API is experiencing severe latency due to CPU saturation",
            "severity": "CRITICAL",
            "status": "INVESTIGATING",
        }
    )

    await prisma.alert.create(
        data={
            "organizationId": org.id,
            "serviceId": checkout_svc.id,
            "incidentId": incident.id,
            "title": "CPU Saturation Detected",
            "description": "CPU > 95% for 5 minutes",
            "severity": "CRITICAL",
            "status": "OPEN",
        }
    )

    print("Seeding Complete!")
    await prisma.disconnect()


if __name__ == "__main__":
    asyncio.run(seed_data())
