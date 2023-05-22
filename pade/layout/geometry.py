import numpy as np
import copy


class Coordinate:
    def __init__(self, coord) -> None:
        # Assume subscriptable input
        self.x = np.round(float(coord[0]), decimals=2)
        self.y = np.round(float(coord[1]), decimals=2)

    def to_skill(self):
        return f'{self.x}:{self.y}'

    def to_list(self, decimals=2):
        return [np.round(self.x, decimals=decimals), np.round(self.y, decimals=decimals)]

    def __round__(self, ndigits=0):
        return Coordinate((round(self[0], ndigits), round(self[1], ndigits)))

    def __getitem__(self, item):
        if item == 0:
            return self.x
        elif item == 1:
            return self.y
        else:
            raise ValueError(f'Invalid index for coordinate {item}')

    def __add__(self, other):
        """
        Assumes other is subscriptable
        """
        if other is None:
            return self
        try:
            return Coordinate((self[0] + other[0], self[1] + other[1]))
        except:
            return Coordinate((self[0] + other, self[1] + other))

    def __sub__(self, other):
        """
        Assumes other is subscriptable
        """
        if other is None:
            return self
        try:
            return Coordinate((self[0] - other[0], self[1] - other[1]))
        except:
            return Coordinate((self[0] - other, self[1] - other))

    def __str__(self) -> str:
        return f'Coordinate({self[0]},{self[1]})'

    def __repr__(self) -> str:
        return f'Coordinate({self[0]},{self[1]})'


class Vector:
    """
    Vector class
    Stores only a np array
    """
    def __init__(self, *args) -> None:
        if len(args) == 1:
            vector = args[0]
            # Assume subscriptable
            self.array = np.array(
                [vector[0], vector[1]])
        elif len(args) == 2:
            # assume initialization by start and stop
            start = args[0]
            stop = args[1]
            self.array = np.array([stop[0]-start[0], stop[1]-start[1]])
        self.array = np.round(self.array, decimals=2)

    def __getitem__(self, item):
        return self.array[item]

    def __add__(self, other):
        if other is None:
            return self
        try:
            # if other is subscriptable
            return Vector((self[0] + other[0], self[1] + other[1]))
        except:
            # Assume scalar
            return Vector((self[0] + other, self[1] + other))

    def __sub__(self, other):
        if other is None:
            return self
        return self + (other * (-1))

    def __mul__(self, other):
        if other is None:
            return None
        return Vector(self.array*other)

    def __truediv__(self, other):
        return Vector(self.array/other)

    def __neg__(self):
        return Vector(-self.array)

    def __len__(self):
        return np.sqrt(self[0]**2 + self[1]**2)

    def __str__(self) -> str:
        return f'Vector({self[0]},{self[1]})'

    def __repr__(self) -> str:
        return f'Vector({self[0]},{self[1]})'

    def normalize(self):
        return Vector(self) / (np.sqrt(self[0]**2 + self[1]**2))

    def x(self):
        return self.array[0]

    def y(self):
        return self.array[1]

    def to_coordinate(self):
        return Coordinate(self)

    def rotate(self, angle):
        """
        Rotate vector by specified angle
        Returns the rotated version of the vector
        """
        # Rotation matrix:
        angle_rad = np.deg2rad(angle)
        Rmat = np.array([[np.cos(angle_rad), -np.sin(angle_rad)], [np.sin(angle_rad), np.cos(angle_rad)]])
        rot_array = Rmat@self.array
        return Vector(np.round(rot_array, decimals=4))

    def quadrant(self):
        """
        Return the quadrant
        """
        if self[0] > 0 and self[1] > 0:
            return 1
        elif self[0] < 0 and self[1] > 0:
            return 2
        elif self[0] < 0 and self[1] < 0:
            return 3
        else:
            return 4


class Line:
    """
    A line is a vector + a start cooridinate
    """
    def __init__(self, start: Coordinate, vector: Vector) -> None:
        self.start = start
        self.vector = vector

