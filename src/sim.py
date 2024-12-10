import simpy
import random
from Vehicle import Vehicle, Direction
import math
# Constants
# INTER_ARRIVAL_MEAN = 5  # Mean time between arrivals (seconds)
# SERVICE_TIME_MEAN = 3   # Mean service time per vehicle (seconds)
SIMULATION_TIME = 40  # Total simulation time (seconds)
GREEN_LIGHT_TIME = 23  # Green light duration for each direction (seconds)
LANES = ['N_Straight', 'N_Left', 'S_Straight', 'S_Left',
         'E_Straight', 'E_Left', 'W_Straight', 'W_Left']

lanes = []

OPPOSING_LANES = {
    'N_Left': ['S_Straight', 'S_Left'],
    'S_Left': ['N_Straight', 'N_Left'],
    'E_Left': ['W_Straight', 'W_Left'],
    'W_Left': ['E_Straight', 'E_Left'], 
    'N_Straight': ['S_Left'],
    'S_Straight': ['N_Left'],
    'E_Straight': ['W_Left'],
    'W_Straight': ['E_Left'],
}

AVG_RUSH_HOUR = 1443 / len(LANES) # cars per hour, based on crd data
AVG_LOW_TRAFFIC = 42 / len(LANES) # cars per hour

INTER_ARRIVAL_MEAN = 3600 / AVG_RUSH_HOUR # seconds
# INTER_ARRIVAL_MEAN = 3600 / AVG_LOW_TRAFFIC # seconds

PROB_TURN = 0.25
vehicle_count = 0
currently_crossing = {lane: [] for lane in LANES}

def equation(lambda_param):
    term1 = math.e(-lambda_param * 2.5)
    term2 = math.e(-lambda_param * 3.5)
    return term1 - term2 - 0.95

# Vehicle arrival process
def vehicle_arrival(env, lane, queue, inter_arrival_mean):
    global vehicle_count
    while True:
        yield env.timeout(random.expovariate(1 / inter_arrival_mean))
        vehicle = Vehicle(lane, random.choices([True, False], weights=[PROB_TURN, 1-PROB_TURN])[0], env.now, vehicle_count)
        vehicle_count += 1
        print_vehicle(vehicle, "Arrival")
        queue.put(vehicle)


# Traffic light controller
def traffic_light_controller(env, queues, green_time):
    directions = [
        ['N_Straight', 'N_Left', 'S_Straight', 'S_Left'],  # North-South
        ['E_Straight', 'E_Left', 'W_Straight', 'W_Left'],  # East-West
    ]
    while True:
        for direction in directions:
            print_light_change(env.now, direction)
            for lane in direction:
                queues[lane]['green_light'] = True
            yield env.timeout(green_time)
            for lane in direction:
                queues[lane]['green_light'] = False

# Vehicle service process
def vehicle_service(env, lane, queue, queues):
    while True:
        while not can_cross(env.now, lane, queue, queues):
            yield env.timeout(0.001)

        vehicle = yield queue.get()
        
        vehicle.set_start_time(env.now)
        vehicle.set_service_time()
        print_vehicle(vehicle, "Start")

        currently_crossing[lane].append(vehicle)
        yield env.timeout(vehicle.service_time)

        print_vehicle(vehicle, "End")
        currently_crossing[lane] = [v for v in currently_crossing[lane] if v != vehicle]

''' return the direction of the first vehicle in the queue '''
def first_vehicle_direction(queue):
    return queue.items[0].direction

''' return True if the queue is empty, False otherwise '''
def queue_empty(queue):
    return len(queue.items) == 0

''' return True if the car can cross the intersection, False otherwise '''
def can_cross(current_time, lane, queue, queues):
    # check that the light is green
    if not queues[lane]['green_light']:
        return False
    
    if not queue_empty(queue):
        # check for each direction
        match (first_vehicle_direction(queue)):
            case Direction.LEFT:
                return can_cross_left(current_time, lane, queues)
            case Direction.STRAIGHT:
                return can_cross_straight(current_time, lane)
            case _:
                return True

''' return True if the car can turn left, False otherwise '''
def can_cross_left(current_time, lane, queues):
    opp_1, opp_2 = OPPOSING_LANES[lane]
    # check if the current and opposing lanes in intersection are free
    if lanes_free_in_intersection(current_time, {opp_1: [Direction.STRAIGHT], opp_2: [Direction.STRAIGHT], lane: [Direction.LEFT, Direction.STRAIGHT]}):
        opp_1_queue = queues[opp_1]['queue']
        opp_2_queue = queues[opp_2]['queue']

        # if both opposing lanes are free, can go left
        if queue_empty(opp_1_queue) and queue_empty(opp_2_queue):
            return True
        
        # if there is a car going straight in the opposing lanes, can't go left
        if (not queue_empty(opp_1_queue) and first_vehicle_direction(opp_1_queue) == Direction.STRAIGHT) or \
            (not queue_empty(opp_2_queue) and first_vehicle_direction(opp_2_queue) == Direction.STRAIGHT):
            return False
        
        return True
    
    return False

''' return True if the car can go straight, False otherwise '''
def can_cross_straight(current_time, lane):
    # check if the current and opposing lanes in intersection are free
    return lanes_free_in_intersection(current_time, {OPPOSING_LANES[lane][0]: [Direction.LEFT], lane: [Direction.LEFT, Direction.STRAIGHT, Direction.RIGHT]})

''' check if the lane has any cars going in the specified direction
that have not completed half their service time '''
def lanes_free_in_intersection(current_time, lanes):
    for lane, direction in lanes.items():
        # check that all cars in the specified direction have completed half their service time
        if not all([vehicle.direction in direction and vehicle.service_half_completed(current_time) for vehicle in currently_crossing[lane]]):
            return False
        
    return True

def print_vehicle(vehicle, type):
    start_time = round(vehicle.start_time, 2) if vehicle.start_time else ''
    end_time = round(vehicle.start_time + vehicle.service_time, 2) if vehicle.start_time and type == 'End' else ''

    print(f"{vehicle.id:<10} | {type:<10} | {vehicle.arrival_time:<12.2f} | {start_time:<10} | {end_time:<8} | {vehicle.lane:<10} | {vehicle.direction.name:<10}")

def print_light_change(time, lanes):
    lane = 'E, W' if lanes[0][0] == 'E' else 'N, S'
    print(f"{'':<10} | {'Green':<10} | {'':<12} | {time:<10.2f} | {'':<8} | {lane:<10} | {'':<10}")

# Main simulation setup
def main():
    env = simpy.Environment()
    
    # Create queues and processes for each lane
    queues = {
        lane: {'queue': simpy.Store(env), 'green_light': False}
        for lane in LANES
    }

    # Start the traffic light controller
    env.process(traffic_light_controller(env, queues, GREEN_LIGHT_TIME))

    for lane in LANES:
        env.process(vehicle_arrival(env, lane, queues[lane]['queue'], INTER_ARRIVAL_MEAN))
        env.process(vehicle_service(env, lane, queues[lane]['queue'], queues))

    print(f"{'Vehicle id':<10} | {'Type':<10} | {'Arrival time':<12} | {'Start time':<10} | {'End time':<8} | {'Lane':<10} | {'Direction':<10}")
    # Run the simulation
    env.run(until=SIMULATION_TIME)

if __name__ == "__main__":
    main()
