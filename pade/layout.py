import numpy as np
import json
from skillbridge import Workspace
import copy

class Coordinate:
    def __init__(self, coord) -> None:
        # Assume subscriptable input
        self.x = np.round(float(coord[0]), decimals=3)
        self.y = np.round(float(coord[1]), decimals=3)

    def to_skill(self):
        return f'{self.x}:{self.y}'

    def to_list(self, decimals=3):
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
        self.array = np.round(self.array, decimals=3)

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
        return self + (-1*other)

    def __mul__(self, other):
        if other is None:
            return None
        return Vector(self.array*other)

    def __truediv__(self, other):
        return Vector(self.array/other)

    def __neg__(self):
        return Vector(-self.array)

    def __str__(self) -> str:
        return f'Vector({self[0]},{self[1]})'

    def __repr__(self) -> str:
        return f'Vector({self[0]},{self[1]})'

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


class Box:
    """
    Arguments: (origin, w, h) or (origin, diagonal) or ('origin', 'opposite_corner') or (diagonal)

    The absolute position of origin will be handled by Pattern when the box is added to it
    """
    def __init__(self, **kwargs) -> None:
        if all([(s in kwargs) for s in ['origin', 'w', 'h']]):
            origin = kwargs['origin']
            w = kwargs['w']
            h = kwargs['h']
            if not isinstance(origin, Coordinate):
                origin = Coordinate(origin)
            self.origin = origin
            self.diagonal = Vector((w, h))
        elif all([(s in kwargs) for s in ['origin', 'diagonal']]):
            origin = kwargs['origin']
            diagonal = kwargs['diagonal']
            if not isinstance(origin, Coordinate):
                origin = Coordinate(origin)
            if not isinstance(diagonal, Vector):
                diagonal = Vector(diagonal)
            self.origin = origin
            self.diagonal = diagonal
        elif all([(s in kwargs) for s in ['origin', 'opposite_corner']]):
            # Initialize by opposite corners
            origin = kwargs['origin']
            opposite_corner = kwargs['opposite_corner']
            if not isinstance(origin, Coordinate):
                origin = Coordinate(origin)
            diagonal = Vector(origin, opposite_corner)
            self.origin = origin
            self.diagonal = diagonal
        elif 'diagonal' in kwargs:
            # Initialize by diagonal only, set origin to (0,0)
            origin = Coordinate((0,0))
            diagonal = kwargs['diagonal']
            if not isinstance(diagonal, Vector):
                diagonal = Vector(diagonal)
            self.origin = origin
            self.diagonal = diagonal


    def __str__(self) -> str:
        return f'Box(origin: {self.origin}, diaginal: {self.diagonal})'

    def __repr__(self) -> str:
        return f'Box(origin: {self.origin}, diaginal: {self.diagonal})'

    def __mul__(self, other):
        if other is None:
            return None
        if isinstance(other, Box):
            # Return Box corresponsing to the intersection of the two boxes
            # Calculated by min of max/max of min
            x_max = min(self.x_max(), other.x_max())
            x_min = max(self.x_min(), other.x_min())
            y_max = min(self.y_max(), other.y_max())
            y_min = max(self.y_min(), other.y_min())
            dx = np.round(x_max - x_min, decimals=3)
            dy = np.round(y_max - y_min, decimals=3)
            if dx > 0 and dy > 0:
                origin = Coordinate((x_min, y_min))
                diagonal = Vector(origin, (x_max, y_max))
                return Box(origin=origin, diagonal=diagonal)
        else:
            raise NotImplementedError()

    def __add__(self, other):
        if other is None:
            return copy.deepcopy(self)
        if isinstance(other, Box):
            overlap = self*other
            self_corners = self.get_all_corners()
            other_corners = other.get_all_corners()
            if overlap is None:
                # If no overlap, return combintion of both
                return Pattern(box_list=[self, other])
            elif self in other:
                # If self is contained in other, return other
                return copy.deepcopy(other)
            elif other in self:
                # If other is contained in self, return self
                return copy.deepcopy(self)
            else:
                # Now there is an overlap, but one is not contained in the other
                # Make a pattern of the parts of other, not containing self
                # and add self to it
                return (other - self) + self
        elif isinstance(other, Pattern):
            # Use the add function of pattern instead
            return other + self
        else:
            raise NotImplementedError()


    def __sub__(self, other):
        if other is None:
            return copy.deepcopy(self)
        if isinstance(other, Box):
            overlap = self*other
            if overlap is None:
                return copy.deepcopy(self)
            elif self in other:
                # If the other covers self completely, self is removed
                # Could alternatively return an empty box?
                return None
            else:
                # If other partially cover self, retun pattern with remaining sections. WIll be 3 boxes at the most
                remainder_box_list = []
                c1 = Coordinate((self.x_min(), self.y_min()))
                c2 = Coordinate((overlap.x_min(), self.y_max()))
                if c2 in self:
                    box = Box(origin=c1, opposite_corner=c2)
                    if box.area() > 0:
                        remainder_box_list.append(box)
                c1 = Coordinate((overlap.x_min(), overlap.y_max()))
                c2 = Coordinate((overlap.x_max(), self.y_max()))
                if c1 in self and c2 in self:
                    box = Box(origin=c1, opposite_corner=c2)
                    if box.area() > 0:
                        remainder_box_list.append(box)
                c1 = Coordinate((overlap.x_min(), self.y_min()))
                c2 = Coordinate((overlap.x_max(), overlap.y_min()))
                if c1 in self and c2 in self:
                    box = Box(origin=c1, opposite_corner=c2)
                    if box.area() > 0:
                        remainder_box_list.append(box)
                c1 = Coordinate((overlap.x_max(), self.y_min()))
                c2 = Coordinate((self.x_max(), self.y_max()))
                if c1 in self:
                    box = Box(origin=c1, opposite_corner=c2)
                    if box.area() > 0:
                        remainder_box_list.append(box)
                return Pattern(box_list=remainder_box_list)
        else:
            raise NotImplementedError()


    def __contains__(self, other):
        if isinstance(other, Coordinate):
            xin = self.x_min() <= other[0] and other[0] <= self.x_max()
            yin = self.y_min() <= other[1] and other[1] <= self.y_max()
            return (xin and yin)
        elif isinstance(other, Box):
            for corner in other.get_all_corners():
                if not corner in self:
                    return False
            return True
        else:
            raise NotImplementedError()


    def is_disjoint(self, other):
        return (self*other == None)


    def get_border(self):
        # Returns list of lines defining the border
        corners = self.get_all_corners()
        lines = []
        for i in range(len(corners)):
            if not i == (len(corners) -1):
                vec = Vector(corners[i], corners[i+1])
            else:
                vec = Vector(corners[i], corners[0])
            lines.append(Line(corners[i], vec))
        return lines


    def w(self):
        return self.diagonal[0]

    def h(self):
        return self.diagonal[1]

    def opposite_corner(self):
        return self.origin + self.diagonal

    def get_all_corners(self):
        return (
            self.origin,
            self.opposite_corner(),
            self.origin + (self.diagonal[0], 0),
            self.origin + (0, self.diagonal[1]),
        )

    def y_max(self):
        return np.max(np.array([c[1] for c in self.get_all_corners()]))

    def y_min(self):
        return np.min(np.array([c[1] for c in self.get_all_corners()]))

    def x_max(self):
        return np.max(np.array([c[0] for c in self.get_all_corners()]))

    def x_min(self):
        return np.min(np.array([c[0] for c in self.get_all_corners()]))

    def upper_right(self):
        return Coordinate((self.x_max(), self.y_max()))

    def upper_left(self):
        return Coordinate((self.x_min(), self.y_max()))

    def lower_left(self):
        return Coordinate((self.x_min(), self.y_min()))

    def lower_right(self):
        return Coordinate((self.x_max(), self.y_min()))

    def center(self):
        return self.origin + self.diagonal/2

    def to_list(self, decimals=3):
        return [self.origin.to_list(decimals=decimals), self.opposite_corner().to_list(decimals=decimals)]

    def set_origin(self, **kwargs):
        if 'origin' in kwargs:
            self.origin = Coordinate(kwargs['origin'])
        elif 'center' in kwargs:
            center = kwargs['center']
            x0 = center[0] - self.w()/2
            y0 = center[1] - self.h()/2
            self.origin = Coordinate((x0, y0))

    def area(self):
        return np.abs(self.diagonal[0] * self.diagonal[1])

    def translate(self, translation, in_place=False):
        """
        Translate the box by a translation vector
        Accepts any subscriptable object as vector
        Returns the translated version of the box
        """
        box = self if in_place else copy.deepcopy(self)
        box.origin = box.origin+translation
        return box

    def rotate(self, angle, rotate_origin=False, in_place=False):
        """
        Rotate box by specified angle
        Returns the rotated version of the box
        """
        box = self if in_place else copy.deepcopy(self)
        # Rotation matrix:
        new_diag = box.diagonal.rotate(angle)
        origin = box.origin
        if rotate_origin:
            o_vec = Vector(box.origin)
            origin = o_vec.rotate(angle).to_coordinate()
        box.origin = origin
        box.diagonal = new_diag
        return box



