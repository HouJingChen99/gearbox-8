#!/usr/bin/python
from NodeGraphQt.base.commands import PortConnectedCmd, PortDisconnectedCmd
from NodeGraphQt.base.model import PortModel


class Port(object):

    def __init__(self, node, port):
        """
        Args:
            node (NodeGraphQt.NodeObject): parent node object.
            port (NodeGraphQt.widgets.port.PortItem): port view item.
        """
        self.__view = port
        self.__model = PortModel(node)

    def __repr__(self):
        module = str(self.__class__.__module__)
        port = str(self.__class__.__name__)
        return '{}.{}(\'{}\')'.format(module, port, self.name())

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.node().id() == other.node().id()
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    @property
    def view(self):
        """
        returns the view item used in the scene.

        Returns:
            PortItem: port item.
        """
        return self.__view

    @property
    def model(self):
        """
        returns the port model.

        Returns:
            PortModel: port model.
        """
        return self.__model

    def type(self):
        """
        Returns the port type.

        Returns:
            str: 'in' for input port or 'out' for output port.
        """
        return self.model.type

    def multi_connection(self):
        """
        Returns if the ports is a single connection or not.

        Returns:
            bool: false if port is a single connection port
        """
        return self.model.multi_connection

    def node(self):
        """
        Return the parent node of the port.

        Returns:
            NodeGraphQt.NodeObject: parent node object.
        """
        return self.model.node

    def name(self):
        """
        name of the port.

        Returns:
            str: port name.
        """
        return self.model.name

    def connected_ports(self):
        """
        Returns all connected ports.

        Returns:
            list[NodeGraphQt.Port]: list of connected ports.
        """
        ports = []
        graph = self.node().graph
        for node_id, port_names in self.model.connected_ports.items():
            for port_name in port_names:
                node = graph.get_node_by_id(node_id)
                if self.type() == 'in':
                    ports.append(node.outputs()[port_name])
                elif self.type() == 'out':
                    ports.append(node.inputs()[port_name])
        return ports

    def connect_to(self, port=None):
        """
        Create connection to the specified port.

        Args:
            port (NodeGraphQt.Port): port object.
        """
        if not port:
            return

        graph = self.node().graph
        viewer = graph.viewer()
        undo_stack = graph.undo_stack()

        undo_stack.beginMacro('connected port')

        pre_conn_port = None
        src_conn_ports = self.connected_ports()
        if not self.multi_connection() and src_conn_ports:
            pre_conn_port = src_conn_ports[0]

        if not port:
            if pre_conn_port:
                undo_stack.push(PortDisconnectedCmd(self, port))
            return

        if graph.acyclic() and viewer.acyclic_check(self.view, port.view):
            if pre_conn_port:
                undo_stack.push(PortDisconnectedCmd(self, pre_conn_port))
                return

        # trg_conn_ports = port.connected_ports()
        # if not port.multi_connection() and trg_conn_ports:
        #     dettached_port = trg_conn_ports[0]
        #     undo_stack.push(PortDisconnectedCmd(port, dettached_port))
        # if pre_conn_port:
        #     undo_stack.push(PortDisconnectedCmd(self, pre_conn_port))

        undo_stack.push(PortConnectedCmd(self, port))
        undo_stack.endMacro()

    def disconnect_from(self, port=None):
        """
        Disconnect from the specified port.

        Args:
            port (NodeGraphQt.Port): port object.
        """
        if not port:
            return
        graph = self.node().graph
        graph._undo_stack.push(PortDisconnectedCmd(self, port))
