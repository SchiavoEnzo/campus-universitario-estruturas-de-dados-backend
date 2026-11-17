from heapq import heappop, heappush
from math import inf, isfinite


class CampusMap:
    def __init__(self):
        self._points = {
            1: "Bloco A",
            2: "Biblioteca",
            3: "Laboratório de Informática",
            4: "Laboratório de Carcanhas",
        }
        self._graph = {
            1: ((2, 150),),
            2: ((3, 100),),
            3: ((1, 200),),
            4: ((1, 750),),
        }

    def points(self):
        return self._points.copy()

    def connections(self):
        return self._graph.copy()

    def add_point(self, name):
        name = name.strip()
        if not name:
            raise ValueError("O nome do ponto não pode ficar vazio.")
        code = max(self._points, default=0) + 1
        self._points[code] = name
        self._graph[code] = ()
        return code

    def remove_point(self, code):
        if code not in self._points:
            raise ValueError("Ponto não cadastrado.")
        del self._points[code]
        del self._graph[code]
        for origin, neighbors in self._graph.items():
            self._graph[origin] = tuple(
                (destination, weight) for destination, weight in neighbors
                if destination != code
            )

    def set_connection(self, origin, destination, distance):
        if origin not in self._graph or destination not in self._graph:
            raise ValueError("Origem ou destino não cadastrado no mapa.")
        if not isfinite(distance) or distance < 0:
            raise ValueError("A distância deve ser finita e não negativa.")
        neighbors = tuple(
            (point, weight) for point, weight in self._graph[origin]
            if point != destination
        )
        self._graph[origin] = neighbors + ((destination, distance),)

    def remove_connection(self, origin, destination):
        if origin not in self._graph or destination not in self._graph:
            raise ValueError("Origem ou destino não cadastrado no mapa.")
        if not any(point == destination for point, _ in self._graph[origin]):
            raise ValueError("Não existe conexão nesse sentido.")
        self._graph[origin] = tuple(
            (point, weight) for point, weight in self._graph[origin]
            if point != destination
        )

    def dijkstra(self, origin, destination):
        if origin not in self._graph or destination not in self._graph:
            raise ValueError("Origem ou destino não cadastrado no mapa.")

        distances = dict.fromkeys(self._graph, inf)
        predecessors = dict.fromkeys(self._graph, None)
        distances[origin] = 0
        queue = [(0, origin)]

        while queue:
            current_distance, current = heappop(queue)

            if current_distance != distances[current]:
                continue

            if current == destination:
                break

            for neighbor, weight in self._graph[current]:
                new_distance = current_distance + weight

                if new_distance < distances[neighbor]:
                    distances[neighbor] = new_distance
                    predecessors[neighbor] = current
                    heappush(queue, (new_distance, neighbor))

        if distances[destination] == inf:
            return [], inf

        path = []
        current = destination

        while current is not None:
            path.append(current)
            current = predecessors[current]

        path.reverse()
        return path, distances[destination]


def show_points(campus):
    print("\nPONTOS DE ACESSO")
    points = campus.points()
    if not points:
        print("Nenhum ponto cadastrado. Adicione um ponto no menu de alteração.")
    for code, name in points.items():
        print(f"{code} - {name}")


def edit_map(campus):
    while True:
        show_points(campus)
        print("\nALTERAR MAPA")
        print("1 - Adicionar ponto")
        print("2 - Remover ponto e suas conexões")
        print("3 - Criar conexão ou alterar sua distância")
        print("4 - Remover conexão")
        print("0 - Voltar")
        print("Conexões têm sentido único. Para ida e volta, configure os dois sentidos.")
        option = input("Escolha uma opção: ").strip()

        if option == "0":
            return
        if option not in ("1", "2", "3", "4"):
            print("Opção inválida.")
            continue

        try:
            if option == "1":
                code = campus.add_point(input("Nome do novo ponto: "))
                print(f"Ponto cadastrado com o código {code}.")
            elif option == "2":
                code = int(input("Código do ponto a remover: "))
                campus.remove_point(code)
                print("Ponto e suas conexões removidos.")
            else:
                origin = int(input("Código do ponto de origem: "))
                destination = int(input("Código do ponto de destino: "))
                if option == "3":
                    distance = float(input("Distância em metros: ").replace(",", "."))
                    campus.set_connection(origin, destination, distance)
                    print("Conexão cadastrada ou atualizada.")
                else:
                    campus.remove_connection(origin, destination)
                    print("Conexão removida.")
        except ValueError as error:
            print(f"Entrada inválida: {error}")


def main():
    campus = CampusMap()

    try:
        while True:
            print("\nNAVEGAÇÃO DO CAMPUS")
            print("1 - Visualizar o mapa")
            print("2 - Calcular a menor rota")
            print("3 - Alterar o mapa")
            print("0 - Sair")
            option = input("Escolha uma opção: ").strip()

            if option == "0":
                print("Programa encerrado.")
                break

            if option == "3":
                edit_map(campus)
                continue

            if option not in ("1", "2"):
                print("Opção inválida. Escolha 1, 2, 3 ou 0.")
                continue

            show_points(campus)
            points = campus.points()

            if option == "1":
                print("\nCONEXÕES DIRECIONADAS (DISTÂNCIA EM METROS)")
                if not any(campus.connections().values()):
                    print("Nenhuma conexão cadastrada.")
                for origin, neighbors in campus.connections().items():
                    for destination, distance in neighbors:
                        print(f"{points[origin]} → {points[destination]}: {distance} m")
                continue

            if not points:
                continue

            try:
                origin = int(input("Código do ponto de origem: "))
                destination = int(input("Código do ponto de destino: "))
                path, distance = campus.dijkstra(origin, destination)
            except ValueError as error:
                print(f"Entrada inválida: {error}")
                continue

            if not path:
                print("Não existe rota entre os pontos escolhidos nesse sentido.")
                continue

            print("\nROTA DE MENOR DISTÂNCIA")
            print(" → ".join(points[point] for point in path))
            print(f"Distância total: {distance} metros")
    except (EOFError, KeyboardInterrupt):
        print("\nPrograma encerrado.")


if __name__ == "__main__":
    main()
