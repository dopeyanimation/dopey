import gtk

from gettext import gettext as _
import gobject

(
  COLUMN_FRAME_NUMBER,
  COLUMN_DESCRIPTION,
  COLUMN_HAS_CEL,
  COLUMN_FG_COLOR,
  COLUMN_BG_COLOR,
) = range(5)

# test data:
cel_list = []
for i in range(1, 25):
    cel_list.append({
            'frame_number': i,
            'description': "",
            'has_cel': False,
            'fg_color': '#222',
            'bg_color': '#faa',
    })


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
        
        # create tree model:
        model = self.__create_model()
        
        # create tree view:
        treeview = gtk.TreeView(model)
        treeview.set_rules_hint(True)
        treeview.get_selection().set_mode(gtk.SELECTION_SINGLE)
        
        sw.add(treeview)

        self.__add_columns(treeview)
        
        self.show_all()
    
    def __create_model(self):
        
        lstore = gtk.ListStore(int, str, bool, str, str)
        for cel in cel_list:
            lstore.append((cel['frame_number'], cel['description'],
                           cel['has_cel'], cel['fg_color'],
                           cel['bg_color']))
        return lstore
    
    def __add_columns(self, treeview):
        
        model = treeview.get_model()

        # frame column
        
        renderer = gtk.CellRendererText()
        renderer.set_data("column", COLUMN_FRAME_NUMBER)
        # renderer.set_property('background-set' , True)
        # renderer.set_property('foreground-set' , True)
        
        column = gtk.TreeViewColumn(_("Frame"))
        column.pack_start(renderer, True)
        column.set_attributes(renderer,
                              text=COLUMN_FRAME_NUMBER, 
                              # foreground=COLUMN_FG_COLOR,
                              # background=COLUMN_BG_COLOR,
                              )
        
        # fix column to 50 pixels:
        column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        column.set_fixed_width(50)
        
        treeview.append_column(column)
        
        # description column
        
        renderer = gtk.CellRendererText()
        renderer.set_data("column", COLUMN_DESCRIPTION)
        # renderer.set_property('background-set' , True)
        # renderer.set_property('foreground-set' , True)
        # renderer.set_property('background' , '#fff')
        # renderer.set_property('foreground' , '#000')
        renderer.set_property('editable' , True)
        renderer.connect("edited", self.on_cell_edited, model)
        
        column = gtk.TreeViewColumn(_("Description"))
        column.pack_start(renderer, True)
        column.set_attributes(renderer, text=COLUMN_DESCRIPTION)
        
        treeview.append_column(column)        

    def on_cell_edited(self, cell, path_string, new_text, model):
        
        it = model.get_iter_from_string(path_string)
        path = model.get_path(it)[0]
        column = cell.get_data("column")
        
        if column == COLUMN_DESCRIPTION:
            old_text = model.get_value(it, column)
            cel_list[path][COLUMN_DESCRIPTION] = new_text
            model.set(it, column, cel_list[path][COLUMN_DESCRIPTION])
        
