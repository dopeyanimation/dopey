import gtk

from gettext import gettext as _
import gobject

import dialogs
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
        self.listmodel = self.create_list(self.ani.cel_list)
        
        # create tree view:
        self.treeview = gtk.TreeView(self.listmodel)
        self.treeview.set_rules_hint(True)
        self.treeview.get_selection().set_mode(gtk.SELECTION_SINGLE)
        self.treeview.connect('row-activated', self.on_row_activated)
        
        self.add_columns()
        
        layers_scroll = gtk.ScrolledWindow()
        layers_scroll.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        layers_scroll.add_with_viewport(self.treeview)

        # controls:
        
        key_button = stock_button(gtk.STOCK_JUMP_TO)
        key_button.connect('clicked', self.on_toggle_key)
        key_button.set_tooltip_text(_('Toggle Keyframe'))
        
        chdesc_button = stock_button(gtk.STOCK_ITALIC)
        chdesc_button.connect('clicked', self.on_change_description)
        chdesc_button.set_tooltip_text(_('Change Cel Description'))
        
        add_button = stock_button(gtk.STOCK_ADD)
        add_button.connect('clicked', self.on_add_drawing)
        add_button.set_tooltip_text(_('Add Drawing to this Cel'))
        
        buttons_hbox = gtk.HBox()
        buttons_hbox.pack_start(key_button)
        buttons_hbox.pack_start(chdesc_button)
        buttons_hbox.pack_start(add_button)

        self.pack_start(layers_scroll)
        self.pack_start(buttons_hbox, expand=False)
        
        self.show_all()

        self.app.doc.model.doc_observers.append(self.update)
    
    def update(self, doc):
        self.queue_draw()
    
    def create_list(self, cel_list):
        listmodel = gtk.ListStore(object)
        for cel in cel_list:
            listmodel.append((cel,))
        return listmodel
    
    def add_columns(self):
        listmodel = self.treeview.get_model()
        
        # frame column
        
        cell = gtk.CellRendererText()
        cell.set_property('background-set' , True)
        
        column = gtk.TreeViewColumn(_("Frame"))
        column.pack_start(cell, True)
        column.set_cell_data_func(cell, self.set_frame)
        
        # fix column to 50 pixels:
        column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        column.set_fixed_width(50)
        
        self.treeview.append_column(column)
        
        # description column
        
        cell = gtk.CellRendererText()
        
        column = gtk.TreeViewColumn(_("Description"))
        column.pack_start(cell, True)
        column.set_cell_data_func(cell, self.set_description)

        self.treeview.append_column(column)        
    
    def on_row_activated(self, treeview, path, view_column):
        self.ani.select_cel(path[0])
        
    def activate_selected(self):
        """Activate the selected row. """
        treeselection = self.treeview.get_selection()
        model, it = treeselection.get_selected()
        path = model.get_path(it)
        self.ani.select_cel(path[0])
    
    def on_toggle_key(self, button):
        self.activate_selected()
        self.ani.toggle_key()
    
    def on_change_description(self, button):
        self.activate_selected()
        treeselection = self.treeview.get_selection()
        model, it = treeselection.get_selected()
        ani_cel = model.get_value(it, 0)
        
        description = dialogs.ask_for_name(self, _("Description"),
                                           ani_cel.description)
        if description:
            self.ani.change_description(ani_cel, description)
    
    def on_add_drawing(self, button):
        self.activate_selected()
        treeselection = self.treeview.get_selection()
        model, it = treeselection.get_selected()
        ani_cel = model.get_value(it, 0)
        
        self.ani.add_drawing(ani_cel)
    
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
