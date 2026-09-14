from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from ..config import settings

_client: MongoClient | None = None

DB_NAME = "gov_scheme_ai"
COLLECTION_NAME = "schemes"


def get_client() -> MongoClient:
    global _client
    if _client is None:
        _client = MongoClient(settings.mongodb_uri)
    return _client


def get_db() -> Database:
    return get_client()[DB_NAME]


def get_schemes_collection() -> Collection:
    return get_db()[COLLECTION_NAME]
