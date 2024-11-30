from ortools.constraint_solver import pywrapcp
from ortools.constraint_solver import routing_enums_pb2

def create_data_model():
    """Создает данные для примера с использованием графа."""
    data = {}
    # Задаем граф в виде списка рёбер (из узла, в узел, вес)
    data['edges'] = [
        # (from_node, to_node, weight)
        (0, 1, 12),
        (0, 2, 10),
        (1, 2, 9),
        (1, 3, 7),
        (2, 3, 8),
        (2, 4, 9),
        (3, 4, 11),
        (3, 6, 7),
        (4, 5, 5),
        (5, 6, 10),
        (6, 7, 8),
        (5, 7, 15),
        (0, 4, 8),
        (1, 4, 13),
        (2, 5, 12),
        (1, 6, 9),
        (0, 5, 14),
        (4, 7, 18),
        (3, 7, 12),
        (2, 7, 17),
        (0, 6, 16),
        (0, 7, 21),
    ]
    # Количество узлов (определяется на основе рёбер)
    data['num_nodes'] = 8
    data['num_vehicles'] = 2  # Количество такси
    data['depot'] = 0  # Депо (начальная и конечная точка для всех такси)
    # Пары "посадка-высадка"
    data['pickup_delivery_pairs'] = [
        [1, 6],  # Пассажир 1: посадка в узле 1, высадка в узле 6
        [2, 5],  # Пассажир 2: посадка в узле 2, высадка в узле 5
        [3, 7],  # Пассажир 3: посадка в узле 3, высадка в узле 7
    ]
    # Требования по загрузке/выгрузке (например, количество пассажиров)
    data['demands'] = [0, 1, 1, 1, 0, -1, -1, -1]
    # Вместимость транспортного средства (максимальное количество пассажиров)
    data['vehicle_capacities'] = [2, 2]  # Вместимость каждого такси
    # Список названий узлов для удобства отображения
    data['locations'] = [
        'Depot',       # 0
        'Pickup 1',    # 1
        'Pickup 2',    # 2
        'Pickup 3',    # 3
        'Location 4',  # 4
        'Delivery 2',  # 5
        'Delivery 1',  # 6
        'Delivery 3',  # 7
    ]
    return data

def compute_distance_matrix(data):
    """Вычисляет матрицу кратчайших расстояний между узлами графа."""
    num_nodes = data['num_nodes']
    # Инициализируем матрицу расстояний бесконечностями
    distance_matrix = [[float('inf')] * num_nodes for _ in range(num_nodes)]
    # Заполняем расстояния для рёбер графа
    for edge in data['edges']:
        from_node, to_node, weight = edge
        distance_matrix[from_node][to_node] = weight
        distance_matrix[to_node][from_node] = weight  # Если граф неориентированный
    # Устанавливаем нули на главной диагонали
    for i in range(num_nodes):
        distance_matrix[i][i] = 0
    # Алгоритм Флойда-Уоршелла для нахождения кратчайших путей между всеми парами узлов
    for k in range(num_nodes):
        for i in range(num_nodes):
            for j in range(num_nodes):
                if distance_matrix[i][k] + distance_matrix[k][j] < distance_matrix[i][j]:
                    distance_matrix[i][j] = distance_matrix[i][k] + distance_matrix[k][j]
    # Преобразуем бесконечности в большие числа (или оставляем как есть, если уверены, что граф связный)
    max_distance = 999999
    for i in range(num_nodes):
        for j in range(num_nodes):
            if distance_matrix[i][j] == float('inf'):
                distance_matrix[i][j] = max_distance
    return distance_matrix

def main():
    # Создаем данные модели
    data = create_data_model()

    # Вычисляем матрицу расстояний на основе графа

    data['distance_matrix'] = compute_distance_matrix(data)

    # Создаем диспетчера индексов узлов и транспортных средств
    manager = pywrapcp.RoutingIndexManager(
        len(data['distance_matrix']),
        data['num_vehicles'],
        data['depot']
    )

    # Создаем модель маршрутизации
    routing = pywrapcp.RoutingModel(manager)

    # Функция расстояния между узлами
    def distance_callback(from_index, to_index):
        # Преобразуем индексы маршрутизатора в индексы узлов
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return int(data['distance_matrix'][from_node][to_node])

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)

    # Определяем стоимость между узлами (в данном случае - расстояние)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # Добавляем ограничение по вместимости
    def demand_callback(from_index):
        """Возвращает требование в узле."""
        from_node = manager.IndexToNode(from_index)
        return data['demands'][from_node]

    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(
        demand_callback_index,
        0,  # Никакой дополнительной нагрузки не допускается
        data['vehicle_capacities'],  # Вместимость каждого такси
        True,  # Начальная загрузка равна нулю
        'Capacity'
    )
    capacity_dimension = routing.GetDimensionOrDie('Capacity')

    # Добавляем пары "посадка-высадка"
    for pickup_node, delivery_node in data['pickup_delivery_pairs']:
        pickup_index = manager.NodeToIndex(pickup_node)
        delivery_index = manager.NodeToIndex(delivery_node)
        routing.AddPickupAndDelivery(pickup_index, delivery_index)
        routing.solver().Add(
            routing.VehicleVar(pickup_index) == routing.VehicleVar(delivery_index)
        )
        routing.solver().Add(
            capacity_dimension.CumulVar(pickup_index) <= capacity_dimension.CumulVar(delivery_index)
        )

    # Настраиваем параметры поиска
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )
    search_parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    )
    search_parameters.time_limit.FromSeconds(30)

    # Решаем задачу маршрутизации
    solution = routing.SolveWithParameters(search_parameters)

    # Функция для вывода решения
    def print_solution(data, manager, routing, solution):
        total_distance = 0
        for vehicle_id in range(data['num_vehicles']):
            index = routing.Start(vehicle_id)
            plan_output = f'\nМаршрут для такси {vehicle_id + 1}:\n'
            route_distance = 0
            while not routing.IsEnd(index):
                node_index = manager.IndexToNode(index)
                plan_output += ' {0} ->'.format(data['locations'][node_index])
                previous_index = index
                index = solution.Value(routing.NextVar(index))
                if not routing.IsEnd(index):
                    route_distance += routing.GetArcCostForVehicle(previous_index, index, vehicle_id)
            node_index = manager.IndexToNode(index)
            plan_output += ' {0}\n'.format(data['locations'][node_index])
            plan_output += 'Расстояние маршрута: {} единиц\n'.format(route_distance)
            print(plan_output)
            total_distance += route_distance
        print('Общее пройденное расстояние всеми такси: {} единиц'.format(total_distance))

    # Проверяем наличие решения и выводим его
    if solution:
        print_solution(data, manager, routing, solution)
    else:
        print('Решение не найдено!')

if __name__ == '__main__':
    main()
