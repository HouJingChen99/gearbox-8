from PySide2.QtWidgets import QLabel
from .stylesheet import STYLE_WHICH_KEY
from pygears.conf import Inject, reg_inject, registry
from PySide2.QtGui import QKeySequence


class WhichKey(QLabel):
    @reg_inject
    def __init__(self,
                 parent=None,
                 graph=Inject('graph/graph'),
                 shortcuts=Inject('graph/shortcuts')):
        super().__init__(parent)
        self.setStyleSheet(STYLE_WHICH_KEY)
        self.setMargin(2)
        self.hide()

        which_key_string = []
        for shortcut, callback in registry('graph/shortcuts'):
            keys = QKeySequence(shortcut).toString().split('+')

            try:
                shift_id = keys.index('Shift')
                keys.pop(shift_id)
            except ValueError:
                shift_id = None

            try:
                ctrl_id = keys.index('Ctrl')
                keys.pop(ctrl_id)
            except ValueError:
                ctrl_id = None

            if shift_id is None:
                keys[0] = keys[0].lower()

            if ctrl_id is not None:
                keys.insert(0, 'C')

            shortut_string = (f'<font color=\"DeepPink\"><b>'
                              f'{"-".join(keys)}'
                              f'</b></font> &#8594; {callback.__name__}')

            which_key_string.append(shortut_string)

        self.setText('&nbsp;&nbsp;'.join(which_key_string))

        graph.key_cancel.connect(self.cancel)

    def cancel(self):
        self.hide()