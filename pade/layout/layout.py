from pade import warn, fatal
from pade.layout.geometry import *
from pade.layout.pattern import *
from pade.layout.routing import *
from pade.utils import num2string
from skillbridge import Workspace
import numpy as np
import re

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

        self.property_list = []

        self.ws = Workspace.open()
        lib_id = self.ws.dd.get_obj(self.lib_name)
        self.tech_file = self.ws.tech.get_tech_file(lib_id)
        self.cell_view = None

    def __str__(self) -> str:
        return f"LayoutItem {self.cell_name} at {self.origin} with {len(self.pattern_list)} Patterns"

    def add_property(self, name, value):
        """
        These are stored on the instace when instantiated
        """
        self.property_list.append((name, value))

    def get_property(self, name):
        for pname, value in self.property_list:
            if pname == name:
                return value

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
        return pattern

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

    def add_vias_on_port(self, via_name_list, port):
        for via_name in via_name_list:
            via = Via(via_name, port=port)
            self.add_via(via)

    def add_via_from_pattern(self, via_def_name, pattern: Pattern, margin=0, **via_attr):
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
            via = Via(via_def_name, box=new_box, via_attr=via_attr)
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

    def instantiate(self, lay_class, cell, build, **kwargs):
        """
        Instantiate component. I build is True, the component will be built using the constructor, otherwise only instantiated from library
        """
        if build:
            lay_item = lay_class(cell, **kwargs)
            lay_inst = self.print_instance(lay_item)
            return lay_inst
        else:
            return LayoutInstance.from_cell(cell, self)

    # -----------------------------
    # Skill interaction functions
    # -----------------------------

    def get_cell_view_terminal(self, tname):
        """
        Get terminal of self from self's layout view
        """
        try:
            terminals = self.ws.db.get(self.cell_view, 'terminals')
            for t in terminals:
                if t.name == tname:
                    for pin in t.pins:
                        if pin.fig is not None:
                            return pin
        except:
            pass


    def get_cell_view_port(self, terminal_name):
        pin = self.get_cell_view_terminal(terminal_name)
        if pin is None:
            raise RuntimeError(f'Could not find pin {terminal_name} in {self}')
        b_box = pin.fig.b_box
        box = Box(origin=b_box[0], opposite_corner=b_box[1])
        layer = pin.fig.layer_name
        port = Port(terminal_name, layer, box)
        return port


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


    def get_all_instances(self):
        """
        Returns all instances in cell_vew as LayoutInstance objects
        """
        instance_list = self.cell_view.instances
        return [LayoutInstance(i) for i in instance_list]


    def print_layout(self, recursive=False):
        """
        Write Layout
        """
        if self.cell_view is None:
            self.open_layoutview()

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
            self.print_port( port)

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

    def print_instance(self, instance):
        """
        This instantiates the LayoutItem in the layout cell view. The instance ID is atored as an attribute
        """
        if self.cell_view is None:
            self.open_layoutview()

        instance_id = self.ws.db.create_inst_by_master_name(self.cell_view, instance.lib_name, instance.cell_name, 'layout', instance.instance_name, instance.origin.to_list(), instance.orientation)

        lay_inst = LayoutInstance(instance_id, origin=instance.origin)

        # Set properties from parents property list
        for name, value in instance.property_list:
            lay_inst.set_property(name, value)

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
        path_id = self.ws.db.create_path_seg(self.cell_view, [path.layer, path.purpose], path.start.to_list(), path.stop.to_list(), path.width, path.begin_style, path.end_style)
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
        run_callbacks = kwargs.get('run_callbacks', True)
        for name, param in cell.parameters.items():
            if param.is_CDF:
                lay_inst.edit_cdf_param(name, param.value, run_callbacks=run_callbacks)

        # Add extra CDF parameters
        cdf_params = kwargs.get('CDF_params', {})
        for name, param in cdf_params.items():
            lay_inst.edit_cdf_param(name, param.value, run_callbacks=run_callbacks)

        # Update inst transform
        # lay_inst.invoke_inst_callbacks()
        lay_inst.update_transform(lay_inst.inst.transform)
        lay_inst.set_box()

        # Keep track of parents transforms
        lay_inst.parent_transform = kwargs.get('transform')
        lay_inst.update_transform(lay_inst.inst.transform)

        # Set properties from lay_items property list
        for name, value in lay_item.property_list:
            lay_inst.set_property(name, value)
        return lay_inst


    def __init__(self, instance_id, **kwargs) -> None:
        self.inst = instance_id
        self.ws = Workspace.open()
        self.name = self.inst.name
        self.cell_name = self.inst.cell_name
        self.lib_name = self.inst.lib_name
        self.lib_id = self.ws.dd.get_obj(self.lib_name)
        self.tech_file = self.ws.tech.get_tech_file(self.lib_id)
        # Keep track of parents transforms
        self.parent_transform = kwargs.get('transform')
        self.transform = None
        self.update_transform(self.inst.transform)
        # Bounding box:
        self.set_box()

    def get_transform(self):
        return super().__getattr__("transform")

    def __str__(self) -> str:
        return f"{self.cell_name} {self.name}"

    def __getattr__(self, item):
        # Check if it is a coordinate
        try:
            # Check if it is a property that can be transformed (like a box or coordinate)
            prop = self.get_transform_property(item)
            if not prop is None:
                return prop
            raise AttributeError()
        except:
            pass
        # Check if it is an attribute of the instance
        try:
            attr = getattr(self.inst, item)
            if not attr is None:
                return attr
            raise AttributeError()
        except:
            pass
        # Check if it is a property
        try:
            prop =  self.get_property(item)
            if not prop is None:
                return prop
            raise AttributeError()
        except:
            pass
        # Check if it is a port
        try:
            port = self.get_port(item)
            if not port is None:
                return port
            raise AttributeError()
        except:
            pass
        try:
            # Then check if it is a cdf parameter
            param = self.get_cdf_param(item)
            if not param is None:
                return param
            raise AttributeError()
        except:
            pass

        # Check if it is a subcell
        try:
            for inst_id in self.ws.db.get(self.inst.master, 'instances'):
                lay_inst = LayoutInstance(inst_id, transform=self.transform)
                if lay_inst.name == item:
                    return lay_inst
            raise AttributeError()
        except:
            pass

        # Finally, try getattr on all subcells
        try:
            for inst_id in self.ws.db.get(self.inst.master, 'instances'):
                lay_inst = LayoutInstance(inst_id, transform=self.transform)
                return getattr(lay_inst, item)
        except:
            pass

        raise AttributeError(f'Failed to get {item} from {self}')

    def get_property(self, name):
        for prop in self.inst.prop:
            if prop.name == name:
                return prop.value

    def get_coordinate(self, cname):
        return self.get_transform_property(cname)

    def get_transform_property(self, pname):
        """
        Return transformed property pname.
        Craches if it fails
        """
        transform = self.transform
        translation = Vector(transform[0])
        # Finally return coordinate
        try:
            c = self.get_property(pname)
        except:
            raise RuntimeError(f'Failed to get property {pname} from {self}')
        # Check if is a coordinate
        try:
            c = Coordinate(c)
            return c + translation
        except:
            pass
        # Check if it is a b_box
        try:
            b = Box(c)
            return b.translate(translation)
        except:
            pass
        raise ValueError(f'Property {pname} could not be converted to Coordinate or Box')


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
            self.transform = self.ws.db.concat_transform(transform, self.parent_transform)
        else:
            self.transform = transform

    def set_property(self, name, value):
        self.ws.db.setq(self.inst, value, name)

    def set_origin(self, origin):
        old_trans = self.inst.transform
        self.inst.transform = [[origin[0], origin[1]], old_trans[1], old_trans[2]]
        self.update_transform(self.inst.transform)
        self.set_box()

    def set_orient(self, orient, run_callbacks=True):
        old_trans = self.inst.transform
        self.inst.transform = [old_trans[0], orient, old_trans[2]]
        if run_callbacks:
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


    def align_hcenter(self, other):
        """
        Horisontally center self relative to other
        """
        # Calculate translation in y-direction
        translation = Vector(self.box.center(), [other.box.center()[0], self.box.center()[1]])
        self.translate(translation)

    def align_vcenter(self, other):
        """
        Vertically center self relative to other
        """
        # Calculate translation in y-direction
        translation = Vector(self.box.center(), [self.box.center()[0], other.box.center()[1]])
        self.translate(translation)

    def align_below(self, other , margin=0):
        """
        Place self below of other with specified margin
        """
        # Calculate translation in y-direction
        translation = Vector(
            [self.box.x_min(), self.box.y_max()],
            [other.box.x_min(), other.box.y_min() - margin])
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


    def edit_cdf_param(self, cdf_param_name, value, run_callbacks=True):
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
                # Causes problem for CAP
                if run_callbacks:
                    self.invoke_inst_callbacks()
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
        try:
            terminals = self.ws.db.get(self.inst.master, 'terminals')
            for t in terminals:
                if t.name == terminal_name:
                    for pin in t.pins:
                        if pin.fig is not None:
                            return pin
        except:
            pass

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


    def get_property_box_list(self, pattern):
        """
        Returns the property boxes that match the given regex pattern
        """
        if not self.inst.prop is None:
            box_list = [p.value for p in self.inst.prop if re.match(pattern, p.name)]
            box_list = [self.transform_bbox(b) for b in box_list]
            box_list = [Box(b) for b in box_list]
            box_list.sort(key=lambda x: x.center()[1])
            return box_list
        else:
            return []



    def get_property_box(self, pname):
        """
        Returns the property box with given name
        """
        box = [p.value for p in self.inst.prop if p.name == pname][0]
        box = Box(self.transform_bbox(box))
        return box
