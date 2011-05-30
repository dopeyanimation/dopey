import gtk

from gettext import gettext as _
import gobject

import dialogs
from layerswindow import stock_button

from lib.framelist import DEFAULT_ACTIVE_CELS

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
        self.ani = app.doc.ani.model
        self.set_size_request(200, 150)
        
        # create list:
        self.listmodel = self.create_list()
        
        # create tree view:
        self.treeview = gtk.TreeView(self.listmodel)
        self.treeview.set_rules_hint(True)
        treesel = self.treeview.get_selection()
        treesel.set_mode(gtk.SELECTION_SINGLE)
        self.changed_handler = treesel.connect('changed', self.on_row_changed)
        
        self.add_columns()
        
        layers_scroll = gtk.ScrolledWindow()
        layers_scroll.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        layers_scroll.add(self.treeview)

        # xsheet controls:
        
        self.key_button = stock_button(gtk.STOCK_JUMP_TO)
        self.key_button.connect('clicked', self.on_toggle_key)
        self.key_button.set_tooltip_text(_('Toggle Keyframe'))
        
        self.chdesc_button = stock_button(gtk.STOCK_ITALIC)
        self.chdesc_button.connect('clicked', self.on_change_description)
        self.chdesc_button.set_tooltip_text(_('Change Cel Description'))
        
        self.add_button = stock_button(gtk.STOCK_ADD)
        self.add_button.connect('clicked', self.on_add_cel)
        self.add_button.set_tooltip_text(_('Add cel to this frame'))
        
        self.remove_button = stock_button(gtk.STOCK_REMOVE)
        self.remove_button.connect('clicked', self.on_remove_cel)
        self.remove_button.set_tooltip_text(_('Remove cel of this frame'))
        
        buttons_hbox = gtk.HBox()
        buttons_hbox.pack_start(self.key_button)
        buttons_hbox.pack_start(self.chdesc_button)
        buttons_hbox.pack_start(self.add_button)
        buttons_hbox.pack_start(self.remove_button)

        # penciltest controls:
        
        self.previous_button = stock_button(gtk.STOCK_GO_UP)
        self.previous_button.connect('clicked', self.on_previous_frame)
        self.previous_button.set_tooltip_text(_('Previous Frame'))
        
        self.next_button = stock_button(gtk.STOCK_GO_DOWN)
        self.next_button.connect('clicked', self.on_next_frame)
        self.next_button.set_tooltip_text(_('Next Frame'))
        
        self.play_button = stock_button(gtk.STOCK_MEDIA_PLAY)
        self.play_button.connect('clicked', self.on_penciltest_play)
        self.play_button.set_tooltip_text(_('Pencil Test'))
        
        self.pause_button = stock_button(gtk.STOCK_MEDIA_PAUSE)
        self.pause_button.connect('clicked', self.on_penciltest_pause)
        self.pause_button.set_tooltip_text(_('Pause Pencil Test'))

        self.stop_button = stock_button(gtk.STOCK_MEDIA_STOP)
        self.stop_button.connect('clicked', self.on_penciltest_stop)
        self.stop_button.set_tooltip_text(_('Stop Pencil Test'))

        anibuttons_hbox = gtk.HBox()
        anibuttons_hbox.pack_start(self.previous_button)
        anibuttons_hbox.pack_start(self.next_button)
        anibuttons_hbox.pack_start(self.play_button)
        anibuttons_hbox.pack_start(self.pause_button)
        anibuttons_hbox.pack_start(self.stop_button)

        # frames edit controls:
        
        insert_button = stock_button(gtk.STOCK_ADD)
        insert_button.connect('clicked', self.on_insert)
        insert_button.set_tooltip_text(_('Insert two frames below selection'))

        pop_button = stock_button(gtk.STOCK_REMOVE)
        pop_button.connect('clicked', self.on_pop)
        pop_button.set_tooltip_text(_('Remove two frames below selection'))

        editbuttons_hbox = gtk.HBox()
        editbuttons_hbox.pack_start(insert_button)
        editbuttons_hbox.pack_start(pop_button)
        
        # lightbox controls:
        
        def opacity_checkbox(attr, label, tooltip=None):
            cb = gtk.CheckButton(label)
            pref = "lightbox.%s" % (attr,)
            default = DEFAULT_ACTIVE_CELS[attr]
            cb.set_active(self.app.preferences.get(pref, default))
            cb.connect('toggled', self.on_opacity_toggled, attr)
            if tooltip is not None:
                cb.set_tooltip_text(tooltip)
            opacity_vbox.pack_start(cb, expand=False)
        
        opacity_vbox = gtk.VBox()
        opacity_checkbox('current', _('Current cel'), _("Show the current cel."))
        opacity_checkbox('nextprev', _('Inmediate cels'), _("Show the inmediate next and previous cels."))
        opacity_checkbox('key', _('Show inmediate keys'), _("Show the cel keys that are after and before the current cel."))
        opacity_checkbox('inbetweens', _('Inbetweens'), _("Show the cels that are between the inmediate key cels."))
        opacity_checkbox('other keys', _('Other keys'), _("Show the other keys cels."))
        opacity_checkbox('other', _('Other cels'), _("Show the rest of the cels."))
        
        self.pack_start(layers_scroll)
        self.pack_start(buttons_hbox, expand=False)
        self.pack_start(anibuttons_hbox, expand=False)
        self.pack_start(editbuttons_hbox, expand=False)
        self.pack_start(opacity_vbox, expand=False)
        
        self.show_all()
        self._change_penciltest_buttons(is_playing=False)
        self.app.doc.model.doc_observers.append(self.update)
        
    def _get_path_from_frame(self, frame):
        return (self.ani.frames.idx, )
    
    def setup_lightbox(self):
        active_cels = {}
        for attr, default in DEFAULT_ACTIVE_CELS.items():
            pref = "lightbox.%s" % (attr,)
            default = DEFAULT_ACTIVE_CELS[attr]
            active_cels[attr] = self.app.preferences.get(pref, default)
        self.ani.frames.setup_active_cels(active_cels)
    
    def setup(self):
        treesel = self.treeview.get_selection()
        treesel.handler_block(self.changed_handler)

        # disconnect treeview so it doesn't update for each row added:
        self.treeview.set_model(None)
        
        self.listmodel.clear()
        xsheet_list = list(enumerate(self.ani.frames))
        for i, frame in xsheet_list:
            self.listmodel.append((i, frame))
        
        column = self.treeview.get_column(0)
        cell = column.get_cell_renderers()[0]
        column.set_cell_data_func(cell, self.set_number)
        column = self.treeview.get_column(1)
        cell = column.get_cell_renderers()[0]
        column.set_cell_data_func(cell, self.set_description)
        
        # reconnect treeview:
        self.treeview.set_model(self.listmodel)
        
        treesel.handler_unblock(self.changed_handler)
        
        self.setup_lightbox()
    
    def update(self, doc):
        if self.ani.cleared:
            self.setup()
            self.ani.cleared = False
        
        frame = self.ani.frames.get_selected()
        path = self._get_path_from_frame(frame)
        self.treeview.get_selection().select_path(path)
        self.treeview.scroll_to_cell(path)
        self.queue_draw()
        self._change_buttons()
    
    def create_list(self):
        xsheet_list = list(enumerate(self.ani.frames))
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
    
    def _change_penciltest_buttons(self, is_playing):
        if is_playing:
            self.play_button.hide()
            self.pause_button.show()
        else:
            self.play_button.show()
            self.pause_button.hide()
        self.stop_button.set_sensitive(is_playing)

    def _change_buttons(self):
        self.previous_button.set_sensitive(self.ani.frames.has_previous())
        self.next_button.set_sensitive(self.ani.frames.has_next())
        
        f = self.ani.frames.get_selected()
        if f.cel is None:
            self.add_button.show()
            self.remove_button.hide()
        else:
            self.add_button.hide()
            self.remove_button.show()
    
    def on_row_changed(self, treesel):
        model, it = treesel.get_selected()
        path = model.get_path(it)
        self.ani.select_frame(path[COLUMNS_ID['frame_index']])
        self._change_buttons()
        
    def on_toggle_key(self, button):
        self.ani.toggle_key()
    
    def on_previous_frame(self, button):
        self.ani.previous_frame()
    
    def on_next_frame(self, button):
        self.ani.next_frame()
    
    def on_change_description(self, button):
        treesel = self.treeview.get_selection()
        model, it = treesel.get_selected()
        frame = model.get_value(it, COLUMNS_ID['frame_data'])
        
        description = dialogs.ask_for_name(self, _("Description"),
                                           frame.description)
        if description:
            self.ani.change_description(description)
    
    def on_add_cel(self, button):
        self.ani.add_cel()
    
    def on_remove_cel(self, button):
        self.ani.remove_cel()
    
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

    def _call_penciltest(self):
        has_next_frame = self.ani.penciltest_next()
        keep_playing = True
        if not has_next_frame or self.penciltest_state == "stop":
            self.ani.select_without_undo(self.beforeplay_frame)
            keep_playing = False
            self._change_penciltest_buttons(keep_playing)
        if self.penciltest_state == "pause":
            keep_playing = False
            self._change_penciltest_buttons(keep_playing)
        return keep_playing

    def on_penciltest_play(self, button):
        """
        Add a 24fps (almost 42ms) animation timer.

        """
        self.beforeplay_frame = self.ani.frames.idx
        self.penciltest_state = "play"
        self._change_penciltest_buttons(is_playing=True)
        bla = gobject.timeout_add(42, self._call_penciltest)

    def on_penciltest_pause(self, button):
        self.penciltest_state = "pause"

    def on_penciltest_stop(self, button):
        self.penciltest_state = "stop"

    def on_opacity_toggled(self, checkbox, attr):
        pref = "lightbox.%s" % (attr,)
        self.app.preferences[pref] = checkbox.get_active()
        self.ani.toggle_opacity(attr, checkbox.get_active())
        self.queue_draw()

    def on_insert(self, button):
        self.ani.insert_frames()

    def on_pop(self, button):
        self.ani.pop_frames()
        
