from enum import Enum
import random

class Direction(Enum):
    LEFT = 1
    RIGHT = 2
    STRAIGHT = 3

    def __str__(self):
        return f'going {self.name.lower()}'

class Vehicle:
    AVG_LEFT_TURN_MOVING = 2 # seconds
    AVG_LEFT_TURN_STOPPED = 3  # seconds
    AVG_RIGHT_TURN_MOVING = 1 # seconds
    AVG_RIGHT_TURN_STOPPED = 2 # seconds
    AVG_STRAIGHT_MOVING = 1 # seconds
    AVG_STRAIGHT_STOPPED = 2 # seconds

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
        moving = (self.start_time - self.front_time) < 0.5
        match self.direction:
            case Direction.LEFT:
                return self.AVG_LEFT_TURN_MOVING if moving else self.AVG_LEFT_TURN_STOPPED
            case Direction.RIGHT:
                return self.AVG_RIGHT_TURN_MOVING if moving else self.AVG_RIGHT_TURN_STOPPED
            case Direction.STRAIGHT:
                return self.AVG_STRAIGHT_MOVING if moving else self.AVG_STRAIGHT_STOPPED

    def set_service_time(self):
        mean_service_time = self.get_mean_service_time()
        lower_bound = mean_service_time - 0.5
        upper_bound = mean_service_time + 0.5

        while not lower_bound <= (service_time := random.expovariate(1 / mean_service_time)) <= upper_bound:
            continue

        self.service_time = service_time

    def set_start_time(self, start_time):
        self.start_time = start_time

    def service_half_completed(self, current_time):
        return (self.start_time + self.service_time) - self.service_time * 0.5  <= current_time
    
    def set_front_time(self, front_time):
        self.front_time = front_time