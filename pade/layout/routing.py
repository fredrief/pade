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
        # Set layer, purpose pair
        self.layer = layer
        self.purpose = kwargs.get('purpose', 'drawing')

        if isinstance(start, Port):
            self.start = start.position
        else:
            self.start = Coordinate(start)
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

        # used only when begin or end style are set to custom
        # list( n_beginLeftDiagExt n_beginRightDiagExt n_beginRightHalfWidth n_endLeftDiagExt n_endRightDiagExt n_endRightHalfWidth)
        self.ext_value_list = kwargs.get('ext_value_list')


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
        self.start_port = None
        self.end_port = None
        self.tech_file = kwargs.get('tech_file')
        self.purpose = kwargs.get('purpose', 'drawing')
        self.ncvias = kwargs.get('ncvias') # Corner vias
        if isinstance(start, Port):
            # If port, use center
            self.start = start.box.center()
            self.start_port = start
            # Use start port box width(height) as routing width
            self.width = min(start.box.w(), start.box.h())
            self.layer = start.layer
        elif isinstance(start, Path):
            self.start = start.get_box().center()
            self.layer = start.layer
            self.width = min(start.get_box().w(), start.get_box().h())
        elif isinstance(start, Box):
            self.start = start.center()
        elif isinstance(start, Route):
            self.start = start.path_list[0].get_box().center()
        else:
            self.start = Coordinate(start)

        if isinstance(stop, Port):
            # If port, use center
            self.stop = stop.box.center()
            self.end_port = stop
            if self.width is None or self.layer is None:
                # Use stop port box width(height) as routing width
                self.width = min(stop.box.w(), stop.box.h())
                self.layer = stop.layer
        elif isinstance(stop, Path):
            self.stop = stop.get_box().center()
        elif isinstance(stop, Route):
            self.stop = stop.path_list[0].get_box().center()
        elif isinstance(stop, Box):
            self.stop = stop.center()
        else:
            self.stop = Coordinate(stop)

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
        elif how == '-|-':
            self.path_len_list = kwargs['path_len_list']
            self.route_custom_h()
        elif how == '|-|':
            self.path_len_list = kwargs['path_len_list']
            self.route_custom_v()
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

        # vias = kwargs.get('vias', [])
        # start_vias = kwargs.get('start_vias', vias)
        # end_vias = kwargs.get('end_vias', vias)

        # for via_name in start_vias:
        #     if self.start_port is None:
        #         raise ValueError('Can only add vias if start is a port')
        #     via = Via(via_name, box=self.start_port.box)
        #     self._add_via(via)

        # for via_name in end_vias:
        #     if self.end_port is None:
        #         raise ValueError('Can only add vias if end is a port')
        #     via = Via(via_name, box=self.end_port.box)
        #     self._add_via(via)


    def __str__(self) -> str:
        return f"Route with {len(self.path_list)} Paths"

    def __repr__(self) -> str:
        return self.__str__()

    def __getitem__(self, key):
        return self.path_list[key]

    def add_path(self, path):
        self.path_list.append(path)

    def add_via_start(self, via_name_list, n_rows=1, n_cols=2, **via_attr):
        p = self.path_list[0]
        if p.begin_style == 'extend':
            center = p.start
        elif p.begin_style == 'truncate':
            # direction = Vector(p.start, p.stop).normalize()
            # center = p.start + direction*(p.width/2)
            center = p.start
        else:
            raise ValueError(f'Unknown path begin style: {p.begin_style}')

        for via_name in via_name_list:
            via = Via(via_name, center=center, n_rows=n_rows, n_cols=n_cols, via_attr=via_attr)
            self._add_via(via)

    def add_via_end(self, via_name_list, n_rows=1, n_cols=2, **via_attr):
        p = self.path_list[-1]
        if p.end_style == 'extend':
            center = p.stop
        elif p.end_style == 'truncate':
            direction = Vector(p.start, p.stop).normalize()
            center = p.stop - direction*(p.width/2)
        else:
            raise ValueError(f'Unknown path end style: {p.end_style}')

        center = self.path_list[-1].stop
        for via_name in via_name_list:
            via = Via(via_name, center=center, n_rows=n_rows, n_cols=n_cols, via_attr=via_attr)
            self._add_via(via)

    def _add_via(self, via):
        self.via_list.append(via)

    def get_layer(self, index=0):
        if isinstance(self.layer, str):
            return self.layer
        try:
            return self.layer[index]
        except:
            return self.layer

    def add_corner_via(self, pos, orient):
        try:
            if self.ncvias is None:
                nrows = 2 if orient == 'v' else 1
                ncols = 2 if orient == 'h' else 1
            else:
                nrows = ncols = self.ncvias
            l0 = int(self.layer[0][-1])
            l1 = int(self.layer[1][-1])
            m1 = np.max((l0, l1))
            m0 = np.min((l0, l1))
            via_name = f'M{m1}_M{m0}'
            if m1 == 5:
                via_name = 'TM_M4'
                if self.ncvias is None:
                    nrows = self.width if self.width > 2 else 2
                else:
                    nrows = self.ncvias
                ncols = nrows
                via = Via(via_name, center=pos, n_rows=nrows, n_cols=ncols, via_attr={'cutSpacing': [0.54, 0.54]})
                self._add_via(via)
                return
            via = Via(via_name, center=pos, n_rows=nrows, n_cols=ncols)
            self._add_via(via)
        except:
            return

    def route_vh(self):
        """
        Route vertically, then horisontally
        """
        # First handle offset
        r_start = self.start
        r_stop = self.stop
        if self.offset != 0:
            if np.abs(self.offset) > 1.0:
                # As this route starts vertically, assume offset is horisontally
                p0 = Path(self.get_layer(1), self.start, dx=self.offset, width=self.width, purpose=self.purpose)
                self.add_path(p0)
                # Update r_start
                r_start += (self.offset, 0)
                # Add corner via
                self.add_corner_via(p0.stop, 'v')
            else:
                # As this route starts vertically, assume offset is horisontally
                p0 = Path(self.get_layer(0), self.start, dx=self.offset, width=self.width, purpose=self.purpose)
                self.add_path(p0)
                # Update r_start
                r_start += (self.offset, 0)

        p_end = None
        if self.offset_end != 0:
            # As this route ends horisontally, assume end offset is vertical
            p_end = Path(self.get_layer(0), r_stop+(0, self.offset_end), dy=-self.offset_end, width=self.width, purpose=self.purpose)
            # Update r_stop
            r_stop += (0, self.offset_end)
            # Add corner via
            self.add_corner_via(p_end.start, 'h')

        vector = r_stop - r_start
        dy=vector[1]
        dx=vector[0]
        p1 = Path(self.get_layer(0), r_start, dy=dy, width=self.width, purpose=self.purpose)
        if not dy == 0:
            self.add_path(p1)
            # Add corner via
            self.add_corner_via(p1.stop, 'v')
        if not dx == 0:
            p2 = Path(self.get_layer(1), p1.stop, dx=dx, width=self.width, purpose=self.purpose)
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
            if np.abs(self.offset) > 1.0:
                # As this route starts horisontally, assume self.offset is vertically
                p0 = Path(self.get_layer(1), r_start, dy=self.offset, width=self.width, purpose=self.purpose)
                self.add_path(p0)
                # Update r_start
                r_start += (0, self.offset)
                # Add corner via
                self.add_corner_via(p0.stop, 'v')
            else:
                # As this route starts horisontally, assume self.offset is vertically
                p0 = Path(self.get_layer(0), r_start, dy=self.offset, width=self.width, purpose=self.purpose)
                self.add_path(p0)
                # Update r_start
                r_start += (0, self.offset)

        p_end = None
        if self.offset_end != 0:
            # As this route ends vertically, assume end offset is horisontal
            p_end = Path(self.get_layer(0), r_stop+(self.offset_end,0), dx=-self.offset_end, width=self.width, purpose=self.purpose)
            # Update r_stop
            r_stop += (self.offset_end, 0)
            # Add corner via
            self.add_corner_via(p_end.start, 'h')

        vector = r_stop - r_start
        dy=vector[1]
        dx=vector[0]
        # dx = dx  - self.width/2 if dx > 0 else dx + self.width/2
        p1 = Path(self.get_layer(0), r_start, dx=dx, width=self.width, purpose=self.purpose)
        if not dx == 0:
            self.add_path(p1)
            # Add corner via
            self.add_corner_via(p1.stop, 'v')
        if not dy == 0:
            p2 = Path(self.get_layer(1), p1.stop, dy=dy, width=self.width, purpose=self.purpose)
            self.add_path(p2)

        if not p_end is None:
            self.add_path(p_end)

    def route_h(self):
        """
        Horizontal route.
        """
        r_start = self.start
        # First handle offset
        if self.offset != 0:
            # As this route starts horisontally, assume self.offset is vertically
            p0 = Path(self.get_layer(0), r_start, dy=self.offset, width=self.width, purpose=self.purpose)
            self.add_path(p0)
            # Update r_start
            r_start += (0, self.offset)

        r_stop = Coordinate((self.stop[0], r_start[1]))
        self.stop = r_stop

        dx = self.stop[0] - r_start[0]
        if dx != 0:
            self.add_path(Path(self.get_layer(0), r_start, dx=dx, width=self.width, purpose=self.purpose))

    def route_v(self):
        """
        Vertical route.
        """
        r_start = self.start
        if self.offset != 0:
            # As this route starts vertically, assume offset is horisontally
            p0 = Path(self.get_layer(0), self.start, dx=self.offset, width=self.width, purpose=self.purpose)
            self.add_path(p0)
        # Update r_start
        r_start += (self.offset, 0)

        r_stop = Coordinate((r_start[0], self.stop[1]))
        self.stop = r_stop

        dy = self.stop[1] - r_start[1]
        if dy != 0:
            self.add_path(Path(self.get_layer(0), r_start, dy=dy, width=self.width, purpose=self.purpose))

    def route_custom_h(self):
        """
        Custom route, start horisontally
        """
        c0 = self.start
        go_h = True # Starts horisontally
        for path_len in self.path_len_list:
            if go_h:
                self.add_path(Path(self.get_layer(0), c0, dx=path_len, width=self.width, purpose=self.purpose))
                c0 += (path_len, 0)
            else:
                self.add_path(Path(self.get_layer(0), c0, dy=path_len, width=self.width, purpose=self.purpose))
                c0 += (0, path_len)
            go_h = not go_h

        # Finally, go to end
        if go_h:
            dx = self.stop[0] - c0[0]
            if dx != 0:
                self.add_path(Path(self.get_layer(0), c0, dx=dx, width=self.width, purpose=self.purpose))
        else:
            dy = self.stop[1] - c0[1]
            if dy != 0:
                self.add_path(Path(self.get_layer(0), c0, dy=dy, width=self.width, purpose=self.purpose))

    def route_custom_v(self):
        """
        Custom route, start vertically
        """
        c0 = self.start
        go_h = False # Starts vertically
        for path_len in self.path_len_list:
            if go_h:
                self.add_path(Path(self.get_layer(0), c0, dx=path_len, width=self.width, purpose=self.purpose))
                c0 += (path_len, 0)
            else:
                self.add_path(Path(self.get_layer(0), c0, dy=path_len, width=self.width, purpose=self.purpose))
                c0 += (0, path_len)
            go_h = not go_h

        # Finally, go to end
        if go_h:
            dx = self.stop[0] - c0[0]
            if dx != 0:
                self.add_path(Path(self.get_layer(0), c0, dx=dx, width=self.width, purpose=self.purpose))
        else:
            dy = self.stop[1] - c0[1]
            if dy != 0:
                self.add_path(Path(self.get_layer(0), c0, dy=dy, width=self.width, purpose=self.purpose))


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

        port = kwargs.get('port')
        if port is not None:
            self.box = port.box
            self.center = port.box.center()

        self.via_attr = kwargs.get('via_attr', {})

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
        # Overwrite if given as viaAttr:
        if 'cutSpacing' in self.via_attr:
            self.via2via_space = self.via_attr['cutSpacing'][0]
        # via2bound space is a list. Assume rules for W and H are equal and select first entry
        self.via2bound_space = tech_file_param_list[self.via2bound_space_rule_index][0]

    def get_via_params(self, tech_file_param_list=None):
        via_param_list = []
        if tech_file_param_list is not None and self.box is not None:
            self.parse_tech_file_rules(tech_file_param_list)
            via_unit_width = self.via_width + self.via2via_space
            self.n_cols = int((self.box.w() - self.via_width - 2*self.via2bound_space) / via_unit_width) + 1

            self.n_rows = int((self.box.h() - self.via_width - 2*self.via2bound_space) / via_unit_width) + 1

        via_param_list = [
            ["cutRows", self.n_rows],
            ["cutColumns", self.n_cols],
            ]

        for key, value in self.via_attr.items():
            via_param_list.append([key, value])

        return via_param_list



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
        elif len(args) == 1 and isinstance(args[0], Path):
            path = args[0]
            self.layer = path.layer
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
