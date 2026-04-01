import json
from django.shortcuts import render
from django.db.models import Sum, Max
from .models import HourlyAggregation, DailyAggregation


def _get_device_data(location, date):
    hourly = list(
        HourlyAggregation.objects.filter(location=location, date=date)
        .order_by("hour")
        .values("hour", "total_in", "total_out", "net_flow", "occupancy")
    )
    for row in hourly:
        row["hour_display"] = row["hour"].strftime("%H:%M")

    agg = (
        HourlyAggregation.objects.filter(location=location, date=date)
        .aggregate(
            total_in=Sum("total_in"),
            total_out=Sum("total_out"),
        )
    )
    summary = {k: v or 0 for k, v in agg.items()}

    return {"hourly": hourly, "summary": summary}


def dashboard(request):
    dates = list(
        HourlyAggregation.objects.values_list("date", flat=True).distinct().order_by("date")
    )
    selected_date = request.GET.get("date", str(dates[0]) if dates else None)

    device_a = _get_device_data("device_A", selected_date)
    device_b = _get_device_data("device_B", selected_date)

    return render(request, "api/dashboard.html", {
        "dates": [str(d) for d in dates],
        "selected_date": selected_date,
        "device_a": device_a,
        "device_b": device_b,
        "device_a_json": json.dumps(device_a["summary"]),
        "device_b_json": json.dumps(device_b["summary"]),
    })
