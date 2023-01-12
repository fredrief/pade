from pade.layout.geometry import *
from pade.layout.pattern import *
from pade.layout.routing import *
from pade.schematic import Cell
from pade.utils import num2string
import numpy as np
from skillbridge import Workspace
from inform import warn

class LayoutItem:
    """
    This corresponds to a cell with a layout view in Virtuoso
    """
    def __init__(self, lib_name, cell_name, instance_name, **kwargs) -> None:
        self.lib_name = lib_name
        self.cell_name = cell_name
        self.instance_name = instance_name

        self.origin = kwargs.get('origin', Coordinate((0,0)))
        self.set_orientation(kwargs.get('orientation'))

        self.pattern_list = kwargs.get('pattern_list', [])
        self.instance_list = kwargs.get('instance_list', [])
        self.route_list = kwargs.get('route_list', [])
        self.port_list = kwargs.get('port_list', [])
        self.via_list = kwargs.get('via_list', [])

        self.ws = Workspace.open()
        lib_id = self.ws.dd.get_obj(self.lib_name)
        self.tech_file = self.ws.tech.get_tech_file(lib_id)
        self.cell_view = None

    def __str__(self) -> str:
        return f"LayoutItem {self.cell_name} at {self.origin} with {len(self.pattern_list)} Patterns"

    def set_origin(self, origin):
        old_origin = self.origin
        self.origin = Coordinate(origin)
        # Update origin for ports
        translation = Coordinate(origin) - old_origin
        for port in self.port_list:
            port.translate(translation)

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

    def add_box(self, box, layer, purpose, margin=0):
        pattern = Pattern(layer=layer, purpose=purpose, box_list=[box])
        if margin != 0:
            pattern = pattern.enclosure(margin, layer=layer, purpose=purpose)
        self.pattern_list.append(pattern)

    def add_instance(self, instance):
        """
        Add to instance list and store as attribute
        """
        self.instance_list.append(instance)
        setattr(self, instance.instance_name, instance)

    def add_route(self, route):
        self.route_list.append(route)

    def add_multiple_routes(self, route_list):
        for route in route_list:
            self.add_route(route)

    def add_port(self, port: Port):
        """
        Add port to port_list and store as attribute
        """
        self.port_list.append(port)
        setattr(self, port.name, port)

    def add_via(self, via):
        self.via_list.append(via)

    def add_via_from_pattern(self, via_def_name, pattern: Pattern, margin=0):
        """
        Add vias that fill pattern region
        """
        for box in pattern.box_list:
            if box.h() > box.w():
                # If taller than wide, subtract margin from y component of diagonal
                new_diag = box.diagonal - Vector([0, 2*margin])
            else:
                new_diag = box.diagonal - Vector([2*margin, 0])
            center = box.center()
            new_box = Box(center=center, diagonal=new_diag)
            via = Via(via_def_name, box=new_box)
            self.add_via(via)

    def add_enclosure(self, layer, purpose, margin=0):
        """
        Add new pattern that enclose self with the specified margin

        Works for generated layout, does not check instances in cell_view
        """
        p = Pattern(layer=layer, purpose=purpose, origin=self.lower_left())
        p.add_box(Box(origin=self.lower_left()-margin ,opposite_corner=self.upper_right()+margin), absolute_position=True)
        self.add_pattern(p)
        return p

    def has_something_to_print(self):
        # If all lists are empty, return False
        return any([len(l)!=0 for l in [
            self.instance_list,
            self.pattern_list,
            self.port_list,
            self.route_list,
            self.via_list
            ]])

    def get_unique_instance_list(self):
        inst_list = []
        for inst in self.instance_list:
            if not any([i2.cell_name == inst.cell_name for i2 in inst_list]):
                inst_list.append(inst)
        return inst_list

    # -----------------------------
    # Skill interaction functions
    # -----------------------------
    def open_layoutview(self, mode='w'):
        self.cell_view = self.ws.db.open_cell_view_by_type(self.lib_name, self.cell_name, "layout", "maskLayout", mode)

    def add_ring(self, width, margin, layer):
        if self.cell_view is None:
            raise RuntimeError('Cannot add ring because cell_view is None')
        b_box = self.cell_view.b_box
        bounding_box = Box(origin=b_box[0], opposite_corner=b_box[1])
        bb_pattern = Pattern(box_list=[bounding_box])
        p1 = bb_pattern.enclosure(margin=margin)
        p2 = bb_pattern.enclosure(margin=margin+width)
        ring_pattern = Pattern(layer=layer, purpose='drawing', pattern=p2-p1)

        # Add pattern and return for reference
        self.add_pattern(ring_pattern)
        return ring_pattern




    def print_layout(self, recursive=False):
        """
        Write Layout
        """
        if not self.has_something_to_print():
            return

        if recursive:
            for inst in self.get_unique_instance_list():
                inst.print_layout(recursive=True)

        # Write instances
        for instance in self.instance_list:
            print(f'Instantiating: {instance}')
            self.print_instance(instance)

        # Write patterns
        for pattern in self.pattern_list:
            print(f'Printing: {pattern}')
            self.print_pattern(pattern)

        # Write routes
        for route in self.route_list:
            print(f'Printing: {route}')
            self.print_route(route)

        # Write ports
        for port in self.port_list:
            print(f'Printing: {port}')
            self.print_port(self, port)

        # Write Vias
        print(f'Printing {len(self.via_list)} vias')
        for via in self.via_list:
            self.print_via(via)

    def flush(self):
        """
        Remove all items from lists
        """
        self.pattern_list = []
        self.instance_list = []
        self.route_list = []
        self.port_list = []
        self.via_list = []

    def save(self):
        self.ws.db.save(self.cell_view)

    def print_instance(self, instance, print_schematic=False):
        """
        This instantiates the LayoutItem in the layout cell view. The instance ID is atored as an attribute
        """
        # Add instance to instance list if not already in it
        # if not instance in self.instance_list:
        #     self.add_instance(instance)
        if self.cell_view is None:
            self.open_layoutview()

        # TODO: Handle the case when layout master does not exist for instance! (is this still needed?)


        instance_id = self.ws.db.create_inst_by_master_name(self.cell_view, instance.lib_name, instance.cell_name, 'layout', instance.instance_name, instance.origin.to_list(), instance.orientation)

        if instance_id.master is None and False:
            # I am not sure if this will be needed
            # The master does not exist, create it and try to open again
            instance.print_layout()
            instance_id = self.ws.db.create_inst_by_master_name(self.cell_view, instance.lib_name, instance.cell_name, 'layout', instance.instance_name, instance.origin.to_list(), instance.orientation)

        lay_inst = LayoutInstance(instance_id, origin=instance.origin)
        return lay_inst

    def print_pattern(self, pattern):
        for box in pattern.box_list:
            self.ws.db.create_rect(
                self.cell_view,
                [pattern.layer, pattern.purpose],
                box.to_list()
                )

    def print_route(self, route):
        # Add route to routlist if not already in list
        # if not route in self.route_list:
        #     self.add_route(route)
        for path in route.path_list:
            self.print_path(path)
        for via in route.via_list:
            self.print_via(via)

    def print_path(self, path):
        path_id = self.ws.db.create_path_seg(self.cell_view, path.layer, path.start.to_list(), path.stop.to_list(), path.width, path.begin_style, path.end_style)
        # Assign net
        if path.net is not None:
            # Create the net in cell_view (If it does not already exist)
            net = self.ws.db.create_net(self.cell_view, path.net)
            # Assign the net to the path seg
            self.ws.db.add_fig_to_net(path_id, net)







    def print_via(self, via):
        # Use tech file to find via rules
        via_def_id = self.ws.tech.find_via_def_by_name(self.tech_file, via.via_def_name)
        via_params = via.get_via_params(self.ws.db.get(via_def_id, 'params'))
        self.ws.db.create_via(self.cell_view, via_def_id, via.center.to_list(), "R0", via_params)

    def print_port(self, port):
        # if not port in self.port_list:
        #     self.add_port(port)
        font_size = min(port.box.w(), port.box.h()) / 5

        fig = self.ws.db.create_rect(self.cell_view, [port.layer, 'drawing'], port.box.to_list())
        # create net raise error if the net exists

        net = self.ws.db.create_net(self.cell_view, port.name)
        if net is None:
            net = self.ws.db.find_net_by_name(self.cell_view, port.name)
        self.ws.db.create_term( net, port.name, "inputOutput")
        self.ws.db.create_pin(net, fig)
        self.ws.db.create_label(self.cell_view, [port.layer, 'label'], port.position.to_list(), port.name, "centerCenter", "R0", "stick", font_size)

    # ---------------------
    # SCHEMATIC
    # ---------------------
    def print_schematic(self):
        # TODO: Would be nice. Requires all instances to be pade.Cell objects such that I have info about connectivity.
        pass




