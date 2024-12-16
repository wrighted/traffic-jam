from enum import Enum
import random

class Direction(Enum):
    LEFT = 1
    RIGHT = 2
    STRAIGHT = 3

    def __str__(self):
        return f'going {self.name.lower()}'

class Vehicle:
    AVG_LEFT_TURN = 3.5 # seconds
    AVG_RIGHT_TURN = 2.5 # seconds
    AVG_STRAIGHT_MOVING = 2.5 # seconds
    AVG_STRAIGHT_STOPPED = 4.5 # seconds

    def __init__(self, lane, turn, arrival_time, id):
        self.lane = lane
        self.direction = self.set_direction(lane, turn)
        self.arrival_time = round(arrival_time, 1)
        self.service_time = None
        self.start_time = None
        self.front_time = None
        self.id = id

    def __repr__(self):
        return f"Vehicle {self.id}"
    
    def set_direction(self, lane, turn):
        return Direction.STRAIGHT if not turn else Direction.RIGHT if lane.endswith('Straight') else Direction.LEFT
        
    def get_mean_service_time(self):
        match self.direction:
            case Direction.LEFT:
                return self.AVG_LEFT_TURN
            case Direction.RIGHT:
                return self.AVG_RIGHT_TURN
            case Direction.STRAIGHT:
                moving = (self.start_time - self.front_time) <= 1
                return self.AVG_STRAIGHT_MOVING if moving else self.AVG_STRAIGHT_STOPPED

    def set_service_time(self):
        mean_service_time = self.get_mean_service_time()
        lower_bound = mean_service_time - 0.25
        upper_bound = mean_service_time + 0.25

        while not lower_bound <= (service_time := random.expovariate(1 / mean_service_time)) <= upper_bound:
            continue

        self.service_time = service_time

    def set_start_time(self, start_time):
        self.start_time = start_time

    # check if the vehicle has completed 90% of its service time
    def service_almost_complete(self, current_time):
        return (current_time - self.start_time) >= (0.9 * self.service_time)
    
    def set_front_time(self, front_time):
        self.front_time = front_time