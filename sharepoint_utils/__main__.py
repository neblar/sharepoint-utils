from argparse import ArgumentParser
from .flatten import Flatten
from pathlib import Path


if __name__ == "__main__":
    argparse = ArgumentParser("Sharepoint Utils")
    argparse.add_argument("--output_dir", type=str, default="/home/workspace/output")
    parsers = argparse.add_subparsers(help="commands", dest="command")
    flatten = parsers.add_parser("flatten")
    flatten.add_argument("start_url", type=str, help="the starting url of the sharepoint exploration")
    flatten.add_argument("fed_auth", type=str, help="the FedAuth cookie obtained by visiting the website")
    flatten.add_argument("--debug", action='store_true', help="saves an image of the last visited page")
    flatten.add_argument("--debug-image-key", type=str, default="debug.png")
    flatten.add_argument("--output-json-key", type=str, default="flatten.json")
    flatten.add_argument("--max-depth", type=int, default=None, help="Maximum depth in exploring folders recursively, ignoring this setting leads to complete traversal")
    flatten.add_argument("--wait-timeout", type=int, default=10, help="Timeout for waiting on page elements to load in seconds")
    flatten.add_argument("--height-based-scroll-time", type=float, default=2, help="Wait time (in seconds) between scrolling dynamic scroll pages with unknown number of items")
    flatten.add_argument("--item-based-scroll-time", type=float, default=0.1, help="Wait time (in seconds) between scrolling dynamic scroll pages with known number of items")
    flatten.add_argument("--scroll-delta", type=float, default=150, help="Number of pixels to scroll by for dynamic scroll pages, lower numbers makes the process slow, and too large number may result in skipping items and breaking the system")
    args = argparse.parse_args()
    output_dir = args.output_dir

    if args.command == "flatten":
        debug_path = f"{output_dir}/{args.debug_image_key}"
        output_path = f"{output_dir}/{args.output_json_key}"
        Flatten(
            start_url=args.start_url,
            fed_auth=args.fed_auth,
            debug=args.debug,
            debug_path=debug_path,
            output_path=output_path,
            wait_timeout=args.wait_timeout,
            max_depth=args.max_depth,
            height_based_scroll_time=args.height_based_scroll_time,
            item_based_scroll_time=args.item_based_scroll_time,
            scroll_delta=args.scroll_delta,
        ).run()