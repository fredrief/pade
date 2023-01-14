from pade.layout.geometry import *
from pade.layout.pattern import Box
from pade.schematic import Terminal
from inform import warn
import numpy as np
import copy
from skillbridge import Workspace

class Path:
    """
    Path segment. Only straight wire in single layer
    """
    def __init__(self, layer, start, **kwargs) -> None:
        self.layer = layer
        self.start = start
        if isinstance(start, Port):
            self.start = start.position
        self.stop = kwargs.get('stop')
        self.width = kwargs.get('width')
        self.begin_style = kwargs.get('begin_style', 'extend')
        self.end_style = kwargs.get('end_style', 'extend')
        self.net = kwargs.get('net')

        if 'dy' in kwargs:
            dy = kwargs['dy']
            self.stop = self.start + (0, dy)
        if 'dx' in kwargs:
            dx = kwargs['dx']
            self.stop = self.start + (dx, 0)

    def __str__(self):
        return f"Path in {self.layer} from {self.start} to {self.stop}"

    def __repr__(self) -> str:
        return self.__str__()

    def set_begin_style(self, style):
        self.begin_style = style

    def set_end_style(self, style):
        self.end_style = style

    def get_box(self):
        if self.start[0] == self.stop[0]:
            # In this case the path is vertical
            c1 = self.start - (self.width/2, 0)
            c2 = self.stop + (self.width/2, 0)
            return Box(origin=c1, opposite_corner=c2)
        else:
            # In this case the path is horizontal
            c1 = self.start - (0, self.width/2)
            c2 = self.stop + (0, self.width/2)
            return Box(origin=c1, opposite_corner=c2)

    def set_net(self, net_name):
        self.net = net_name


