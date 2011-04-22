import gtk

from gettext import gettext as _
import gobject

import dialogs
from layerswindow import stock_button

COLUMNS_NAME = ('frame_index', 'frame_data')
COLUMNS_ID = dict((name, i) for i, name in enumerate(COLUMNS_NAME))

XSHEET_COLORS = {
    'key_on': ('#f2f5a9', '#f2f5a9'),
    'key_off': ('#ffffff', '#ededed'),
    'with_cel': ('#cdf5ff', '#c3e9f2'),
    'without_cel': ('#ffffff', '#ededed'),
}

class ToolWidget(gtk.VBox):
    
    tool_widget_title = _("X Sheet")
    
    def __init__(self, app):
        gtk.VBox.__init__(self)
        self.app = app
        self.ani = app.doc.model.ani
        self.set_size_request(200, 150)
        
        # create list:
        self.listmodel = self.create_list(self.ani.get_xsheet_list())
        
        # create tree view:
        self.treeview = gtk.TreeView(self.listmodel)
        self.treeview.set_rules_hint(True)
        treesel = self.treeview.get_selection()
        treesel.set_mode(gtk.SELECTION_SINGLE)
        treesel.connect('changed', self.on_row_changed)
        
        self.add_columns()
        
        layers_scroll = gtk.ScrolledWindow()
        layers_scroll.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        layers_scroll.add_with_viewport(self.treeview)

        # controls:
        
        key_button = stock_button(gtk.STOCK_JUMP_TO)
        key_button.connect('clicked', self.on_toggle_key)
        key_button.set_tooltip_text(_('Toggle Keyframe'))
        
        previous_button = stock_button(gtk.STOCK_GO_UP)
        previous_button.connect('clicked', self.on_previous_frame)
        previous_button.set_tooltip_text(_('Previous Frame'))
        
        next_button = stock_button(gtk.STOCK_GO_DOWN)
        next_button.connect('clicked', self.on_next_frame)
        next_button.set_tooltip_text(_('Next Frame'))
        
        chdesc_button = stock_button(gtk.STOCK_ITALIC)
        chdesc_button.connect('clicked', self.on_change_description)
        chdesc_button.set_tooltip_text(_('Change Cel Description'))
        
        add_button = stock_button(gtk.STOCK_ADD)
        add_button.connect('clicked', self.on_add_cel)
        add_button.set_tooltip_text(_('Add cel to this frame'))
        
        buttons_hbox = gtk.HBox()
        buttons_hbox.pack_start(key_button)
        buttons_hbox.pack_start(previous_button)
        buttons_hbox.pack_start(next_button)
        buttons_hbox.pack_start(chdesc_button)
        buttons_hbox.pack_start(add_button)

        self.pack_start(layers_scroll)
        self.pack_start(buttons_hbox, expand=False)
        
        self.show_all()

        self.app.doc.model.doc_observers.append(self.update)
        
    def _get_path_from_frame(self, frame):
        return (self.ani.frames.idx, )
    
    def update(self, doc):
        frame = self.ani.frames.get_selected()
        path = self._get_path_from_frame(frame)
        self.treeview.get_selection().select_path(path)
        self.queue_draw()
    
    def create_list(self, xsheet_list):
        listmodel = gtk.ListStore(int, object)
        for i, frame in xsheet_list:
            listmodel.append((i, frame))
        return listmodel
    
    def add_columns(self):
        listmodel = self.treeview.get_model()
        
        # frame column
        
        cell = gtk.CellRendererText()
        cell.set_property('background-set' , True)
        
        column = gtk.TreeViewColumn(_("Frame"))
        column.pack_start(cell, True)
        column.set_cell_data_func(cell, self.set_number)
        
        # fix column to 50 pixels:
        column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        column.set_fixed_width(50)
        
        self.treeview.append_column(column)
        
        # description column
        
        cell = gtk.CellRendererText()
        cell.set_property('background-set' , True)
        
        column = gtk.TreeViewColumn(_("Description"))
        column.pack_start(cell, True)
        column.set_cell_data_func(cell, self.set_description)

        self.treeview.append_column(column)        
    
    def on_row_activated(self, treeview, path, view_column):
        self.ani.select_frame(path[COLUMNS_ID['frame_index']])

    def on_row_changed(self, treeselection):
        model, it = treeselection.get_selected()
        path = model.get_path(it)
        self.ani.select_frame(path[COLUMNS_ID['frame_index']])
        
    def on_toggle_key(self, button):
        self.ani.toggle_key()
    
    def on_previous_frame(self, button):
        self.ani.previous_frame()
    
    def on_next_frame(self, button):
        self.ani.next_frame()
    
    def on_change_description(self, button):
        treeselection = self.treeview.get_selection()
        model, it = treeselection.get_selected()
        frame = model.get_value(it, COLUMNS_ID['frame_data'])
        
        description = dialogs.ask_for_name(self, _("Description"),
                                           frame.description)
        if description:
            self.ani.change_description(description)
    
    def on_add_cel(self, button):
        treeselection = self.treeview.get_selection()
        model, it = treeselection.get_selected()
        frame = model.get_value(it, COLUMNS_ID['frame_data'])
        self.ani.add_cel()
    
    def _get_row_class(self, model, it):
        """Return 0 if even row, 1 if odd row."""
        path = model.get_path(it)[0]
        return path % 2

    def set_number(self, column, cell, model, it):
        idx = model.get_value(it, COLUMNS_ID['frame_index'])
        cell.set_property('text', idx+1)
        
        frame = model.get_value(it, COLUMNS_ID['frame_data'])
        r = self._get_row_class(model, it)
        if frame.is_key:
            cell.set_property('background', 
                              XSHEET_COLORS['key_on'][r])
        else:
            cell.set_property('background', 
                              XSHEET_COLORS['key_off'][r])

    def set_description(self, column, cell, model, it):
        frame = model.get_value(it, COLUMNS_ID['frame_data'])
        cell.set_property('text', frame.description)
        
        r = self._get_row_class(model, it)
        if frame.cel is not None:
            cell.set_property('background',
                              XSHEET_COLORS['with_cel'][r])
        else:
            cell.set_property('background', 
                              XSHEET_COLORS['without_cel'][r])
