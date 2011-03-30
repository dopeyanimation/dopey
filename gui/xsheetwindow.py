import gtk

from gettext import gettext as _
import gobject

from layerswindow import stock_button

columns_name = ('frame_number', 'description')
columns_id = dict((name, i) for i, name in enumerate(columns_name))


class ToolWidget(gtk.VBox):
    
    tool_widget_title = _("X Sheet")
    
    def __init__(self, app):
        gtk.VBox.__init__(self)
        self.app = app
        self.ani = app.doc.model.ani
        self.set_size_request(200, 150)

        # create list:
        listmodel = self.create_list(self.ani.cel_list)
        
        # create tree view:
        treeview = gtk.TreeView(listmodel)
        treeview.set_rules_hint(True)
        treeview.get_selection().set_mode(gtk.SELECTION_SINGLE)
       
        self.add_columns(treeview)
        
        layers_scroll = gtk.ScrolledWindow()
        layers_scroll.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        layers_scroll.add_with_viewport(treeview)

        # controls:
        
        key_button = stock_button(gtk.STOCK_ADD)
        key_button.connect('clicked', self.on_toggle_key)
        key_button.set_tooltip_text(_('Toggle Keyframe'))

        buttons_hbox = gtk.HBox()
        buttons_hbox.pack_start(key_button)

        self.pack_start(layers_scroll)
        self.pack_start(buttons_hbox, expand=False)
        
        self.show_all()
    
    def create_list(self, cel_list):
        lstore = gtk.ListStore(object)
        for cel in cel_list:
            lstore.append((cel,))
        return lstore
    
    def add_columns(self, treeview):
        listmodel = treeview.get_model()
        
        # frame column
        
        cell = gtk.CellRendererText()
        cell.set_data("column", columns_id['frame_number'])
        cell.set_property('background-set' , True)
        
        column = gtk.TreeViewColumn(_("Frame"))
        column.pack_start(cell, True)
        column.set_cell_data_func(cell, self.set_frame)
        
        # fix column to 50 pixels:
        column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        column.set_fixed_width(50)
        
        treeview.append_column(column)
        
        # description column
        
        cell = gtk.CellRendererText()
        cell.set_data("column", columns_id['description'])
        cell.set_property('editable' , True)
        cell.connect("edited", self.on_cell_edited, listmodel)
        
        column = gtk.TreeViewColumn(_("Description"))
        column.pack_start(cell, True)
        column.set_cell_data_func(cell, self.set_description)

        treeview.append_column(column)        
    
    def on_cell_edited(self, cell, path_string, new_text, model):
        it = model.get_iter_from_string(path_string)
        ani_cel = model.get_value(it, 0)
        column = cell.get_data("column")
        
        if column == columns_id['description']:
            ani_cel.description = new_text
    
    def on_toggle_key(self, button):
        current_cel = self.ani.get_current_cel()
        self.ani.toggle_key(current_cel)
    
    def set_frame(self, column, cell, model, it):
        ani_cel = model.get_value(it, 0)
        cell.set_property('text', ani_cel.frame_number)
        if ani_cel.is_key:
            cell.set_property('background', '#f2f5a9')
        else:
            cell.set_property('background', '#ffffff')

    def set_description(self, column, cell, model, it):
        ani_cel = model.get_value(it, 0)
        cell.set_property('text', ani_cel.description)
        
