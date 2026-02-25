from src.main import create_app


def main():
    app = create_app()
    client = app.test_client()

    def check(path: str) -> None:
        resp = client.get(path)
        print(f"{path} -> {resp.status_code} {resp.get_json()}")

    check("/api/health")
    check("/api/epub/status/unknown")


if __name__ == "__main__":
    main()
