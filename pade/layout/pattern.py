from pade.layout.geometry import Coordinate, Vector
import numpy as np
import copy

class Box:
    """
    Arguments: [[x0, y0], [x1, y1]] or [x0, y0], [x1, y1] or (origin, w, h) or (origin, diagonal) or ('origin', 'opposite_corner') or (diagonal)

    The absolute position of origin will be handled by Pattern when the box is added to it
    """
    def __init__(self, *args, **kwargs) -> None:
        if len(args) == 1:
            # Assume args is [[x0, y0], [x1, y1]]
            origin = Coordinate(args[0][0])
            opposite_corner = Coordinate(args[0][1])
            diagonal = Vector(origin, opposite_corner)
            self.origin = origin
            self.diagonal = diagonal
        elif len(args) == 2:
            # Assume args is [x0, y0], [x1, y1]
            origin = Coordinate(args[0])
            opposite_corner = Coordinate(args[1])
            diagonal = Vector(origin, opposite_corner)
            self.origin = origin
            self.diagonal = diagonal
        elif all([(s in kwargs) for s in ['origin', 'w', 'h']]):
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
        elif all([(s in kwargs) for s in ['center', 'diagonal']]):
            diagonal = kwargs['diagonal']
            if not isinstance(diagonal, Vector):
                diagonal = Vector(diagonal)
            self.diagonal = diagonal
            self.set_origin(center=kwargs['center'])
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

        else:
            raise ValueError('Invalid arguments for Box')


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
            dx = np.round(x_max - x_min, decimals=2)
            dy = np.round(y_max - y_min, decimals=2)
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
        return np.abs(self.diagonal[0])

    def h(self):
        return np.abs(self.diagonal[1])

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

    def center_left(self):
        return self.lower_left() + (0, self.h()/2)

    def center_right(self):
        return self.lower_right() + (0, self.h()/2)

    def center_top(self):
        return self.upper_left() + (self.w()/2, 0)

    def center_bottom(self):
        return self.lower_left() + (self.w()/2, 0)

    def to_list(self, decimals=3):
        return [self.origin.to_list(decimals=decimals), self.opposite_corner().to_list(decimals=decimals)]

    def set_origin(self, **kwargs):
        if 'origin' in kwargs:
            self.origin = Coordinate(kwargs['origin'])
        elif 'center' in kwargs:
            center = kwargs['center']
            x0 = center[0] - self.diagonal[0]/2
            y0 = center[1] - self.diagonal[1]/2
            self.origin = Coordinate((x0, y0))

    def set_center(self, center, in_place=False):
        translation = Vector(self.center(), center)
        new_box = self.translate(translation, in_place=in_place)
        return new_box


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
        self.layer = kwargs.get('layer')
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
        if self.layer is None and self.purpose is None and self.origin is None:
            return f"Blank Pattern with {len(self.box_list)} boxes"
        else:
            return f"Pattern {self.layer} {self.purpose} at {self.origin} with {len(self.box_list)} boxes"

    def __repr__(self) -> str:
        return f"Pattern {self.layer} {self.purpose} at {self.origin} with {len(self.box_list)} boxes"

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

    def set_layer(self, layer):
        self.layer = layer

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
        return box_copy

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
