#!/usr/bin/python

from PySide2 import QtCore, QtWidgets, QtGui

from .constants import (IN_PORT, OUT_PORT, PIPE_LAYOUT_CURVED,
                        PIPE_LAYOUT_STRAIGHT)
from .node_abstract import AbstractNodeItem
from .pipe import Pipe
from .port import PortItem
from .scene import NodeScene
from .node import NodeItem

from pygears.conf import Inject, reg_inject, bind, MayInject

ZOOM_MIN = -0.95
ZOOM_MAX = 2.0


@reg_inject
def graph(main=Inject('viewer/main'), root=Inject('gear/hier_root')):
    viewer = Graph()
    main.buffers['graph'] = viewer
    bind('viewer/graph', viewer)
    viewer.resize(800, 500)
    viewer.setGeometry(500, viewer.y(), 800, 500)

    top = NodeItem(root)
    viewer.top = top
    top.layout()
    viewer.fit_all()


class Graph(QtWidgets.QGraphicsView):

    moved_nodes = QtCore.Signal(dict)
    connection_changed = QtCore.Signal(list, list)
    node_selected = QtCore.Signal(str)

    @reg_inject
    def __init__(self,
                 parent=None,
                 sim_bridge=MayInject('viewer/sim_bridge'),
                 sim_proxy=MayInject('viewer/sim_proxy')):
        super().__init__(parent)
        scene_area = 8000.0
        scene_pos = (scene_area / 2) * -1
        self.setScene(NodeScene(self))
        self.setSceneRect(scene_pos, scene_pos, scene_area, scene_area)
        self.setRenderHint(QtGui.QPainter.Antialiasing, True)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setViewportUpdateMode(QtWidgets.QGraphicsView.FullViewportUpdate)
        self._pipe_layout = PIPE_LAYOUT_STRAIGHT
        self._live_pipe = None
        self._detached_port = None
        self._start_port = None
        self._origin_pos = None
        self._previous_pos = QtCore.QPoint(self.width(), self.height())
        self._prev_selection = []
        self._node_positions = {}
        self._rubber_band = QtWidgets.QRubberBand(
            QtWidgets.QRubberBand.Rectangle, self)
        self._undo_stack = QtWidgets.QUndoStack(self)

        self.acyclic = True
        self.LMB_state = False
        self.RMB_state = False
        self.MMB_state = False

        if sim_bridge:
            sim_bridge.sim_refresh.connect(self.sim_refresh)
            sim_bridge.after_run.connect(self.sim_refresh)
            self.timestep_proxy = sim_proxy.registry('sim/timestep')

    def __str__(self):
        return '{}.{}()'.format(self.__module__, self.__class__.__name__)

    def __repr__(self):
        return '{}.{}()'.format(self.__module__, self.__class__.__name__)

    def sim_refresh(self):
        self.print_modeline()

    @reg_inject
    def print_modeline(self,
                       modeline=Inject('viewer/modeline')):
        template = f"""
        <table>
            <td width=20%><font color=\"darkorchid\"><b>graph</b></font></td>
            <td width=80%>Timestep: {self.timestep_proxy.get()}</td>
        </table>
        """

        modeline.setText(template)

    def activate(self):
        if hasattr(self, 'timestep_proxy'):
            self.print_modeline()

    def _set_viewer_zoom(self, value):
        if value == 0.0:
            return
        scale = 0.9 if value < 0.0 else 1.1
        zoom = self.get_zoom()
        if ZOOM_MIN >= zoom:
            if scale == 0.9:
                return
        if ZOOM_MAX <= zoom:
            if scale == 1.1:
                return
        self.scale(scale, scale)

    def _set_viewer_pan(self, pos_x, pos_y):
        scroll_x = self.horizontalScrollBar()
        scroll_y = self.verticalScrollBar()
        scroll_x.setValue(scroll_x.value() - pos_x)
        scroll_y.setValue(scroll_y.value() - pos_y)

    def _combined_rect(self, nodes):
        group = self.scene().createItemGroup(nodes)
        rect = group.boundingRect()
        self.scene().destroyItemGroup(group)
        return rect

    def _items_near(self, pos, item_type=None, width=20, height=20):
        x, y = pos.x() - width, pos.y() - height
        rect = QtCore.QRect(x, y, width, height)
        items = []
        for item in self.scene().items(rect):
            if not item_type or isinstance(item, item_type):
                items.append(item)
        return items

    def mousePressEvent(self, event):
        alt_modifier = event.modifiers() == QtCore.Qt.AltModifier
        shift_modifier = event.modifiers() == QtCore.Qt.ShiftModifier
        if event.button() == QtCore.Qt.LeftButton:
            self.LMB_state = True
        elif event.button() == QtCore.Qt.RightButton:
            self.RMB_state = True
        elif event.button() == QtCore.Qt.MiddleButton:
            self.MMB_state = True
        self._origin_pos = event.pos()
        self._previous_pos = event.pos()
        self._prev_selection = self.selected_nodes()

        if alt_modifier:
            return

        items = self._items_near(self.mapToScene(event.pos()), None, 20, 20)
        nodes = [i for i in items if isinstance(i, AbstractNodeItem)]

        # toggle extend node selection.
        if shift_modifier:
            for node in nodes:
                node.selected = not node.selected

        # update the recorded node positions.
        self._node_positions.update({n: n.pos for n in self.selected_nodes()})

        # show selection selection marquee
        if self.LMB_state and not items:
            rect = QtCore.QRect(self._previous_pos, QtCore.QSize())
            rect = rect.normalized()
            map_rect = self.mapToScene(rect).boundingRect()
            self.scene().update(map_rect)
            self._rubber_band.setGeometry(rect)
            self._rubber_band.show()

        if not shift_modifier:
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.LMB_state = False
        elif event.button() == QtCore.Qt.RightButton:
            self.RMB_state = False
        elif event.button() == QtCore.Qt.MiddleButton:
            self.MMB_state = False

        # hide selection marquee
        if self._rubber_band.isVisible():
            rect = self._rubber_band.rect()
            map_rect = self.mapToScene(rect).boundingRect()
            self._rubber_band.hide()
            self.scene().update(map_rect)

        # find position changed nodes and emit signal.
        moved_nodes = {
            n: pos
            for n, pos in self._node_positions.items() if n.pos != pos
        }
        if moved_nodes:
            self.moved_nodes.emit(moved_nodes)

        # reset recorded positions.
        self._node_positions = {}

        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        alt_modifier = event.modifiers() == QtCore.Qt.AltModifier
        shift_modifier = event.modifiers() == QtCore.Qt.ShiftModifier
        if self.MMB_state and alt_modifier:
            pos_x = (event.x() - self._previous_pos.x())
            zoom = 0.1 if pos_x > 0 else -0.1
            self._set_viewer_zoom(zoom)
        elif self.MMB_state or (self.LMB_state and alt_modifier):
            pos_x = (event.x() - self._previous_pos.x())
            pos_y = (event.y() - self._previous_pos.y())
            self._set_viewer_pan(pos_x, pos_y)

        if self.LMB_state and self._rubber_band.isVisible():
            rect = QtCore.QRect(self._origin_pos, event.pos()).normalized()
            map_rect = self.mapToScene(rect).boundingRect()
            path = QtGui.QPainterPath()
            path.addRect(map_rect)
            self._rubber_band.setGeometry(rect)
            self.scene().setSelectionArea(path, QtCore.Qt.IntersectsItemShape)
            self.scene().update(map_rect)

            if shift_modifier and self._prev_selection:
                for node in self._prev_selection:
                    if node not in self.selected_nodes():
                        node.selected = True

        self._previous_pos = event.pos()
        super().mouseMoveEvent(event)

    def wheelEvent(self, event):
        adjust = (event.delta() / 120) * 0.1
        self._set_viewer_zoom(adjust)

    def establish_connection(self, start_port, end_port):
        """
        establish a new pipe connection.
        """
        pipe = Pipe()
        print(f'Add pipe: {start_port} -> {end_port}')
        self.scene().addItem(pipe)
        pipe.set_connections(start_port, end_port)
        # pipe.draw_path(pipe.input_port, pipe.output_port)
        return pipe

    def sceneMousePressEvent(self, event):
        """
        triggered mouse press event for the scene (takes priority over viewer).
         - detect selected pipe and start connection.
         - remap Shift and Ctrl modifier.

        Args:
            event (QtWidgets.QGraphicsScenePressEvent):
                The event handler from the QtWidgets.QGraphicsScene
        """
        ctrl_modifier = event.modifiers() == QtCore.Qt.ControlModifier
        alt_modifier = event.modifiers() == QtCore.Qt.AltModifier
        shift_modifier = event.modifiers() == QtCore.Qt.ShiftModifier
        if shift_modifier:
            event.setModifiers(QtCore.Qt.ControlModifier)
        elif ctrl_modifier:
            event.setModifiers(QtCore.Qt.ShiftModifier)

        if not alt_modifier:
            pos = event.scenePos()
            # port_items = self._items_near(pos, PortItem, 5, 5)
            # if port_items:
            #     port = port_items[0]
            #     if not port.multi_connection and port.connected_ports:
            #         self._detached_port = port.connected_ports[0]
            #     self.start_live_connection(port)
            #     if not port.multi_connection:
            #         [p.delete() for p in port.connected_pipes]
            #     return

            node_items = self._items_near(pos, AbstractNodeItem, 3, 3)
            if node_items:
                node = node_items[0]

                # record the node positions at selection time.
                for n in node_items:
                    self._node_positions[n] = n.pos

                # emit selected node id with LMB.
                if event.button() == QtCore.Qt.LeftButton:
                    self.node_selected.emit(node.id)

                if not node.model.child:
                    return

            # pipe_items = self._items_near(pos, Pipe, 3, 3)
            # if pipe_items:
            #     pipe = pipe_items[0]
            #     attr = {IN_PORT: 'output_port', OUT_PORT: 'input_port'}
            #     from_port = pipe.port_from_pos(pos, True)
            #     to_port = getattr(pipe, attr[from_port.port_type])
            #     if not from_port.multi_connection and from_port.connected_ports:
            #         self._detached_port = from_port.connected_ports[0]
            #     elif not to_port.multi_connection:
            #         self._detached_port = to_port

            #     self.start_live_connection(from_port)
            #     self._live_pipe.draw_path(self._start_port, None, pos)
            #     pipe.delete()

    def all_pipes(self):
        pipes = []
        for item in self.scene().items():
            if isinstance(item, Pipe):
                pipes.append(item)
        return pipes

    def select(self, obj):

        for n in self.selected_nodes():
            n.selected = False

        for p in self.selected_pipes():
            p.setSelected(False)

        obj.setSelected(True)

    def select_all(self):
        """
        Select all nodes in the current node graph.
        """
        self._undo_stack.beginMacro('select all')
        for node in self.all_nodes():
            node.set_selected(True)
        self._undo_stack.endMacro()

    def clear_selection(self):
        """
        Clears the selection in the node graph.
        """
        self._undo_stack.beginMacro('deselected nodes')
        for node in self.all_nodes():
            node.set_selected(False)
        self._undo_stack.endMacro()

    def all_nodes(self):
        nodes = []
        for item in self.scene().items():
            if isinstance(item, AbstractNodeItem):
                nodes.append(item)
        return nodes

    def selected_nodes(self):
        nodes = []
        for item in self.scene().selectedItems():
            if isinstance(item, AbstractNodeItem):
                nodes.append(item)
        return nodes

    def selected_pipes(self):
        pipes = []
        for item in self.scene().selectedItems():
            if isinstance(item, Pipe):
                pipes.append(item)
        return pipes

    def add_node(self, node, pos=None):
        print(f'Adding: {node.name}')
        pos = pos or (self._previous_pos.x(), self._previous_pos.y())
        node.pre_init(self, pos)
        self.scene().addItem(node)

    def remove_node(self, node):
        if isinstance(node, AbstractNodeItem):
            node.delete()

    def move_nodes(self, nodes, pos=None, offset=None):
        group = self.scene().createItemGroup(nodes)
        group_rect = group.boundingRect()
        if pos:
            x, y = pos
        else:
            pos = self.mapToScene(self._previous_pos)
            x = pos.x() - group_rect.center().x()
            y = pos.y() - group_rect.center().y()
        if offset:
            x += offset[0]
            y += offset[1]
        group.setPos(x, y)
        self.scene().destroyItemGroup(group)

    def get_pipes_from_nodes(self, nodes=None):
        nodes = nodes or self.selected_nodes()
        if not nodes:
            return
        pipes = []
        for node in nodes:
            n_inputs = node.inputs if hasattr(node, 'inputs') else []
            n_outputs = node.outputs if hasattr(node, 'outputs') else []

            for port in n_inputs:
                for pipe in port.connected_pipes:
                    connected_node = pipe.output_port.node
                    if connected_node in nodes:
                        pipes.append(pipe)
            for port in n_outputs:
                for pipe in port.connected_pipes:
                    connected_node = pipe.input_port.node
                    if connected_node in nodes:
                        pipes.append(pipe)
        return pipes

    def center_on(self, nodes=None):
        """
        Center the node graph on the given nodes or all nodes by default.

        Args:
            nodes (list[NodeGraphQt.Node]): a list of nodes.
        """
        self.center_selection(nodes)

    def center_selection(self, nodes=None):
        if not nodes:
            if self.selected_nodes():
                nodes = self.selected_nodes()
            elif self.all_nodes():
                nodes = self.all_nodes()
        if len(nodes) == 1:
            self.centerOn(nodes[0])
        else:
            rect = self._combined_rect(nodes)
            self.centerOn(rect.center().x(), rect.center().y())

    def get_pipe_layout(self):
        return self._pipe_layout

    def set_pipe_layout(self, layout=''):
        layout_types = {
            'curved': PIPE_LAYOUT_CURVED,
            'straight': PIPE_LAYOUT_STRAIGHT
        }
        self._pipe_layout = layout_types.get(layout, 'curved')
        # for pipe in self.all_pipes():
        #     pipe.draw_path(pipe.input_port, pipe.output_port)

    def reset_zoom(self):
        self.scale(1.0, 1.0)
        self.resetMatrix()

    def get_zoom(self):
        transform = self.transform()
        cur_scale = (transform.m11(), transform.m22())
        return float('{:0.2f}'.format(cur_scale[0] - 1.0))

    def set_zoom(self, value=0.0):
        if value == 0.0:
            self.reset_zoom()
            return
        zoom = self.get_zoom()
        if zoom < 0.0:
            if not (ZOOM_MIN <= zoom <= ZOOM_MAX):
                return
        else:
            if not (ZOOM_MIN <= value <= ZOOM_MAX):
                return
        value = value - zoom
        self._set_viewer_zoom(value)

    def fit_all(self):
        self.zoom_to_nodes(self.top._nodes)

    def zoom_to_nodes(self, nodes):
        rect = self._combined_rect(nodes)
        self.fitInView(rect, QtCore.Qt.KeepAspectRatio)
        if self.get_zoom() > 0.1:
            self.reset_zoom()
