from app.brokers.base import BrokerAdapter
from app.brokers.spokeo import SpokeoAdapter
from app.brokers.whitepages import WhitepagesAdapter

BROKER_REGISTRY: dict[str, BrokerAdapter] = {
    "spokeo": SpokeoAdapter(),
    "whitepages": WhitepagesAdapter(),
}
