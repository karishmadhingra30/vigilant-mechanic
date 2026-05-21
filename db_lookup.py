import json
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
MOCK_DB_PATH = BASE_DIR / "mock_db.json"
SERVICE_CODES_PATH = BASE_DIR / "service_codes.json"


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _load_mock_db() -> dict:
    return _load_json(MOCK_DB_PATH)


def get_customer_by_phone(phone: str) -> dict | None:
    normalized_phone = phone.strip()
    for customer in _load_mock_db()["customers"]:
        if customer["phone"] == normalized_phone:
            return customer
    return None


def get_vehicles_for_customer(customer_id: str) -> list[dict]:
    return [
        vehicle
        for vehicle in _load_mock_db()["vehicles"]
        if vehicle["customer_id"] == customer_id
    ]


def get_service_history(vehicle_id: str) -> list[dict]:
    records = [
        record
        for record in _load_mock_db()["service_history"]
        if record["vehicle_id"] == vehicle_id
    ]
    return sorted(records, key=lambda record: record["date"], reverse=True)


def lookup_service_code(code: str) -> dict | None:
    return list_all_service_codes().get(code)


def list_all_service_codes() -> dict:
    return _load_json(SERVICE_CODES_PATH)


if __name__ == "__main__":
    sample_customer = get_customer_by_phone("555-0142")
    print(sample_customer)
    if sample_customer:
        sample_vehicles = get_vehicles_for_customer(sample_customer["customer_id"])
        print(sample_vehicles)
        if sample_vehicles:
            print(get_service_history(sample_vehicles[0]["vehicle_id"])[:2])
    print(lookup_service_code("BRK-001"))
