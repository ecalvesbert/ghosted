from app.brokers.spokeo import SpokeoAdapter

BROKER_REGISTRY: dict[str, "BrokerAdapter"] = {
    "spokeo": SpokeoAdapter(),
}
