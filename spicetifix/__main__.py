from spicetifix.api import run_api_server


def main() -> None:
    run_api_server(port=8765)


if __name__ == "__main__":
    main()