class Pattern:
    """
    Single layer object holding geometries consisting of several boxes
    Absolute position of box origin is handled when added to pattern
    """
    def __init__(self,  **kwargs) -> None:
        self.layer_name = kwargs.get('layer_name')
        self.purpose = kwargs.get('purpose')
        self.box_list = []
        self.origin = Coordinate((0,0))
        if 'origin' in kwargs:
            self.origin = Coordinate(kwargs['origin'])
        elif 'box_list' in kwargs:
            # If instantiates with a list of boxes, calculate origin as lower left
            self.box_list = kwargs['box_list']
            self.origin = self.lower_left()
        elif 'pattern' in kwargs:
            self.set_pattern(kwargs['pattern'])
            self.origin = self.lower_left()


    def __str__(self) -> str:
        if self.layer_name is None and self.purpose is None and self.origin is None:
            return f"Blank Pattern with {len(self.box_list)} boxes"
        else:
            return f"Pattern {self.layer_name} {self.purpose} at {self.origin} with {len(self.box_list)} boxes"

    def __repr__(self) -> str:
        return f"Pattern {self.layer_name} {self.purpose} at {self.origin} with {len(self.box_list)} boxes"

    def __mul__(self, other):
        if other is None:
            return None
        # Return new patterm describing intersection between patterns
        p = copy.deepcopy(self)
        p.reset_box_list()
        if isinstance(other, Pattern):
            for b1 in self.get_sorted_box_list():
                for b2 in other.get_sorted_box_list():
                    intersection = b1*b2
                    if intersection is not None:
                        # Add intersection to p. This ensures that only non-overlapping region is added
                        p.add_box(intersection, True)
        return p

    def __add__(self, other):
        """
        Do not care about overlap, just append/add the boxes
        """
        new_pattern = copy.deepcopy(self)
        if other is None:
            return new_pattern
        if isinstance(other, Pattern):
            new_pattern.add_pattern(other)
            return new_pattern
        elif isinstance(other, Box):
            new_pattern.add_box(other, absolute_position=True)
            return new_pattern
        else:
            raise NotImplementedError()

    def __sub__(self, other):
        new_pattern = copy.deepcopy(self)
        if other is None:
            return new_pattern
        if isinstance(other, Box):
            # If other is a box, build new pattern from all non-overlapping regions
            new_pattern.reset_box_list()
            for box in self.get_sorted_box_list():
                diff_pattern = box - other
                # Add to avoid overlap
                new_pattern += diff_pattern
            return new_pattern
        elif isinstance(other, Pattern):
            for box in other.get_sorted_box_list():
                diff = self - box
                new_pattern = new_pattern*diff
            return new_pattern
        else:
            raise NotImplementedError()

    def reduce(self):
        """
        Remove all boxes that is completely
        Cannot be done in_place
        """
        new_pattern = copy.deepcopy(self)
        new_pattern.reset_box_list()
        sorted_box_list = self.get_sorted_box_list()
        for i1 in range(0, len(sorted_box_list)):
            b_new = sorted_box_list[i1]
            for i2 in range(0, i1):
                b_existing = sorted_box_list[i2]
                b_new -= b_existing
                if b_new is None:
                    break
            new_pattern += b_new
        return new_pattern

    def area(self):
        area = 0
        # Assume non-overlapping boxes
        for box in self.box_list:
            area += box.area()

    def set_layer(self, layer_name):
        self.layer_name = layer_name

    def set_purpose(self, purpose):
        self.purpose = purpose

    def add_box(self, box, absolute_position=False):
        """
        Add box (adds a copy of the box)
        Parameters:
            absolute_position: bool
                If true, let the box have absolute position, i.e., do not correct by adding self.origin to box.origin.
        """
        if not box is None:
            box_copy = copy.deepcopy(box)
            if not absolute_position:
                box_copy.origin += self.origin
            self.box_list.append(box_copy)

    def add_box_list(self, box_list, absolute_position=False):
        for box in box_list:
            self.add_box(box, absolute_position=absolute_position)

    def get_box_list(self):
        return copy.deepcopy(self.box_list)

    def reset_box_list(self):
        self.box_list = []

    def get_sorted_box_list(self, key='area', order='descending'):
        if key == 'area':
            area_f = lambda b: (b.area())
            reverse = order=='descending'
            return sorted(self.box_list, key=area_f, reverse=reverse)
        else:
            raise NotImplementedError()


    def set_pattern(self, pattern):
        """
        Set Pattern from other pattern object
        """
        self.box_list = pattern.get_box_list()

    def set_origin(self, origin=None):
        if origin is None:
            self.origin = self.lower_left()
        else:
            self.origin = origin

    def add_pattern(self, pattern):
        """
        Add all boxes from other pattern. Do not correct origin
        """
        self.box_list += pattern.get_box_list()

    def y_max(self):
        return np.max(np.array([b.y_max() for b in self.box_list]))

    def y_min(self):
        return np.min(np.array([b.y_min() for b in self.box_list]))

    def x_min(self):
        return np.min(np.array([b.x_min() for b in self.box_list]))

    def x_max(self):
        return np.max(np.array([b.x_max() for b in self.box_list]))

    def upper_right(self):
        return Coordinate((self.x_max(), self.y_max()))

    def upper_left(self):
        return Coordinate((self.x_min(), self.y_max()))

    def lower_left(self):
        return Coordinate((self.x_min(), self.y_min()))

    def lower_right(self):
        return Coordinate((self.x_max(), self.y_min()))

    def center(self):
        """
        Returns center defined as follows.
        """
        x_center = (self.x_max() + self.x_min()) / 2
        y_center = (self.y_max() + self.y_min()) / 2
        return Coordinate((x_center, y_center))

    def w(self):
        return self.x_max() - self.x_min()

    def h(self):
        return self.y_max() - self.y_min()

    def translate(self, translation, in_place=False):
        """
        Translate whole pattern by translating origin and all boxes
        """
        p = self if in_place else copy.deepcopy(self)
        p.origin += translation
        for box in p.box_list:
            box.translate(translation, in_place=True)
        return p

    def enclosure(self, margin=0, **kwargs):
        """
        Returns enclosure around whole region covered by self
        """
        p = Pattern(origin=self.lower_left(), **kwargs)
        p.add_box(Box(origin=self.lower_left()-margin, opposite_corner=self.upper_right()+margin), absolute_position=True)
        return p

    def box_enclosure(self, margin=0, **kwargs):
        """
        Returns enclosure around each box of self
        """
        p = Pattern(**kwargs)
        for box in self.box_list:
            enclosing_box = Box(origin=box.lower_left()-margin, opposite_corner=box.upper_right()+margin)
            p.add_box(enclosing_box, absolute_position=True)
        p.set_origin()
        return p

    def rotate(self, angle, keep_position=True, in_place=False):
        """
        Rotate whole pattern by angle degrees
        keep_position:
            This will conpensate such that the lower left corner remains at the same place
        """
        pattern = self if in_place else copy.deepcopy(self)
        # Lower left before rotation
        p0 = pattern.lower_left()
        for box in pattern.box_list:
            # Rotate both box diagonal and origin vectors
            box.rotate(angle, rotate_origin=True, in_place=True)
        if keep_position:
            # Lower left after rotation
            p1 = pattern.lower_left()
            translation = -Vector(p0, p1)
            pattern.translate(translation, in_place=True)
        return pattern