class Route:
    """
    Route. May contain several path segments and vias
    """
    def __init__(self, start, stop, how, **kwargs) -> None:
        self.path_list = []
        self.via_list = []
        self.width = None
        self.layer = None
        self.offset = kwargs.get('offset', 0)
        self.offset_end = kwargs.get('offset_end', 0)
        self.net = kwargs.get('net')
        self.start_port = None
        self.end_port = None
        self.tech_file = kwargs.get('tech_file')
        if isinstance(start, Port):
            # If port, use center
            self.start = start.box.center()
            self.start_port = start
            # Use start port box width(height) as routing width
            self.width = min(start.box.w(), start.box.h())
            self.layer = start.layer
        else:
            self.start = start

        if isinstance(stop, Port):
            # If port, use center
            self.stop = stop.box.center()
            self.end_port = stop
            if self.width is None or self.layer is None:
                # Use stop port box width(height) as routing width
                self.width = min(stop.box.w(), stop.box.h())
                self.layer = stop.layer
        else:
            self.stop = stop

        # Possibility for overwriting width and layer:
        self.width = kwargs.get('width', self.width)
        self.layer = kwargs.get('layer', self.layer)

        if self.width is None or self.layer is None:
            raise ValueError('Route width and layer must be specified if start is not a Port')

        if how == '|-':
            self.route_vh()
        elif how == '-|':
            self.route_hv()
        elif how == '-':
            self.route_h()
        elif how == '|':
            self.route_v()
        else:
            warn('Route method not recognized')

        self.handle_path_style(**kwargs)

        # Add vias
        # TODO: Do this automatically. Currently must be done manually
        # Requires:
        # - Find names of required vias, should look in the tech file
        # - determine number of rows and cols for vias
        # if not self.start_port is None and self.tech_file is not None:
        #     if self.layer != self.start_port.layer:
        #         via_def_name = Via.find_via_def_name_from_layer_name(self.tech_file, self.start_port.layer, self.layer)


        # Assign net to path segments if applicable
        if self.net is not None:
            for p in self.path_list:
                p.set_net(self.net)


    def __str__(self) -> str:
        return f"Route with {len(self.path_list)} Paths"

    def __repr__(self) -> str:
        return self.__str__()

    def add_path(self, path):
        self.path_list.append(path)

    def add_via_start(self, via_name_list, n_rows=1, n_cols=2):
        p = self.path_list[0]
        if p.begin_style == 'extend':
            center = p.start
        elif p.begin_style == 'truncate':
            direction = Vector(p.start, p.stop).normalize()
            center = p.start + direction*(p.width/2)

        for via_name in via_name_list:
            via = Via(via_name, center=center, n_rows=n_rows, n_cols=n_cols)
            self._add_via(via)

    def add_via_end(self, via_name_list, n_rows=1, n_cols=2):
        p = self.path_list[-1]
        if p.end_style == 'extend':
            center = p.stop
        elif p.end_style == 'truncate':
            direction = Vector(p.start, p.stop).normalize()
            center = p.stop - direction*(p.width/2)

        center = self.path_list[-1].stop
        for via_name in via_name_list:
            via = Via(via_name, center=center, n_rows=n_rows, n_cols=n_cols)
            self._add_via(via)

    def _add_via(self, via):
        self.via_list.append(via)

    def route_vh(self):
        """
        Route vertically, then horisontally
        """
        # First handle offset
        r_start = self.start
        r_stop = self.stop
        if self.offset != 0:
            # As this route starts vertically, assume offset is horisontally
            p0 = Path(self.layer, self.start, dx=self.offset, width=self.width)
            self.add_path(p0)
            # Update r_start
            r_start += (self.offset, 0)

        p_end = None
        if self.offset_end != 0:
            # As this route ends horisontally, assume end offset is vertical
            p_end = Path(self.layer, r_stop+(0, self.offset_end), dy=-self.offset_end, width=self.width)
            # Update r_stop
            r_stop += (0, self.offset_end)

        vector = r_stop - r_start
        dy=vector[1]
        dx=vector[0]
        p1 = Path(self.layer, r_start, dy=dy, width=self.width)
        if not dy == 0:
            self.add_path(p1)
        if not dx == 0:
            p2 = Path(self.layer, p1.stop, dx=dx, width=self.width)
            self.add_path(p2)
        if not p_end is None:
            self.add_path(p_end)

    def route_hv(self):
        """
        Route horisontally, then vertically
        """
        r_start = self.start
        r_stop = self.stop

        # First handle offset
        if self.offset != 0:
            # As this route starts horisontally, assume self.offset is vertically
            p0 = Path(self.layer, r_start, dy=self.offset, width=self.width)
            self.add_path(p0)
            # Update r_start
            r_start += (0, self.offset)

        p_end = None
        if self.offset_end != 0:
            # As this route ends vertically, assume end offset is horisontal
            p_end = Path(self.layer, r_stop+(self.offset_end,0), dx=-self.offset_end, width=self.width)
            # Update r_stop
            r_stop += (self.offset_end, 0)

        vector = r_stop - r_start
        dy=vector[1]
        dx=vector[0]
        # dx = dx  - self.width/2 if dx > 0 else dx + self.width/2
        p1 = Path(self.layer, r_start, dx=dx, width=self.width)
        if not dx == 0:
            self.add_path(p1)
        if not dy == 0:
            p2 = Path(self.layer, p1.stop, dy=dy, width=self.width)
            self.add_path(p2)

        if not p_end is None:
            self.add_path(p_end)

    def route_h(self):
        """
        Horizontal route.
        """
        dx = self.stop[0] - self.start[0]
        self.add_path(Path(self.layer, self.start, dx=dx, width=self.width))

    def route_v(self):
        """
        Vertical route.
        """
        dy = self.stop[1] - self.start[1]
        self.add_path(Path(self.layer, self.start, dy=dy, width=self.width))

    def handle_path_style(self, **kwargs):
        # Add begin/end styles
        if 'begin_style' in kwargs:
            self.path_list[0].set_begin_style(kwargs['begin_style'])
        if 'end_style' in kwargs:
            self.path_list[-1].set_end_style(kwargs['end_style'])

    def end(self):
        return self.path_list[-1].stop