class LayoutInstance:
    """
    An instantiated LayoutItem
    """
    @staticmethod
    def from_cell(cell, parent_layout_item: LayoutItem, **kwargs):
        """
        Instantiate from pade.Cell
        Particularily suited for kit models
        """
        lib_name = cell.lib_name
        cell_name = cell.cell_name
        instance_name = kwargs.get('instance_name', cell.instance_name)
        lay_item = LayoutItem(lib_name, cell_name, instance_name)


        origin = kwargs.get('origin', Coordinate((0,0)))
        lay_item.set_origin(origin)
        # Print this layout item in paren layout
        lay_inst = parent_layout_item.print_instance(lay_item)
        # edit all cdf parameters of cell in instance
        for name, param in cell.parameters.items():
            if param.is_CDF:
                lay_inst.edit_cdf_param(name, param.value)

        # Add extra CDF parameters
        cdf_params = kwargs.get('CDF_params', {})
        for name, param in cdf_params.items():
            lay_inst.edit_cdf_param(name, param.value)

        # Keep track of parents transforms
        lay_inst.parent_transform = kwargs.get('transform')
        lay_inst.update_transform(lay_inst.inst.transform)
        return lay_inst


    def __init__(self, instance_id, **kwargs) -> None:
        self.inst = instance_id
        self.ws = Workspace.open()
        self.lib_id = self.ws.dd.get_obj(self.lib_name)
        self.tech_file = self.ws.tech.get_tech_file(self.lib_id)
        # Keep track of parents transforms
        self.parent_transform = kwargs.get('transform')
        self.update_transform(self.inst.transform)
        # Bounding box:
        self.set_box()


    def __getattr__(self, item):
        try:
            # First try supers gettatr
            return super().__getattr__(item)
        except:
            attr = getattr(self.inst, item)
            if attr is None:
                try:
                    # First check if item is a port of the instance
                    port = self.get_port(item)
                    if not port is None:
                        return port
                except:
                    pass
                try:
                    # Check if item is a subcell
                    for inst_id in self.master.instances:
                        lay_inst = LayoutInstance(inst_id, transform=self.transform)
                        if lay_inst.name == item:
                            return lay_inst
                except:
                    pass
                try:
                    # Then check if it is a cdf parameter
                    attr = self.get_cdf_param(item)
                except:
                    pass
            return attr


    def set_box(self):
        """
        Update box based on layout instance
        """
        b_box = self.inst.b_box
        self.box = Box(origin=b_box[0], opposite_corner=b_box[1])

    def update_transform(self, transform):
        """
        Concatenate new transform with parent transform
        """
        if not self.parent_transform is None:
            self.transform = self.ws.db.concat_transform(self.parent_transform, transform)
        else:
            self.transform = transform


    def set_origin(self, origin):
        old_trans = self.inst.transform
        self.inst.transform = [[origin[0], origin[1]], old_trans[1], old_trans[2]]
        self.update_transform(self.inst.transform)
        self.set_box()

    def set_orient(self, orient):
        old_trans = self.inst.transform
        self.inst.transform = [old_trans[0], orient, old_trans[2]]
        self.invoke_inst_callbacks()
        self.update_transform(self.inst.transform)
        self.set_box()

    def get_inst_origin(self):
        return Coordinate(self.inst.transform[0])

    def translate(self, translation):
        self.set_origin(self.get_inst_origin() + translation)

    def align_top(self, other , margin=0):
        """
        Place self on top of other with specified margin
        """
        # Calculate translation in y-direction
        translation = Vector([self.box.x_min(), self.box.y_min()], [other.box.x_min(), other.box.y_max() + margin])
        self.translate(translation)


    def align_right(self, other , margin=0):
        """
        Place self right of other with specified margin
        """
        # Calculate translation in y-direction
        translation = Vector([self.box.x_min(), self.box.y_min()], [other.box.x_max() + margin, other.box.y_min()])
        self.translate(translation)

    def align_left(self, other , margin=0):
        """
        Place self left of other with specified margin
        """
        # Calculate translation in y-direction
        translation = Vector([self.box.x_max(), self.box.y_min()], [other.box.x_min() - margin, other.box.y_min()])
        self.translate(translation)

    def set_xmin(self, xmin):
        """
        Translate to achieve targer xmin
        TODO: Does not handle rotated objects
        """
        translation = Vector([self.box.x_min(), 0], [xmin, 0])
        self.translate(translation)

    def set_ymin(self, ymin):
        """
        Translate to achieve target ymin
        """
        translation = Vector([0, self.box.y_min()], [0, ymin])
        self.translate(translation)

    def set_center(self, center):
        translation = Vector(self.box.center(), center)
        self.translate(translation)


    def edit_cdf_param(self, cdf_param_name, value):
        """
        Modify CDF Param of self
        """
        instance_parameters = self.ws.cdf.get_inst_CDF(self.inst).parameters
        for p in instance_parameters:
            if p.name == cdf_param_name:
                param_type = p.param_type
                if param_type == 'string':
                    value = num2string(value, decimals=3)
                if param_type == 'cyclic':
                    # Hack for cyclic parameters
                    param_type = 'string'
                self.ws.db.replace_prop(self.inst, cdf_param_name, param_type, value)
                # Update Box in case it is modified by CDF
                self.box = Box(origin=self.inst.b_box[0], opposite_corner=self.inst.b_box[1])

                # Run all callbacks. This fixes other derived parameters
                self.invoke_inst_callbacks()
                self.update_transform(self.inst.transform)
                self.set_box()
                return

        raise ValueError(f'Could not find parameter {cdf_param_name} in {self}')


    def invoke_inst_callbacks(self):
        """
        Run/invoke all callbacks of instance
        Using skill function written by Andrew Becket. Loaded in .cdsinit.
        """
        self.ws["abInvokeInstCdfCallbacks"](self.inst)


    def get_cdf_param(self, param_name):
        cdf_param_list = self.get_cdf_param_list()
        for p in cdf_param_list:
            if p.name == param_name:
                return p

    def get_cdf_param_list(self):
        return self.ws.cdf.get_inst_CDF(self.inst).parameters

    def get_pin(self, terminal_name):
        """
        Get pin of self from self's layout view
        """
        terminals = self.master.terminals
        for t in terminals:
            if t.name == terminal_name:
                for pin in t.pins:
                    if pin.fig is not None:
                        return pin

    def get_pin_b_box(self, terminal_name):
        pin = self.get_pin(terminal_name)
        b_box = pin.fig.b_box
        c1 = Coordinate(b_box[0])
        c2 = Coordinate(b_box[1])
        box = Box(origin=c1, opposite_corner=c2)
        return box

    def transform_bbox(self, b_box):
        return self.ws.db.transform_b_box(b_box, self.transform)

    def get_port(self, terminal_name):
        pin = self.get_pin(terminal_name)
        if pin is None:
            raise RuntimeError(f'Could not find pin {terminal_name} in {self}')
        b_box = pin.fig.b_box
        # Transform bbox with self.transform
        b_box = self.transform_bbox(b_box)
        box = Box(origin=b_box[0], opposite_corner=b_box[1])
        layer = pin.fig.layer_name
        port = Port(terminal_name, layer, box)
        return port


    def get_height(self):
        cv = self.ws.db.open_cell_view_by_type(self.lib_name, self.cell_name, "layout", "maskLayout", "r")
        return cv.b_box[1][1]

    def get_width(self):
        cv = self.ws.db.open_cell_view_by_type(self.lib_name, self.cell_name, "layout", "maskLayout", "r")
        return cv.b_box[1][0]




