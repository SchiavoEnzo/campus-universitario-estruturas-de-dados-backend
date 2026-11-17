import json
import os
from copy import deepcopy
from functools import lru_cache
from pathlib import Path

from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError

from .campus_navigation import CampusMap


@lru_cache(maxsize=1)
def mongo_client(uri):
    # Pool pequeno por processo: cada instância serverless mantém o próprio pool.
    return MongoClient(uri, maxPoolSize=5, timeoutMS=7000)


def initial_graph(dataset):
    if dataset == "frontend":
        seed = json.loads((Path(__file__).resolve().parents[1] / "data/frontend.json").read_text())
        nodes, edges = seed["nodes"], seed["edges"]
    elif dataset == "original":
        original = CampusMap()
        coords = {"1": (220, 140), "2": (370, 130), "3": (520, 140), "4": (665, 150)}
        nodes = [
            dict(id=str(code), name=name, category="Acadêmico", x=coords[str(code)][0], y=coords[str(code)][1])
            for code, name in original.points().items()
        ]
        edges = [
            {"id": f"{a}-{b}", "from": str(a), "to": str(b), "distance": meters,
             "time": None, "accessible": None, "blocked": False}
            for a, neighbors in original.connections().items() for b, meters in neighbors
        ]
    else:
        raise RuntimeError("Dataset inválido.")
    return {"revision": 1, "nodes": nodes, "edges": edges}


class MongoGraph:
    def __init__(self):
        uri = os.getenv("MONGODB_URI")
        if not uri:
            raise RuntimeError("MONGODB_URI não configurada.")
        self.collection = mongo_client(uri)[os.getenv("MONGODB_DB") or "campus_viva"]["graphs"]
        self.key = os.getenv("CAMPUS_DATASET") or "original"
        if self.key not in {"original", "frontend"}:
            raise RuntimeError("Dataset inválido.")

    def read(self):
        doc = self.collection.find_one({"_id": self.key}, {"_id": 0})
        if doc is not None:
            return doc
        seed = initial_graph(self.key)
        try:
            self.collection.insert_one({"_id": self.key, **deepcopy(seed)})
            return seed
        except DuplicateKeyError:
            return self.collection.find_one({"_id": self.key}, {"_id": 0})

    def write(self, graph, revision):
        return self.collection.replace_one(
            {"_id": self.key, "revision": revision}, {"_id": self.key, **graph}
        ).matched_count == 1


class LocalGraph:
    """Modo de demonstração: uma instância e dados em memória por processo."""
    def __init__(self, dataset):
        from threading import Lock
        self.lock = Lock()
        self.graph = initial_graph(dataset)

    def read(self):
        with self.lock:
            return deepcopy(self.graph)

    def write(self, graph, revision):
        with self.lock:
            if self.graph["revision"] != revision:
                return False
            self.graph = deepcopy(graph)
            return True


@lru_cache(maxsize=2)
def local_graph(dataset):
    return LocalGraph(dataset)
