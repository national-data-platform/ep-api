# api\services\status_services\full_metrics.py
from .check_api_status import get_status
from .system_metrics import get_public_ip, get_system_metrics


def get_full_metrics():
    """
    Retrieve full system metrics including public IP, CPU, memory, disk,
    and the current status of all integrated services.
    """
    public_ip = get_public_ip()
    cpu, mem_used, mem_total, disk_used, disk_total = get_system_metrics()

    services_status = get_status()

    metrics = {
        "public_ip": public_ip,
        "cpu": f"{cpu:.1f}%",
        "memory": f"{mem_used:.1f}GB/{mem_total:.1f}GB",
        "disk": f"{disk_used:.1f}GB/{disk_total:.1f}GB",
        "services": services_status,
    }

    return metrics
