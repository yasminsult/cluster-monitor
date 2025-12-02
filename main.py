from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from kubernetes import client, config
from datetime import datetime

# Load in-cluster Kubernetes config
config.load_incluster_config()
core = client.CoreV1Api()

app = FastAPI()
templates = Jinja2Templates(directory="templates")

def get_pod_data():
    pods = core.list_pod_for_all_namespaces(watch=False).items
    pod_list = []
    pod_status_summary = {"Running": 0, "Pending": 0, "Failed": 0, "Unknown": 0}
    top_restarting = []
    for pod in pods:
        status = pod.status.phase
        pod_status_summary[status] = pod_status_summary.get(status, 0) + 1
        restarts = sum([c.restart_count for c in pod.status.container_statuses]) if pod.status.container_statuses else 0
        pod_list.append({
            "name": pod.metadata.name,
            "namespace": pod.metadata.namespace,
            "status": status,
            "node": pod.spec.node_name,
            "restarts": restarts
        })
    top_restarting = sorted(pod_list, key=lambda x: x["restarts"], reverse=True)[:5]
    return pod_list, pod_status_summary, top_restarting

def get_services_data():
    svcs = core.list_service_for_all_namespaces(watch=False).items
    svc_list = []
    svc_type_counts = {}
    for svc in svcs:
        name = svc.metadata.name
        ns = svc.metadata.namespace
        svc_type = svc.spec.type
        cluster_ip = svc.spec.cluster_ip
        ports = [p.port for p in svc.spec.ports]
        svc_list.append({
            "name": name,
            "namespace": ns,
            "type": svc_type,
            "cluster_ip": cluster_ip,
            "ports": ports
        })
        svc_type_counts[svc_type] = svc_type_counts.get(svc_type, 0) + 1
    return svc_list, svc_type_counts

def get_node_readiness():
    nodes = core.list_node().items
    ready = 0
    not_ready = 0
    for node in nodes:
        for condition in node.status.conditions:
            if condition.type == "Ready":
                if condition.status == "True":
                    ready += 1
                else:
                    not_ready += 1
    return {"ready": ready, "not_ready": not_ready}

@app.get("/")
def dashboard(request: Request):
    pods, pod_status_summary, top_restarting = get_pod_data()
    services, svc_type_counts = get_services_data()
    node_readiness = get_node_readiness()
    
    # Calculate metrics for dashboard
    total_pods = len(pods)
    total_services = len(services)
    total_nodes = node_readiness["ready"] + node_readiness["not_ready"]
    health_score = int((pod_status_summary.get("Running", 0) / total_pods * 100)) if total_pods > 0 else 0
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "pods": pods,
        "pod_status": pod_status_summary,
        "services": services,
        "svc_counts": svc_type_counts,
        "node_readiness": node_readiness,
        "top_restarting": top_restarting,
        "total_pods": total_pods,
        "total_services": total_services,
        "total_nodes": total_nodes,
        "health_score": health_score
    })

@app.get("/api/health")
def health_check():
    """Health check endpoint"""
    try:
        core.list_namespace(limit=1)
        return {"status": "healthy"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

@app.get("/api/metrics")
def get_metrics():
    """Metrics endpoint"""
    try:
        pods, pod_status, _ = get_pod_data()
        services, svc_counts = get_services_data()
        node_readiness = get_node_readiness()
        return {
            "pods": {"total": len(pods), "status": pod_status},
            "services": {"total": len(services), "types": svc_counts},
            "nodes": node_readiness
        }
    except Exception as e:
        return {"error": str(e)}
