STYLE_TEXTBROWSER = '''
color: {text_color};
background-color: {background};
selection-background-color: rgba(150, 150, 150, 70);
inset grey;
'''


STYLE_WHICH_KEY = '''
padding: 2px;
margin: 0px;
color: {text_color};
background: {background};
selection-background-color: rgba(219, 158, 0, 255);
'''

STYLE_MODELINE = '''
padding: 2px;
margin-bottom: 1px;
border-radius: 0px;
border: 1px solid rgba(235, 235, 235, 150);
color: {text_color};
background: {background};
selection-background-color: rgba(219, 158, 0, 255);
'''

STYLE_TABSEARCH_LIST = '''
QListView {{
    background-color: rgba(40, 40, 40, 255);
    border: 1px solid rgba(20, 20, 20, 255);
    color: {text_color};
    padding-top: 4px;
}}
'''

STYLE_QMENU = '''
QMenu {{
    color: rgba(255, 255, 255, 200);
    background-color: rgba(47, 47, 47, 255);
    border: 1px solid rgba(0, 0, 0, 30);
}}

QMenu::item {{
    padding: 5px 18px 2px;
    background-color: transparent;
}}
QMenu::item:selected {{
    color: rgba(98, 68, 10, 255);
    background-color: rgba(219, 158, 0, 255);
}}
QMenu::separator {{
    height: 1px;
    background: rgba(255, 255, 255, 50);
    margin: 4px 8px;
}}
'''
