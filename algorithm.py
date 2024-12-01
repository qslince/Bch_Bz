import numpy as np
import pandas as pd
from ortools.constraint_solver import pywrapcp, routing_enums_pb2
import sqlite3

# Загрузка данных из файла
edges = pd.read_excel("edges.xlsx", index_col=0)

def create_data_model():
    conn = sqlite3.connect('test.db')
    query = "SELECT * FROM taxi_orders"
    orders_df = pd.read_sql(query, conn)
    all_locations = pd.concat([orders_df['start_location'], orders_df['end_location']]).unique()
    """Создает данные для примера с использованием графа."""
    edges.columns = ['from_node', 'to_node', 'weight']
    data = {}
    data['edges'] = edges.values.tolist()
    # Определяем количество узлов как максимальный номер узла +1
    data['num_nodes'] = max(edges['from_node'].max(), edges['to_node'].max()) + 1
    data['num_vehicles'] = 10
    data['depot'] = 2
    data['pickup_delivery_pairs'] = []
    data['pickup_delivery_pairs'] = []
    for _, order in orders_df.iterrows():
        start_location = order['start_location']
        end_location = order['end_location']
        
        pickup = all_locations.tolist().index(start_location)
        deliv = all_locations.tolist().index(end_location)
        
        data['pickup_delivery_pairs'].append([pickup+1, deliv+1])
        


    # Инициализируем список demands нулями для всех узлов
    data['demands'] = [0] * data['num_nodes']

    # Назначаем спрос для узлов пикапа и доставки
    for pickup_node, delivery_node in data['pickup_delivery_pairs']:
        data['demands'][pickup_node] = 1    # Узел пикапа: +1
        data['demands'][delivery_node] = -1  # Узел доставки: -1

    # Вместимость каждого транспортного средства
    data['vehicle_capacities'] = [5] * data['num_vehicles']

    # Определяем названия локаций
    data['locations'] = [0] * data['num_nodes']
    # Добавляем названия для остальных узлов, если они есть
    if data['num_nodes'] > len(data['locations']):
        data['locations'] += [f'Location {i}' for i in range(len(data['locations']), data['num_nodes'])]

    return data

def compute_distance_matrix(data):
    """Вычисляет матрицу кратчайших расстояний между узлами графа с использованием NumPy."""
    num_nodes = data['num_nodes']
    distance_matrix = np.full((num_nodes, num_nodes), np.inf)

    # Заполнение матрицы расстояний на основе рёбер
    for from_node, to_node, weight in data['edges']:
        distance_matrix[from_node, to_node] = weight
        distance_matrix[to_node, from_node] = weight
    # Установка диагонали в 0
    np.fill_diagonal(distance_matrix, 0)

    # Применение алгоритма Флойда-Уоршелла для вычисления всех кратчайших путей
    for k in range(num_nodes):
        distance_matrix = np.minimum(
            distance_matrix,
            np.add.outer(distance_matrix[:, k], distance_matrix[k, :])
        )

    # Замена бесконечностей на большое число
    distance_matrix[distance_matrix == np.inf] = 999999
    return distance_matrix.astype(int)

def main():
    data = create_data_model()
    data['distance_matrix'] = compute_distance_matrix(data)

    # Создание менеджера индексов маршрутизации
    manager = pywrapcp.RoutingIndexManager(
        len(data['distance_matrix']),
        data['num_vehicles'],
        data['depot']
    )

    # Создание модели маршрутизации
    routing = pywrapcp.RoutingModel(manager)

    # Callback для расчета расстояния между узлами
    def distance_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return data['distance_matrix'][from_node][to_node]

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # Callback для расчета спроса в узлах
    def demand_callback(from_index):
        """Возвращает требование в узле."""
        from_node = manager.IndexToNode(from_index)
        return data['demands'][from_node]

    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)

    # Добавление ограничений по вместимости
    routing.AddDimensionWithVehicleCapacity(
        demand_callback_index,
        0,  # Нет дополнительного запаса
        data['vehicle_capacities'],  # Вместимость транспортных средств
        True,  # Начальные значения коррелируют с узлами депо
        'Capacity'
    )

    capacity_dimension = routing.GetDimensionOrDie('Capacity')

    # Добавление пар подъема и доставки
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

    # Параметры поиска
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (

        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )
    search_parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    )
    search_parameters.time_limit.FromSeconds(30)

    # Решение задачи маршрутизации
    solution = routing.SolveWithParameters(search_parameters)

    # Функция для печати решения
    def print_solution(data, manager, routing, solution):
       total_distance = 0
       for vehicle_id in range(data['num_vehicles']):
           index = routing.Start(vehicle_id)
           if routing.IsEnd(solution.Value(routing.NextVar(index))):
               continue  # Пропускаем транспортные средства без маршрута
           plan_output = f'\nМаршрут для такси {vehicle_id + 1}:\n'
           route_distance = 0
           route_load = 0
           while not routing.IsEnd(index):
               node_index = manager.IndexToNode(index)
               route_load += data['demands'][node_index]
               plan_output += f' {data["locations"][node_index]} (нагрузка: {route_load}) ->'
               previous_index = index
               index = solution.Value(routing.NextVar(index))
               if not routing.IsEnd(index):
                   route_distance += routing.GetArcCostForVehicle(previous_index, index, vehicle_id)
           node_index = manager.IndexToNode(index)
           plan_output += f' {data["locations"][node_index]} (нагрузка: {route_load})\n'
           plan_output += f'Расстояние маршрута: {route_distance} единиц\n'
           print(plan_output)
           total_distance += route_distance
       print(f'Общее пройденное расстояние всеми такси: {total_distance} единиц')

    # Печать решения или сообщение об отсутствии решения
    if solution:
        print_solution(data, manager, routing, solution)
    else:
        print('Решение не найдено!')

if __name__ == '__main__':
    main()