class Path:
    """
    Path segment. Only straight wire in single layer
    """
    def __init__(self, layer_name, **kwargs) -> None:
        self.layer_name = layer_name
        self.start = kwargs.get('start')
        self.stop = kwargs.get('stop')
        self.width = kwargs.get('width')
        self.begin_style = kwargs.get('begin_style')
        self.end_style = kwargs.get('end_style')


class Route:
    """
    Route. May contain several path segments and vias
    """
    def __init__(self) -> None:
        self.path_list = []
        self.via_list = []

    def __str__(self) -> str:
        return f"Route with {len(self.path_list)} Paths"

    def add_path(self, path):
        self.path_list.append(path)

    def add_via(self, via):
        self.via_list.append(via)




class Via:
    """
    Via. May have multiple rows and columns of vias
    """
    def __init__(self, via_def_name, **kwargs) -> None:
        self.via_def_name = via_def_name
        self.n_rows = kwargs.get('n_rows')
        self.n_cols = kwargs.get('n_cols')
        self.center = kwargs.get('center')

        if 'box' in kwargs:
            self.box = kwargs['box']
            self.center = self.box.center()

        # Index of via spacing rules in tech file parameter list
        # Might be tech-dependent?
        self.via_width_rule_index = 1
        self.via2via_space_rule_index = 5
        self.via2bound_space_rule_index = 6

    def __str__(self) -> str:
        return f"Via {self.via_def_name} with {self.n_rows} and {self.n_cols} columns"

    def parse_tech_file_rules(self, tech_file_param_list):
        # Calculate required number of cols and rows based on box
        self.via_width = tech_file_param_list[self.via_width_rule_index]
        # via2via space is a list. Assume rules for W and H are equal and select first entry
        self.via2via_space = tech_file_param_list[self.via2via_space_rule_index][0]
        # via2bound space is a list. Assume rules for W and H are equal and select first entry
        self.via2bound_space = tech_file_param_list[self.via2bound_space_rule_index][0]

    def get_via_params(self, tech_file_param_list=None, **kwargs):
        if tech_file_param_list is not None:
            self.parse_tech_file_rules(tech_file_param_list)
            via_unit_width = self.via_width + self.via2via_space
            self.n_cols = int((self.box.w() - self.via_width - 2*self.via2bound_space) / via_unit_width) + 1
            self.n_rows = int((self.box.h() - self.via_width - 2*self.via2bound_space) / via_unit_width) + 1

        return [["cutRows", self.n_rows], ["cutColumns", self.n_cols]]



