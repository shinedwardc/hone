# inventory/pkg/render.py

import json
from dataclasses import asdict

from pkg.pricing import Line


def format_json_output(order: str, invoice: dict, indent: int = 2) -> str:
    lines: list[Line] = invoice["lines"]

    output_data = {
        "order": order,
        "lines": [asdict(line) for line in lines],
        "subtotal": invoice["subtotal"],
        "tax": invoice["tax"],
        "total": invoice["total"],
    }
    return json.dumps(output_data, indent=indent)
