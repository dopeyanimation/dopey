import gtk

from gettext import gettext as _
import gobject


(
  COLUMN_FRAME_NUMBER,
  COLUMN_DESCRIPTION,
  COLUMN_HAS_CEL
) = range(3)

# test data:
cel_list = []
for i in range(1, 25):
    cel_list.append([i, "", False])


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

        lstore = gtk.ListStore(
            gobject.TYPE_UINT,
            gobject.TYPE_STRING,
            gobject.TYPE_BOOLEAN
            )
        
        for cel in cel_list:
            it = lstore.append()
            lstore.set(it,
                COLUMN_FRAME_NUMBER, cel[COLUMN_FRAME_NUMBER],
                COLUMN_DESCRIPTION, cel[COLUMN_DESCRIPTION],
                COLUMN_HAS_CEL, cel[COLUMN_HAS_CEL]
            )                      
        
        return lstore
    
    def __add_columns(self, treeview):
        
        model = treeview.get_model()

        # frame column
        renderer = gtk.CellRendererText()
        renderer.set_data("column", COLUMN_FRAME_NUMBER)

        column = gtk.TreeViewColumn(_("Frame"), renderer,
                               text=COLUMN_FRAME_NUMBER)

        # fix column to 50 pixels
        column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        column.set_fixed_width(50)

        treeview.append_column(column)

        # description column
        renderer = gtk.CellRendererText()
        renderer.connect("edited", self.on_cell_edited, model)
        renderer.set_data("column", COLUMN_DESCRIPTION)

        column = gtk.TreeViewColumn(_("Description"), renderer,
                               text=COLUMN_DESCRIPTION,
                               editable=False)
        treeview.append_column(column)        

    def on_cell_edited(self, cell, path_string, new_text, model):
        
        it = model.get_iter_from_string(path_string)
        path = model.get_path(it)[0]
        column = cell.get_data("column")
        
        if column == COLUMN_DESCRIPTION:
            old_text = model.get_value(it, column)
            cel_list[path][COLUMN_DESCRIPTION] = new_text
            model.set(it, column, cel_list[path][COLUMN_DESCRIPTION])
        
