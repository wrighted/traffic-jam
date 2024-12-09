import simpy
import random
from Vehicle import Vehicle, Direction

# Constants
# INTER_ARRIVAL_MEAN = 5  # Mean time between arrivals (seconds)
# SERVICE_TIME_MEAN = 3   # Mean service time per vehicle (seconds)
SIMULATION_TIME = 40  # Total simulation time (seconds)
GREEN_LIGHT_TIME = 3   # Green light duration for each direction (seconds)
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

# Vehicle arrival process
def vehicle_arrival(env, lane, queue, inter_arrival_mean):
    global vehicle_count
    while True:
        yield env.timeout(random.expovariate(1 / inter_arrival_mean))
        vehicle = Vehicle(lane, random.choices([True, False], weights=[PROB_TURN, 1-PROB_TURN])[0], env.now, vehicle_count)
        vehicle_count += 1
        print(f"{vehicle} arrives in lane {vehicle.lane} {str(vehicle.direction)} at time {vehicle.arrival_time:.1f}")
        queue.put(vehicle)


# Traffic light controller
def traffic_light_controller(env, queues, green_time):
    directions = [
        ['N_Straight', 'N_Left', 'S_Straight', 'S_Left'],  # North-South
        ['E_Straight', 'E_Left', 'W_Straight', 'W_Left'],  # East-West
    ]
    while True:
        for direction in directions:
            print(f"    Green light for {direction} at time {env.now:.1f}")
            for lane in direction:
                queues[lane]['green_light'] = True
            yield env.timeout(green_time)
            for lane in direction:
                queues[lane]['green_light'] = False

# Vehicle service process
def vehicle_service(env, lane, queue, queues):
    while True:
        while not can_cross(lane, queue, queues):
            yield env.timeout(0.001)

        vehicle = yield queue.get()
        print(f"{vehicle} starts crossing {lane} at time {env.now:.1f}")
        
        vehicle.set_start_time(env.now)        
        currently_crossing[lane].append(vehicle)
        yield env.timeout(vehicle.service_time)

        print(f"{vehicle} finishes crossing {lane} at time {env.now:.1f}")
        currently_crossing[lane] = [v for v in currently_crossing[lane] if v != vehicle]

def first_vehicle_direction(queue):
    return queue.items[0].direction

def queue_empty(queue):
    return len(queue.items) == 0

def can_cross(lane, queue, queues):
    # check that the light is green
    if not queues[lane]['green_light']:
        return False
    
    if not queue_empty(queue):
        # check for each direction
        match (first_vehicle_direction(queue)):
            case Direction.LEFT:
                return can_cross_left(lane, queues)
            case Direction.STRAIGHT:
                return can_cross_straight(lane)
            case _:
                return True

''' return True if the car can turn left, False otherwise '''
def can_cross_left(lane, queues):
    opp_1, opp_2 = OPPOSING_LANES[lane]
    # check if the current and opposing lanes in intersection are free
    if lanes_free_in_intersection({opp_1: [Direction.STRAIGHT], opp_2: [Direction.STRAIGHT], lane: [Direction.LEFT, Direction.STRAIGHT]}):
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
def can_cross_straight(lane):
    # check if the current and opposing lanes in intersection are free
    return lanes_free_in_intersection({OPPOSING_LANES[lane][0]: [Direction.LEFT], lane: [Direction.LEFT, Direction.STRAIGHT, Direction.RIGHT]})

''' check if the lane has any cars going in the specified direction
that have not completed half their service time '''
def lanes_free_in_intersection(lanes):
    for lane, direction in lanes.items():
        # check that all cars in the specified direction have completed half their service time
        if not all([vehicle.direction in direction and vehicle.service_half_completed() for vehicle in currently_crossing[lane]]):
            return False
        
    return True

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

    # Run the simulation
    env.run(until=SIMULATION_TIME)

if __name__ == "__main__":
    main()
