"""Time, date and host resource usage."""

from __future__ import annotations

import platform
from datetime import datetime

from app.tools.base import BaseTool, NoParams


class SystemInfoTool(BaseTool):
    name = "system_info"
    description = "Get the current date and time, the operating system, and resource usage."
    params_model = NoParams

    def execute(self, params: NoParams) -> str:
        info: dict[str, str] = {
            "time": datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z"),
            "os": f"{platform.system()} {platform.release()}",
            "machine": platform.machine(),
            "python": platform.python_version(),
        }
        try:
            import psutil

            memory = psutil.virtual_memory()
            info["cpu"] = f"{psutil.cpu_percent(interval=0.2)}% in use"
            info["memory"] = (
                f"{memory.percent}% of {round(memory.total / 1e9, 1)} GB in use"
            )
        except ImportError:
            pass

        return "\n".join(f"{k}: {v}" for k, v in info.items())
