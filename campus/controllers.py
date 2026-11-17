import os
from secrets import compare_digest
from typing import Annotated, Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from .campus_navigation import CampusMap
from .repository import MongoGraph, local_graph


router = APIRouter(prefix="/api")
bearer = HTTPBearer(auto_error=False)
PointId = Annotated[str, StringConstraints(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
Weight = Annotated[float, Field(ge=0, le=10_000_000, allow_inf_nan=False)]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Point(Input):
    name: Name
    category: Name = "Serviços"
    x: float = Field(default=415, ge=0, le=830)
    y: float = Field(default=280, ge=0, le=560)


class Connection(Input):
    distance: Weight
    time: Weight | None = None
    accessible: bool | None = None
    blocked: bool = False


class Route(Input):
    origin: PointId
    destination: PointId
    criterion: Literal["distance", "time"] = "distance"
    accessible: bool = False


def repository():
    if os.getenv("CAMPUS_STORAGE") == "memory" and not os.getenv("VERCEL"):
        return local_graph(os.getenv("CAMPUS_DATASET") or "original")
    return MongoGraph()


def require_admin(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
    expected = os.getenv("ADMIN_TOKEN") or ""
    if len(expected) < 32:
        raise HTTPException(503, "Edição administrativa não configurada.")
    if not credentials or not compare_digest(credentials.credentials.encode(), expected.encode()):
        raise HTTPException(401, "Credencial administrativa inválida.", headers={"WWW-Authenticate": "Bearer"})


def point_exists(graph, point_id):
    if not any(n["id"] == point_id for n in graph["nodes"]):
        raise HTTPException(404, f"Ponto não cadastrado: {point_id}.")


def save(repo, graph):
    revision = graph["revision"]
    graph["revision"] += 1
    if not repo.write(graph, revision):
        raise HTTPException(409, "O mapa mudou durante a edição. Consulte a versão atual e tente novamente.")


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/graph")
def graph(repo=Depends(repository)):
    return repo.read()


@router.post("/routes")
def calculate(payload: Route, repo=Depends(repository)):
    graph = repo.read()
    point_exists(graph, payload.origin)
    point_exists(graph, payload.destination)

    # Adapta os IDs da API aos códigos inteiros da classe original, sem reescrever Dijkstra.
    campus = CampusMap()
    for code in campus.points():
        campus.remove_point(code)
    codes = {n["id"]: campus.add_point(n["name"]) for n in graph["nodes"]}
    ids = {code: point_id for point_id, code in codes.items()}
    usable_edges = {}
    for edge in graph["edges"]:
        weight = edge.get(payload.criterion)
        if edge.get("blocked") or weight is None or (payload.accessible and edge.get("accessible") is not True):
            continue
        a, b = edge["from"], edge["to"]
        campus.set_connection(codes[a], codes[b], weight)
        usable_edges[(a, b)] = edge

    path, cost = campus.dijkstra(codes[payload.origin], codes[payload.destination])
    point_ids = [ids[code] for code in path]
    points = {node["id"]: node for node in graph["nodes"]}
    segments = [usable_edges[(a, b)] for a, b in zip(point_ids, point_ids[1:])]
    if not path:
        return {"found": False, "criterion": payload.criterion, "path": [], "segments": [],
                "cost": None, "distance": None, "time": None, "revision": graph["revision"]}
    return {
        "found": True, "criterion": payload.criterion, "path": [points[p] for p in point_ids],
        "segments": segments, "cost": cost, "distance": sum(e["distance"] for e in segments),
        "time": sum(e["time"] for e in segments) if all(e.get("time") is not None for e in segments) else None,
        "revision": graph["revision"],
    }


@router.post("/points", status_code=201, dependencies=[Depends(require_admin)])
def add_point(payload: Point, repo=Depends(repository)):
    graph = repo.read()
    if len(graph["nodes"]) >= 500:
        raise HTTPException(409, "Limite de 500 pontos atingido.")
    node = {"id": uuid4().hex, **payload.model_dump()}
    graph["nodes"].append(node)
    save(repo, graph)
    return node


@router.put("/points/{point_id}", dependencies=[Depends(require_admin)])
def edit_point(point_id: PointId, payload: Point, repo=Depends(repository)):
    graph = repo.read()
    point_exists(graph, point_id)
    node = {"id": point_id, **payload.model_dump()}
    graph["nodes"] = [node if n["id"] == point_id else n for n in graph["nodes"]]
    save(repo, graph)
    return node


@router.delete("/points/{point_id}", status_code=204, dependencies=[Depends(require_admin)])
def delete_point(point_id: PointId, repo=Depends(repository)):
    graph = repo.read()
    point_exists(graph, point_id)
    graph["nodes"] = [n for n in graph["nodes"] if n["id"] != point_id]
    graph["edges"] = [e for e in graph["edges"] if point_id not in (e["from"], e["to"])]
    save(repo, graph)


@router.put("/connections/{origin}/{destination}", dependencies=[Depends(require_admin)])
def set_connection(origin: PointId, destination: PointId, payload: Connection, repo=Depends(repository)):
    graph = repo.read()
    point_exists(graph, origin)
    point_exists(graph, destination)
    previous = next((e for e in graph["edges"] if (e["from"], e["to"]) == (origin, destination)), None)
    if previous is None and len(graph["edges"]) >= 5000:
        raise HTTPException(409, "Limite de 5.000 conexões atingido.")
    edge = {"id": previous["id"] if previous else uuid4().hex,
            "from": origin, "to": destination, **payload.model_dump()}
    graph["edges"] = [e for e in graph["edges"] if e is not previous] + [edge]
    save(repo, graph)
    return edge


@router.delete("/connections/{origin}/{destination}", status_code=204, dependencies=[Depends(require_admin)])
def delete_connection(origin: PointId, destination: PointId, repo=Depends(repository)):
    graph = repo.read()
    old_count = len(graph["edges"])
    graph["edges"] = [e for e in graph["edges"] if (e["from"], e["to"]) != (origin, destination)]
    if len(graph["edges"]) == old_count:
        raise HTTPException(404, "Não existe conexão nesse sentido.")
    save(repo, graph)