class Via:
    """
    Via. May have multiple rows and columns of vias
    """
    @staticmethod
    def find_via_def_name_from_layer_name(tech_file, layer1_name, layer2_name):
        for via_def in tech_file.via_defs:
            if via_def.layer1.name == layer1_name and via_def.layer2.name == layer2_name:
                return via_def.name

    def __init__(self, via_def_name, **kwargs) -> None:
        self.via_def_name = via_def_name
        self.n_rows = kwargs.get('n_rows')
        self.n_cols = kwargs.get('n_cols')
        self.center = kwargs.get('center')

        self.box = kwargs.get('box')
        if self.box is not None:
            self.center = self.box.center()

        # Index of via spacing rules in tech file parameter list
        # Might be tech-dependent?
        self.via_width_rule_index = 1
        self.via2via_space_rule_index = 5
        self.via2bound_space_rule_index = 6

    def __str__(self) -> str:
        return f"Via {self.via_def_name} with {self.n_rows} and {self.n_cols} columns"

    def __repr__(self) -> str:
        return self.__str__()

    def parse_tech_file_rules(self, tech_file_param_list):
        # Calculate required number of cols and rows based on box
        self.via_width = tech_file_param_list[self.via_width_rule_index]
        # via2via space is a list. Assume rules for W and H are equal and select first entry
        self.via2via_space = tech_file_param_list[self.via2via_space_rule_index][0]
        # via2bound space is a list. Assume rules for W and H are equal and select first entry
        self.via2bound_space = tech_file_param_list[self.via2bound_space_rule_index][0]

    def get_via_params(self, tech_file_param_list=None, **kwargs):
        if tech_file_param_list is not None and self.box is not None:
            self.parse_tech_file_rules(tech_file_param_list)
            via_unit_width = self.via_width + self.via2via_space
            self.n_cols = int((self.box.w() - self.via_width - 2*self.via2bound_space) / via_unit_width) + 1
            self.n_rows = int((self.box.h() - self.via_width - 2*self.via2bound_space) / via_unit_width) + 1

        return [["cutRows", self.n_rows], ["cutColumns", self.n_cols]]



class Port:
    """
    Port on Layout. Generates a figure(rect), net, terminal and a pin
    """
    def __init__(self, name, *args, **kwargs) -> None:
        if isinstance(name, Terminal):
            self.name = name.name
        else:
            self.name = name

        if len(args) == 1 and isinstance(args[0], Route):
            route = args[0]
            self.layer = route.layer
            path = route.path_list[0]
            self.box = path.get_box()
            self.position = self.box.center()
        elif len(args) == 1 and isinstance(args[0], Port):
            port = args[0]
            self.layer = port.layer
            self.box = port.box
            self.position = self.box.center()
        elif len(args) == 2 and isinstance(args[-1], Box):
            self.layer = args[0]
            self.box = copy.deepcopy(args[-1])
            self.position = self.box.center()
        elif len(args) == 2 and not isinstance(args[-1], Box):
            self.layer = args[0]
            self.position = args[1]
            box_width = kwargs.get('box_width', 0.2)
            self.box = Box(diagonal=(box_width, box_width))
        elif len(args) == 3:
            # Assume layer, position and box
            self.layer = args[0]
            self.position = args[1]
            self.box = args[2]
        else:
            raise ValueError('Invalid input arguments')
        self.box.set_origin(center=self.position)

    def __str__(self) -> str:
        return f"Port {self.name} in {self.layer} at {self.position}"

    def __repr__(self) -> str:
        return self.__str__()

    def __sub__(self, other):
        if isinstance(other, Port):
            return Vector(other.position, self.position)
        else:
            raise NotImplementedError()


    def translate(self, translation):
        self.position += translation
