import json

from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from .simulation_service import service


def index(request):
    return render(request, "simulator.html")


def _json_body(request):
    if not request.body:
        return {}
    try:
        return json.loads(request.body.decode("utf-8"))
    except Exception:
        return None


@csrf_exempt
def api_start(request):
    if request.method != "POST":
        return HttpResponseBadRequest("POST only")
    body = _json_body(request)
    if body is None:
        return JsonResponse({"error": "invalid json"}, status=400)
    duration = body.get("duration", 600)
    ok, payload = service.start(duration_seconds=duration)
    return JsonResponse(payload, status=200 if ok else 400)


@csrf_exempt
def api_stop(request):
    if request.method != "POST":
        return HttpResponseBadRequest("POST only")
    _, payload = service.stop()
    return JsonResponse(payload)


def api_data(request):
    return JsonResponse(service.snapshot(), json_dumps_params={"ensure_ascii": False})


def api_stats(request):
    snap = service.snapshot()
    return JsonResponse(
        {"status": snap.get("status"), "stats": snap.get("stats"), "timestamp": snap.get("timestamp", "")},
        json_dumps_params={"ensure_ascii": False},
    )


def api_items(request):
    snap = service.snapshot()
    items = snap.get("items") or []
    return JsonResponse(
        {"count": len(items), "items": items[:20]},
        json_dumps_params={"ensure_ascii": False},
    )


def api_robots(request):
    snap = service.snapshot()
    robots = snap.get("robots") or []
    return JsonResponse(
        {"count": len(robots), "robots": robots},
        json_dumps_params={"ensure_ascii": False},
    )


def api_bins(request):
    snap = service.snapshot()
    bins = snap.get("bins") or []
    return JsonResponse(
        {"count": len(bins), "bins": bins},
        json_dumps_params={"ensure_ascii": False},
    )


def api_history(request):
    """动力学历史数据（关节角、末端轨迹、扭矩）"""
    return JsonResponse(service.get_history(), json_dumps_params={"ensure_ascii": False})


def api_time(request):
    snap = service.snapshot()
    return JsonResponse(
        snap.get("time_data") or {"simulation_time": 0.0, "fps": 0.0, "frames": 0},
        json_dumps_params={"ensure_ascii": False},
    )

