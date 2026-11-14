"""Mock vehicle registry.

In production this would decode a VIN and call a valuation service; the
function signatures would stay the same.
"""

VEHICLE_CATALOG = {
    # Compact and mid-size cars
    "civic":     {"make": "Honda",     "model": "Civic",          "fuel": "Gasoline", "vehicle_class": "car",    "msrp": 30_000},
    "corolla":   {"make": "Toyota",    "model": "Corolla",        "fuel": "Gasoline", "vehicle_class": "car",    "msrp": 25_000},
    "elantra":   {"make": "Hyundai",   "model": "Elantra",        "fuel": "Gasoline", "vehicle_class": "car",    "msrp": 24_000},
    "camry":     {"make": "Toyota",    "model": "Camry",          "fuel": "Hybrid",   "vehicle_class": "car",    "msrp": 36_000},
    # SUVs and crossovers
    "rav4":      {"make": "Toyota",    "model": "RAV4",           "fuel": "Hybrid",   "vehicle_class": "suv",    "msrp": 40_000},
    "crv":       {"make": "Honda",     "model": "CR-V",           "fuel": "Gasoline", "vehicle_class": "suv",    "msrp": 38_000},
    "tucson":    {"make": "Hyundai",   "model": "Tucson",         "fuel": "Gasoline", "vehicle_class": "suv",    "msrp": 33_000},
    "seltos":    {"make": "Kia",       "model": "Seltos",         "fuel": "Gasoline", "vehicle_class": "suv",    "msrp": 28_000},
    "cx5":       {"make": "Mazda",     "model": "CX-5",           "fuel": "Gasoline", "vehicle_class": "suv",    "msrp": 35_000},
    "rogue":     {"make": "Nissan",    "model": "Rogue",          "fuel": "Gasoline", "vehicle_class": "suv",    "msrp": 34_000},
    "forester":  {"make": "Subaru",    "model": "Forester",       "fuel": "Gasoline", "vehicle_class": "suv",    "msrp": 37_000},
    "modely":    {"make": "Tesla",     "model": "Model Y",        "fuel": "Electric", "vehicle_class": "suv",    "msrp": 60_000},
    # Pickups
    "f150":      {"make": "Ford",      "model": "F-150",          "fuel": "Gasoline", "vehicle_class": "pickup", "msrp": 50_000},
    "ram1500":   {"make": "Ram",       "model": "Ram 1500",       "fuel": "Gasoline", "vehicle_class": "pickup", "msrp": 55_000},
    "silverado": {"make": "Chevrolet", "model": "Silverado 1500", "fuel": "Gasoline", "vehicle_class": "pickup", "msrp": 52_000},
}


def lookup_vehicle(query: str) -> dict | None:
    """Fuzzy lookup by model name ("civic", "CIVIC", "Honda Civic", "cr-v")."""
    q = query.lower().strip()
    if not q:
        return None
    if q in VEHICLE_CATALOG:
        return VEHICLE_CATALOG[q]
    for key, vehicle in VEHICLE_CATALOG.items():
        model = vehicle["model"].lower()
        if q in key or q in model or model in q:
            return vehicle
    return None


def supported_models() -> list[str]:
    return sorted({f"{v['make']} {v['model']}" for v in VEHICLE_CATALOG.values()})
