import simpy
import random

# Constants
INTER_ARRIVAL_MEAN = 5  # Mean time between arrivals (seconds)
SERVICE_TIME_MEAN = 3   # Mean service time per vehicle (seconds)
SIMULATION_TIME = 3600  # Total simulation time (seconds)
GREEN_LIGHT_TIME = 30   # Green light duration for each direction (seconds)
LANES = ['N_Straight', 'N_Left', 'S_Straight', 'S_Left',
         'E_Straight', 'E_Left', 'W_Straight', 'W_Left']

# Vehicle arrival process
def vehicle_arrival(env, lane, queue, inter_arrival_mean):
    while True:
        yield env.timeout(random.expovariate(1 / inter_arrival_mean))
        vehicle = f"Vehicle_{lane}_{env.now}"
        print(f"{vehicle} arrives at {lane} at time {env.now:.1f}")
        queue.put(vehicle)

# Traffic light controller
def traffic_light_controller(env, queues, green_time):
    directions = [
        ['N_Straight', 'N_Left', 'S_Straight', 'S_Left'],  # North-South
        ['E_Straight', 'E_Left', 'W_Straight', 'W_Left'],  # East-West
    ]
    while True:
        for direction in directions:
            print(f"Green light for {direction} at time {env.now:.1f}")
            for lane in direction:
                queues[lane]['green_light'] = True
            yield env.timeout(green_time)
            for lane in direction:
                queues[lane]['green_light'] = False

# Vehicle service process
def vehicle_service(env, lane, queue, service_time_mean):
    while True:
        vehicle = yield queue.get()
        print(f"{vehicle} starts crossing {lane} at time {env.now:.1f}")
        yield env.timeout(random.expovariate(1 / service_time_mean))
        print(f"{vehicle} finishes crossing {lane} at time {env.now:.1f}")

# Main simulation setup
def main():
    env = simpy.Environment()
    
    # Create queues and processes for each lane
    queues = {
        lane: {'queue': simpy.Store(env), 'green_light': False}
        for lane in LANES
    }
    
    for lane in LANES:
        env.process(vehicle_arrival(env, lane, queues[lane]['queue'], INTER_ARRIVAL_MEAN))
        env.process(vehicle_service(env, lane, queues[lane]['queue'], SERVICE_TIME_MEAN))
    
    # Start the traffic light controller
    env.process(traffic_light_controller(env, queues, GREEN_LIGHT_TIME))
    
    # Run the simulation
    env.run(until=SIMULATION_TIME)

if __name__ == "__main__":
    main()