class SchematicPrinter:
    """
    Class for printing schematic, based on Layout instance and a cell
    """
    def __init__(self, lay_item: LayoutItem, cell: Cell) -> None:
        self.lay_item = lay_item
        self.lib_name = lay_item.lib_name
        self.cell_name = lay_item.cell_name
        self.cell = cell

    def print(self):
        ws = Workspace.open()
        layout_view = self.lay_item.cell_view

        # Open cell view
        cell_view = ws.db.open_cell_view_by_type(self.lib_name, self.cell_name, 'schematic', 'schematic', 'w')

        # Create pins
        iopin_master = ws.db.open_cell_view("basic", "iopin", "symbol", None, "r")
        terminal_list = layout_view.terminals
        for i in range(len(terminal_list)):
            t = terminal_list[i]
            ws.sch.create_pin(cell_view, iopin_master, t.name, "inputOutput", None, [0, i*0.2], "R0")

        # Create symbol if not already exists
        if not ws.dd.get_obj(self.lib_name, self.cell_name, "symbol"):
            ws.sch.view_to_view(self.lib_name, self.cell_name, self.lib_name, self.cell_name, "schematic", "symbol", "schSchemToPinList", "schPinListToSymbol")



        # Create instances
        x0 = 2
        y0 = 0.4
        symbol = None
        for lay_inst in layout_view.instances:
            if not symbol is None:
                symbol_width = symbol.b_box[1][0] - symbol.b_box[0][0]
                symbol_height = symbol.b_box[1][1] - symbol.b_box[0][1]
                x0 += symbol_width
                # Spread out in vertical direction
                if x0 > 15:
                    x0 = 2
                    y0 -= symbol_height

            # TODO: Handle recursive printing



            # Find symbol for instance
            symbol = ws.db.open_cell_view_by_type(lay_inst.lib_name, lay_inst.cell_name, "symbol")

            # Instantiate cell in schematic
            sch_inst = ws.db.create_inst_by_master_name(cell_view, lay_inst.lib_name, lay_inst.cell_name, 'symbol', lay_inst.name, [x0,y0], "R0")
            inst_origin = Coordinate(sch_inst.transform[0])

            # Copy all CDF params from lay_inst onto sch_inst
            ws.cdf.sync_inst_param_value(lay_inst, sch_inst)
            # Invoke all callbacks
            ws["abInvokeInstCdfCallbacks"](sch_inst)


            # TODO: Verify this! Not sure if this will work when nets and terminals have different names
            for term in sch_inst.master.terminals:
                # Find the name of the net that the term is connected to
                for net in layout_view.nets:
                    if net.term.name == term.name:
                        net_name = net.name

                pin_corners = term.pins[0].fig.b_box
                pin_center = Box(origin=pin_corners[0], opposite_corner=pin_corners[1]).center() + inst_origin
                # Draw wire
                wire_id_list = ws.sch.create_wire(cell_view, "draw", "full", [pin_center.to_list(), (pin_center + (0.05, 0)).to_list()], 0.0625, 0.0625, 0.0)
                # Create wire label
                ws.sch.create_wire_label(cell_view, wire_id_list[0],  (pin_center + (0.125, 0)).to_list(), net_name, "lowerLeft", "R0", "stick", 0.0625, None)

        # Check and save
        ws.sch.check(cell_view)
        ws.db.save(cell_view)