class Port:
    """
    Port on Layout. Generates a figure(rect), net, terminal and a pin
    """
    def __init__(self, name, layer_name, position, **kwargs) -> None:
        self.layer_name = layer_name
        self.name = name
        self.position = Coordinate(position) # center of port
        # set box for pin figure
        if 'box' in kwargs:
            self.box = copy.deepcopy(kwargs['box'])
            self.box_width = self.box.w()
        else:
            self.box_width = kwargs.get('box_width', 0.2)
            self.box = Box(diagonal=(self.box_width, self.box_width))
        self.box.set_origin(center=self.position)

    def __str__(self) -> str:
        return f"Port {self.name} in {self.layer_name} at {self.position}"


class LayoutItem:
    """
    This corresponds to a cell with a layout view in Virtuoso
    """
    def __init__(self, lib_name, cell_name, instance_name, **kwargs) -> None:
        self.lib_name = lib_name
        self.cell_name = cell_name
        self.instance_name = instance_name

        self.set_origin(kwargs.get('origin')) # Origin only applies to instance
        self.set_orientation(kwargs.get('orientation'))
        self.set_parameters(kwargs.get('parameters'))

        self.pattern_list = kwargs.get('pattern_list', [])
        self.instance_list = kwargs.get('instance_list', [])
        self.route_list = kwargs.get('route_list', [])
        self.port_list = kwargs.get('port_list', [])
        self.via_list = kwargs.get('via_list', [])

        self.ws = Workspace.open()
        lib_id = self.ws.dd.get_obj(self.lib_name)
        self.tech_file = self.ws.tech.get_tech_file(lib_id)

    def __str__(self) -> str:
        return f"LayoutItem {self.cell_name} at {self.origin} with {len(self.pattern_list)} Patterns"

    def set_parameters(self, parameters):
        self.parameters = parameters if not parameters is None else {}

    def set_origin(self, origin):
        self.origin = Coordinate(origin) if not origin is None else Coordinate((0,0))

    def set_orientation(self, orientation):
        self.orientation = orientation if not orientation is None else "R0"

    def y_max(self):
        return np.max(np.array([p.y_max() for p in self.pattern_list]))

    def y_min(self):
        return np.min(np.array([p.y_min() for p in self.pattern_list]))

    def x_min(self):
        return np.min(np.array([p.x_min() for p in self.pattern_list]))

    def x_max(self):
        return np.max(np.array([p.x_max() for p in self.pattern_list]))

    def upper_right(self):
        return Coordinate((self.x_max(), self.y_max()))

    def upper_left(self):
        return Coordinate((self.x_min(), self.y_max()))

    def lower_left(self):
        return Coordinate((self.x_min(), self.y_min()))

    def lower_right(self):
        return Coordinate((self.x_max(), self.y_min()))

    def w(self):
        return self.x_max() - self.x_min()

    def h(self):
        return self.y_max() - self.y_min()

    def center(self):
        """
        Returns center defined as follows.
        """
        x_center = (self.x_max() + self.x_min()) / 2
        y_center = (self.y_max() + self.y_min()) / 2
        return Coordinate((x_center, y_center))

    def add_pattern(self, pattern):
        self.pattern_list.append(pattern)

    def add_instance(self, instance):
        """
        Add to instance list and store as attribute
        """
        self.instance_list.append(instance)
        setattr(self, instance.instance_name, instance)

    def add_route(self, route):
        self.route_list.append(route)

    def add_port(self, port: Port):
        """
        Add port to port_list and store as attribute
        """
        self.port_list.append(port)
        setattr(self, port.name, port)

    def add_via(self, via):
        self.via_list.append(via)

    def add_via_from_pattern(self, via_def_name, pattern: Pattern):
        """
        Add vias that fill pattern region
        """
        for box in pattern.box_list:
            via = Via(via_def_name, box=box)
            self.add_via(via)

    def add_enclosure(self, layer_name, purpose, margin=0):
        """
        Add new pattern that enclose self with the specified margin
        """
        p = Pattern(layer_name=layer_name, purpose=purpose, origin=self.lower_left())
        p.add_box(Box(origin=self.lower_left()-margin ,opposite_corner=self.upper_right()+margin), absolute_position=True)
        self.add_pattern(p)
        return p

    def get_parameter_list(self):
        # TODO
        pass

    def print_layout(self, recursive=False):
        """
        Write Layout
        """
        cell_view = self.ws.db.open_cell_view_by_type(self.lib_name, self.cell_name, "layout", "maskLayout", "w")

        # Write instances
        for instance in self.instance_list:
            # TODO: Support parameters
            print(f'Instantiating: {instance}')
            if recursive:
                instance.print_layout(recursive=True)
            self.ws.db.create_inst_by_master_name(cell_view, instance.lib_name, instance.cell_name, 'layout', instance.instance_name, instance.origin.to_list(), instance.orientation)


        # Write patterns
        for pattern in self.pattern_list:
            print(f'Printing: {pattern}')
            for box in pattern.box_list:
                self.ws.db.create_rect(
                    cell_view,
                    [pattern.layer_name, pattern.purpose],
                    box.to_list()
                    )

        # Write routes
        for route in self.route_list:
            print(f'Printing: {route}')
            for path in route.path_list:
                self.ws.db.create_path_seg(cell_view, path.layer_name, path.start.to_list(), path.stop.to_list(), path.width, path.begin_style, path.end_style)

        # Write ports
        for port in self.port_list:
            print(f'Printing: {port}')
            fig = self.ws.db.create_rect(cell_view, [port.layer_name, 'drawing'], port.box.to_list())
            net = self.ws.db.create_net(cell_view, port.name)
            self.ws.db.create_term( net, port.name, "inputOutput")
            self.ws.db.create_pin(net, fig)
            self.ws.db.create_label(cell_view, [port.layer_name, 'label'], port.position.to_list(), port.name, "centerCenter", "R0", "stick", port.box_width/5)

        # Write Vias
        print(f'Printing {len(self.via_list)} vias')
        for via in self.via_list:
            # Use tech file to find via rules
            via_def_id = self.ws.tech.find_via_def_by_name(self.tech_file, via.via_def_name)
            via_params = via.get_via_params(self.ws.db.get(via_def_id, 'params'))
            self.ws.db.create_via(cell_view, via_def_id, via.center.to_list(), "R0", via_params)

        self.ws.db.save(cell_view)










