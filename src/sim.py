import simpy
import random
from Vehicle import Vehicle, Direction
import sys

# Constants
# INTER_ARRIVAL_MEAN = 5  # Mean time between arrivals (seconds)
# SERVICE_TIME_MEAN = 3   # Mean service time per vehicle (seconds)
adaptive = False

SIMULATION_TIME = 1000  # Total simulation time (seconds)
MAX_GREEN_TIME = 35  # Maximum green light duration for each direction (seconds)
GREEN_LIGHT_TIME = 25  # Green light duration for both directions (seconds)
MIN_GREEN_TIME = 10
LANES = ['N_Straight', 'N_Left', 'S_Straight', 'S_Left',
         'E_Straight', 'E_Left', 'W_Straight', 'W_Left']

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

AVG_RUSH_HOUR = 3000 / len(LANES) # cars per hour
AVG_LOW_TRAFFIC = 300 / len(LANES) # cars per hour

INTER_ARRIVAL_MEAN = 3600 / AVG_RUSH_HOUR # seconds
# INTER_ARRIVAL_MEAN = 3600 / AVG_LOW_TRAFFIC # seconds

PROB_TURN = 0.1
vehicle_count = 0
currently_crossing = {lane: [] for lane in LANES}
queue_lengths = {lane: [] for lane in LANES}
queue_avg = []
all_vehicles = []
next_green = GREEN_LIGHT_TIME

''' return True if the queue is empty, False otherwise '''
def queue_empty(queue):
    return len(queue.items) == 0


# Vehicle arrival process
def vehicle_arrival(env, lane, queue, inter_arrival_mean):
    global vehicle_count
    while True:
        yield env.timeout(random.expovariate(1 / inter_arrival_mean))
        vehicle = Vehicle(lane, random.choices([True, False], weights=[PROB_TURN, 1-PROB_TURN])[0], env.now, vehicle_count)
        vehicle_count += 1

        print_vehicle(vehicle, "Arrival")
        if queue_empty(queue):
            vehicle.set_front_time(env.now)

        queue.put(vehicle)
        all_vehicles.append(vehicle)


# Traffic light controller
def traffic_light_controller(env, queues, green_time):
    global next_green
    directions = [
        ['N_Straight', 'N_Left', 'S_Straight', 'S_Left'],  # North-South
        ['E_Straight', 'E_Left', 'W_Straight', 'W_Left'],  # East-West
    ]

    while True:
        for direction in directions:
            print_light_change(env.now, direction)
            for lane in direction:
                queues[lane]['green_light'] = True
            
            if adaptive:
                queue_ns, queue_ew = sum_queues(directions)

                if (direction == directions[0] and queue_ns > 20) or (direction == directions[1] and queue_ew > 20):
                    green_time = MAX_GREEN_TIME
                elif (direction == directions[0] and queue_ns < 10) or (direction == directions[1] and queue_ew < 10):
                    green_time = MIN_GREEN_TIME
                else:
                    green_time = GREEN_LIGHT_TIME
            else:
                green_time = GREEN_LIGHT_TIME

            while green_time > 0:
                next_green = green_time
                green_time -= 0.1
                yield env.timeout(0.1)

            for lane in direction:
                queues[lane]['green_light'] = False


# Return the total length of the queues in each direction
def sum_queues(directions):
    dir1 = sum([queue_lengths[lane][-1] if len(queue_lengths[lane]) > 0 else 0 for lane in directions[0]])
    dir2 = sum([queue_lengths[lane][-1] if len(queue_lengths[lane]) > 0 else 0 for lane in directions[1]])
    return dir1, dir2


# Vehicle service process
def vehicle_service(env, lane, queue, queues):
    while True:
        while not can_cross(env.now, lane, queue, queues):
            yield env.timeout(0.001)

        vehicle = yield queue.get()

        # set the time the vehicle reached the front of the queue
        if not queue_empty(queue):
            queue.items[0].set_front_time(env.now)
        
        print_vehicle(vehicle, "Start")

        env.process(vehicle_crossing(env, lane, vehicle))


