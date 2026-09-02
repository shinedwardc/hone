# inventory/main.py

import sys
from pkg.pricing import Pricer
from pkg.render import format_json_output


def main() -> None:
    pricer = Pricer()
    if len(sys.argv) <= 1:
        print("Inventory Pricing App")
        print('Usage: python main.py "<item>:<quantity>[,<item>:<quantity>...]"')
        print('Example: python main.py "widget:10"')
        return

    order = " ".join(sys.argv[1:])
    try:
        invoice = pricer.price_order(order)
        if invoice is not None:
            to_print = format_json_output(order, invoice)
            print(to_print)
        else:
            print("Error: Order is empty or contains only whitespace.")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
