import os
import unittest
from copy import deepcopy
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import app
from campus.controllers import repository
from campus.repository import initial_graph


class MemoryGraph:
    def __init__(self, dataset="original"):
        self.graph = initial_graph(dataset)
        self.conflict = False

    def read(self):
        return deepcopy(self.graph)

    def write(self, graph, revision):
        if self.conflict or revision != self.graph["revision"]:
            return False
        self.graph = deepcopy(graph)
        return True


class TestAPI(unittest.TestCase):
    def setUp(self):
        self.repo = MemoryGraph()
        app.dependency_overrides[repository] = lambda: self.repo
        self.client = TestClient(app)
        token = "x" * 32
        self.env = patch.dict(os.environ, {"ADMIN_TOKEN": token})
        self.env.start()
        self.headers = {"Authorization": f"Bearer {token}"}

    def tearDown(self):
        self.env.stop()
        self.client.close()
        app.dependency_overrides.clear()

    def route(self, origin, destination, **extra):
        return self.client.post("/api/routes", json=dict(origin=origin, destination=destination, **extra))

    def test_original_distance_and_one_way(self):
        response = self.route("1", "3")
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual([p["id"] for p in result["path"]], ["1", "2", "3"])
        self.assertEqual(result["distance"], 250)
        self.assertFalse(self.route("1", "4").json()["found"])
        self.assertEqual(self.route("1", "1").json()["cost"], 0)
        self.assertEqual(self.route("999", "1").status_code, 404)

    def test_graph_edits_affect_routing_and_cascade(self):
        target = "/api/connections/1/3"
        self.assertEqual(self.client.put(target, json={"distance": 70}).status_code, 401)
        self.assertEqual(self.client.put(target, json={"distance": -1}, headers=self.headers).status_code, 422)
        self.assertEqual(self.client.put(target, json={"distance": 70}, headers=self.headers).status_code, 200)
        self.assertEqual(self.route("1", "3").json()["distance"], 70)
        self.assertEqual(self.client.delete("/api/points/3", headers=self.headers).status_code, 204)
        self.assertFalse(any("3" in (e["from"], e["to"]) for e in self.client.get("/api/graph").json()["edges"]))

    def test_frontend_uses_requested_weights_and_filters(self):
        self.repo = MemoryGraph("frontend")
        self.assertEqual(len(self.client.get("/api/graph").json()["nodes"]), 24)
        self.assertEqual(self.route("BLK-A", "LAB-INF", criterion="time").json()["cost"], 5)
        response = self.client.put("/api/connections/BIB/LAB-INF",
                                   json={"distance": 100, "time": 2, "accessible": True, "blocked": True},
                                   headers=self.headers)
        self.assertEqual(response.status_code, 200)
        route = self.route("BLK-A", "LAB-INF", criterion="time", accessible=True).json()
        self.assertTrue(route["found"])
        self.assertTrue(all(s["accessible"] and not s["blocked"] for s in route["segments"]))
        self.assertGreater(route["cost"], 5)

    def test_conflicting_edit_is_not_saved(self):
        self.repo.conflict = True
        response = self.client.post("/api/points", json={"name": "Novo ponto"}, headers=self.headers)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.repo.read()["revision"], 1)


if __name__ == "__main__":
    unittest.main()
