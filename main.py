import sys
from automatify.api import run_api_server


def start():
    run_api_server(port=8765)


if __name__ == "__main__":
    start()