def vehicle_crossing(env, lane, vehicle):
    currently_crossing[lane].append(vehicle)
    yield env.timeout(vehicle.service_time)
    
    print_vehicle(vehicle, "End")
    currently_crossing[lane] = [v for v in currently_crossing[lane] if v != vehicle]


''' return the direction of the first vehicle in the queue '''
def first_vehicle_direction(queue):
    return queue.items[0].direction


''' return True if the car can cross the intersection, False otherwise '''
def can_cross(current_time, lane, queue, queues):
    # check that the light is green
    if not queues[lane]['green_light']:
        return False
    
    if not queue_empty(queue):
        vehicle = queue.items[0]
        vehicle.set_start_time(max(current_time, vehicle.arrival_time))
        vehicle.set_service_time()

        # check for each direction
        match (first_vehicle_direction(queue)):
            case Direction.LEFT:
                intersection_free = can_cross_left(current_time, lane, queues)
            case Direction.STRAIGHT:
                intersection_free = can_cross_straight(current_time, lane)
            case Direction.RIGHT:
                intersection_free = can_cross_right(current_time, lane)

        if intersection_free and vehicle.service_time > next_green:
            # ensure there is enough time to cross before the light changes
            return False

        return intersection_free
    else:
        return False

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


''' return True if the car can turn right, False otherwise '''
def can_cross_right(current_time, lane):
    return lanes_free_in_intersection(current_time, {lane: [Direction.STRAIGHT, Direction.RIGHT]})


''' check if the lane has any cars going in the specified direction
that have not completed half their service time '''
def lanes_free_in_intersection(current_time, lanes):
    for lane, direction in lanes.items():
        # check that all cars in the specified direction have completed half their service time
        for vehicle in currently_crossing[lane]:
            if vehicle.direction in direction and not vehicle.service_almost_complete(current_time):
                return False
        
    return True


# Function to update queue lengths periodically
def update_queue_lengths(env, queues):
    while True:
        for lane, queue in queues.items():
            queue_lengths[lane].append(len(queue['queue'].items))

        yield env.timeout(1)  # Update every second


# Print vehicle information
def print_vehicle(vehicle, type):
    start_time = round(vehicle.start_time, 2) if vehicle.start_time else ''
    end_time = round(vehicle.start_time + vehicle.service_time, 2) if vehicle.start_time and type == 'End' else ''

    print(f"{vehicle.id:<10} | {type:<10} | {vehicle.arrival_time:<12.2f} | {start_time:<10} | {end_time:<8} | {vehicle.lane:<10} | {vehicle.direction.name:<10}")


# Print light change information
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
        env.process(update_queue_lengths(env, queues))

    # print(f"{'Vehicle id':<10} | {'Type':<10} | {'Arrival time':<12} | {'Start time':<10} | {'End time':<8} | {'Lane':<10} | {'Direction':<10}")
    # Run the simulation
    env.run(until=SIMULATION_TIME)

    # Print statistics
    print("Statistics")

    waiting_times = [(vehicle.start_time if vehicle.start_time is not None else SIMULATION_TIME) - vehicle.arrival_time for vehicle in all_vehicles]
    vehicles_crossed = len(list(filter(lambda x: x.start_time is not None, all_vehicles)))
    print(f"Average waiting time: {sum(waiting_times) / len(waiting_times)}")
    print("Total vehicles: ", len(all_vehicles))
    print(f"Vehicles crossed: {vehicles_crossed}")
    throughput = vehicles_crossed / SIMULATION_TIME
    print(f"Throughput: {throughput} vehicles / second")
    print(f"Max queue length: {max([max(queue_lengths[lane]) for lane in LANES])}")
    print(f"Avg queue length: {sum([sum(queue_lengths[lane]) for lane in LANES]) / sum(len(queue_lengths[lane]) for lane in LANES)}")
    max_possible_flow = len(all_vehicles) / SIMULATION_TIME
    print(f"Traffic flow efficiency: {throughput / max_possible_flow * 100}%\n")

if __name__ == "__main__":
    seed = sys.argv[1]
    adaptive = False if sys.argv[2] == 'False' else True
    print(f'Seed: {seed}')
    random.seed(seed)
    main()