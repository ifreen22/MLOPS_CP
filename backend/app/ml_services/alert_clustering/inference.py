import asyncio
from prisma import Prisma
from app.ml_services.alert_clustering.service import alert_clustering_service

async def run_clustering_on_db():
    if not alert_clustering_service.is_loaded:
        alert_clustering_service.load_model()
    if not alert_clustering_service.is_loaded:
        raise RuntimeError("Alert clustering model is not loaded.")
        
    db = Prisma()
    await db.connect()
    try:
        alerts = await db.alert.find_many(where={"status": "OPEN"})
        if not alerts:
            return {"alerts": 0, "situations_created": 0}

        log_texts = [f"[{alert.severity}] {alert.title} {alert.description or ''}" for alert in alerts]
        predictions = alert_clustering_service.batch_predict(log_texts)
        clusters = {}
        for alert, prediction in zip(alerts, predictions):
            clusters.setdefault(prediction["cluster_id"], []).append((alert, prediction["confidence"]))

        created = 0
        for cluster_id, items in clusters.items():
            if cluster_id == -1:
                continue

            representative_alert = items[0][0].title
            existing = await db.alertcluster.find_first(
                where={"representativeAlert": representative_alert, "status": "OPEN"}
            )
            if existing:
                continue

            severity = "HIGH" if any(str(item[0].severity).upper() in {"CRITICAL", "SEV1"} for item in items) else "MEDIUM"
            affected_services = len({item[0].serviceId for item in items})
            situation = await db.situation.create(
                data={
                    "title": f"Situation (Cluster {cluster_id}): {representative_alert}",
                    "summary": f"Automatically grouped {len(items)} open alerts.",
                    "severity": severity,
                    "status": "OPEN",
                    "affectedServices": str(affected_services),
                }
            )
            await db.alertcluster.create(
                data={
                    "situationId": situation.id,
                    "title": f"Cluster {cluster_id}",
                    "summary": f"Contains {len(items)} alerts",
                    "status": "OPEN",
                    "representativeAlert": representative_alert,
                    "affectedServices": str(affected_services),
                    "severity": severity,
                    "confidence": items[0][1],
                }
            )
            created += 1

        return {"alerts": len(alerts), "situations_created": created}
    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(run_clustering_on_db())
