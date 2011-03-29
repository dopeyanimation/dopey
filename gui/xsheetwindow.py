import gtk

from gettext import gettext as _
import gobject

columns_name = ('frame_number', 'description')
columns_id = dict((name, i) for i, name in enumerate(columns_name))

# test data:
cel_list = []
for i in range(1, 25):
    cel_list.append({
            'frame_number': i,
            'description': "",
            'has_cel': False,
            'is_key': False,
    })

for i in (1, 8, 12):
    cel_list[i-1]['is_key'] = True


class ToolWidget(gtk.VBox):
    
    tool_widget_title = _("X Sheet")
    
    def __init__(self, app):
        gtk.VBox.__init__(self)
        self.app = app
        self.set_size_request(200, 150)
        
        sw = gtk.ScrolledWindow()
        sw.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.pack_start(sw)
        
        # create list:
        listmodel = self.create_list(cel_list)
        
        # create tree view:
        treeview = gtk.TreeView(listmodel)
        treeview.set_rules_hint(True)
        treeview.get_selection().set_mode(gtk.SELECTION_SINGLE)
        
        sw.add(treeview)

        self.add_columns(treeview)
        
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
            ani_cel['description'] = new_text
    
    def set_frame(self, column, cell, model, it):
        ani_cel = model.get_value(it, 0)
        cell.set_property('text', ani_cel['frame_number'])
        if ani_cel['is_key']:
            cell.set_property('background', '#f2f5a9')
        else:
            cell.set_property('background', '#ffffff')

    def set_description(self, column, cell, model, it):
        ani_cel = model.get_value(it, 0)
        cell.set_property('text', ani_cel['description'])
        
