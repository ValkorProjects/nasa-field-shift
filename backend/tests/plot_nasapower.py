import os
import sys
from datetime import datetime
import matplotlib.pyplot as plt

# `backend` is the import root (same as run.py)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from datasets.clients.nasapower.nasapower_client import get_dailyPlot, Parameters
from datasets.clients.nasapower.nasapower_typedef import NO_DATA

MAX_PARAMS_PER_REQUEST = 5  # the plot endpoint rejects more than 5 parameters per call

parameter_names = [v for k, v in vars(Parameters).items() if not k.startswith("_")]

data = None
parameters = {}
for i in range(0, len(parameter_names), MAX_PARAMS_PER_REQUEST):
    batch = parameter_names[i:i + MAX_PARAMS_PER_REQUEST]
    result = get_dailyPlot(",".join(batch), longitude=-104.99, latitude=39.74)
    if result is None:
        continue
    data = data or result
    parameters.update(result.Properties.Parameter)

try:
    if data is None:
        raise RuntimeError("No data returned from NASA POWER")

    if not parameters:
        raise RuntimeError("Response contains no parameters")

    where = f"lon {data.Geometry.Longitude}, lat {data.Geometry.Latitude}"
    empty = [name for name, p in parameters.items() if not p.has_data()]
    if len(empty) == len(parameters):
        raise RuntimeError(
            f"NASA POWER returned no data (all values are {NO_DATA}) for {where}. "
            "The location may be outside the projection dataset's coverage, or the "
            "dates may have no data. Try a different location or date range."
        )
    if empty:
        print(f"Warning: no data for {', '.join(empty)} at {where}; skipping them.")
        parameters = {name: p for name, p in parameters.items() if name not in empty}

    n = len(parameters)
    fig, axes = plt.subplots(n, 1, figsize=(12, 3 * n), sharex=True, squeeze=False)

    for ax, (name, param) in zip(axes[:, 0], parameters.items()):
        plotted = False
        for scenario_name, scenario in param.Scenarios.items():
            # Sorted (date, value) pairs, skipping the -999 "no data" entries
            points = sorted(
                (datetime.strptime(date, "%Y%m%d"), value)
                for date, value in scenario.Values.items()
                if value != NO_DATA
            )
            if not points:
                continue
            x, y = zip(*points)
            ax.plot(x, y, label=scenario_name)
            plotted = True

        ax.set_title(name)
        ax.set_ylabel(name)
        ax.grid(True, alpha=0.3)
        if plotted:
            ax.legend(loc="upper right")
        else:
            ax.text(0.5, 0.5, "no valid data", ha="center", va="center", transform=ax.transAxes)

    axes[-1, 0].set_xlabel("Date")
    fig.suptitle(
        f"NASA POWER daily projection - lon {data.Geometry.Longitude}, lat {data.Geometry.Latitude}"
    )
    fig.autofmt_xdate()
    fig.tight_layout(rect=(0, 0, 1, 0.98))
    plt.show()

except Exception as e:
    print(f"Ocorreu um erro {e}")
