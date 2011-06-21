import gtk

from gettext import gettext as _
import gobject

import dialogs
from layerswindow import stock_button

from lib.framelist import DEFAULT_ACTIVE_CELS

COLUMNS_NAME = ('frame_index', 'frame_data', 'frame_icon')
COLUMNS_ID = dict((name, i) for i, name in enumerate(COLUMNS_NAME))

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
        
        def pixbuf_button(pixbuf):
            b = gtk.Button()
            img = gtk.Image()
            img.set_from_pixbuf(pixbuf)
            b.add(img)
            return b

        self.key_button = stock_button(gtk.STOCK_JUMP_TO)
        self.key_button.connect('clicked', self.on_toggle_key)
        self.key_button.set_tooltip_text(_('Toggle Keyframe'))
        
        self.chdesc_button = stock_button(gtk.STOCK_ITALIC)
        self.chdesc_button.connect('clicked', self.on_change_description)
        self.chdesc_button.set_tooltip_text(_('Change Cel Description'))
        
        pixbuf_add = self.app.pixmaps.cel_add
        self.add_cel_button = pixbuf_button(pixbuf_add)
        self.add_cel_button.connect('clicked', self.on_add_cel)
        self.add_cel_button.set_tooltip_text(_('Add cel to this frame'))
        
        pixbuf_remove = self.app.pixmaps.cel_remove
        self.remove_cel_button = pixbuf_button(pixbuf_remove)
        self.remove_cel_button.connect('clicked', self.on_remove_cel)
        self.remove_cel_button.set_tooltip_text(_('Remove cel of this frame'))
        
        buttons_hbox = gtk.HBox()
        buttons_hbox.pack_start(self.key_button)
        buttons_hbox.pack_start(self.chdesc_button)
        buttons_hbox.pack_start(self.add_cel_button)
        buttons_hbox.pack_start(self.remove_cel_button)

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
        
        insert_frame_button = stock_button(gtk.STOCK_ADD)
        insert_frame_button.connect('clicked', self.on_insert_frame)
        insert_frame_button.set_tooltip_text(_('Insert frame below selection'))
        self.insert_frame_button = insert_frame_button

        remove_frame_button = stock_button(gtk.STOCK_REMOVE)
        remove_frame_button.connect('clicked', self.on_remove_frame)
        remove_frame_button.set_tooltip_text(_('Remove frame below selection'))
        self.remove_frame_button = remove_frame_button

        cut_button = stock_button(gtk.STOCK_CUT)
        cut_button.connect('clicked', self.on_cut)
        cut_button.set_tooltip_text(_('Cut cel'))

        copy_button = stock_button(gtk.STOCK_COPY)
        copy_button.connect('clicked', self.on_copy)
        copy_button.set_tooltip_text(_('Copy cel'))

        paste_button = stock_button(gtk.STOCK_PASTE)
        paste_button.connect('clicked', self.on_paste)
        paste_button.set_tooltip_text(_('Paste cel'))

        editbuttons_hbox = gtk.HBox()
        editbuttons_hbox.pack_start(insert_frame_button)
        editbuttons_hbox.pack_start(remove_frame_button)
        editbuttons_hbox.pack_start(cut_button)
        editbuttons_hbox.pack_start(copy_button)
        editbuttons_hbox.pack_start(paste_button)
        
        # lightbox controls:

        adj = gtk.Adjustment(lower=0, upper=100, step_incr=1, page_incr=10)
        self.opacity_scale = gtk.HScale(adj)
        opa = self.app.preferences.get('lightbox.factor', 100)
        self.opacity_scale.set_value(opa)
        self.opacity_scale.set_value_pos(gtk.POS_LEFT)
        opacity_lbl = gtk.Label(_('Opacity:'))
        opacity_hbox = gtk.HBox()
        opacity_hbox.pack_start(opacity_lbl, expand=False)
        opacity_hbox.pack_start(self.opacity_scale, expand=True)
        self.opacity_scale.connect('value-changed', self.on_opacityfactor_changed)
        
        def opacity_checkbox(attr, label, tooltip=None):
            cb = gtk.CheckButton(label)
            pref = "lightbox.%s" % (attr,)
            default = DEFAULT_ACTIVE_CELS[attr]
            cb.set_active(self.app.preferences.get(pref, default))
            cb.connect('toggled', self.on_opacity_toggled, attr)
            if tooltip is not None:
                cb.set_tooltip_text(tooltip)
            opacityopts_vbox.pack_start(cb, expand=False)
        
        opacityopts_vbox = gtk.VBox()
        opacity_checkbox('nextprev', _('Inmediate'), _("Show the inmediate next and previous cels."))
        opacity_checkbox('key', _('Inmediate keys'), _("Show the cel keys that are after and before the current cel."))
        opacity_checkbox('inbetweens', _('Inbetweens'), _("Show the cels that are between the inmediate key cels."))
        opacity_checkbox('other keys', _('Other keys'), _("Show the other keys cels."))
        opacity_checkbox('other', _('Other'), _("Show the rest of the cels."))
        
        self.pack_start(layers_scroll)
        self.pack_start(buttons_hbox, expand=False)
        self.pack_start(anibuttons_hbox, expand=False)
        self.pack_start(editbuttons_hbox, expand=False)
        self.pack_start(opacity_hbox, expand=False)
        self.pack_start(opacityopts_vbox, expand=False)
        
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
        column = self.treeview.get_column(2)
        cell = column.get_cell_renderers()[0]
        column.set_cell_data_func(cell, self.set_icon)
        
        # reconnect treeview:
        self.treeview.set_model(self.listmodel)
        
        treesel.handler_unblock(self.changed_handler)
        
        self.setup_lightbox()
    
    def _update(self):
        if self.ani.cleared:
            self.setup()
            self.ani.cleared = False
        
        frame = self.ani.frames.get_selected()
        path = self._get_path_from_frame(frame)
        self.treeview.get_selection().select_path(path)
        self.treeview.scroll_to_cell(path)
        self.queue_draw()
        self._update_buttons_sensitive()
        
        if self.ani.penciltest_state == "play":
            self._play_penciltest()
    
    def update(self, doc):
        return self._update()

    def create_list(self):
        xsheet_list = list(enumerate(self.ani.frames))
        listmodel = gtk.ListStore(int, object)
        for i, frame in xsheet_list:
            listmodel.append((i, frame))
        return listmodel
    
    def add_columns(self):
        listmodel = self.treeview.get_model()
        
        # frame number column
        
        cell = gtk.CellRendererText()
#        cell.set_property('background-set' , True)
        
        column = gtk.TreeViewColumn(_("Frame"))
        column.pack_start(cell, True)
        column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        column.set_fixed_width(50)
        column.set_cell_data_func(cell, self.set_number)
        
        self.treeview.append_column(column)
        
        # description column
        
        cell = gtk.CellRendererText()
#        cell.set_property('background-set' , True)
        
        column = gtk.TreeViewColumn(_("Description"))
        column.pack_start(cell, True)
        column.set_cell_data_func(cell, self.set_description)

        self.treeview.append_column(column)
    
        # icon column
        
        cell = gtk.CellRendererPixbuf()
        column = gtk.TreeViewColumn(_("Status"))
        column.pack_start(cell, expand=False)
        column.add_attribute(cell, 'pixbuf', 0)
        column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        column.set_fixed_width(50)
        column.set_cell_data_func(cell, self.set_icon)
        
        self.treeview.append_column(column)
        
    def _change_penciltest_buttons(self, is_playing):
        if is_playing:
            self.play_button.hide()
            self.pause_button.show()
        else:
            self.play_button.show()
            self.pause_button.hide()
        self.stop_button.set_sensitive(is_playing)

    def _update_buttons_sensitive(self):
        self.previous_button.set_sensitive(self.ani.frames.has_previous())
        self.next_button.set_sensitive(self.ani.frames.has_next())
        
        f = self.ani.frames.get_selected()
        if f.cel is None:
            self.add_cel_button.show()
            self.remove_cel_button.hide()
        else:
            self.add_cel_button.hide()
            self.remove_cel_button.show()
    
    def on_row_changed(self, treesel):
        model, it = treesel.get_selected()
        path = model.get_path(it)
        self.ani.select_frame(path[COLUMNS_ID['frame_index']])
        self._update_buttons_sensitive()
        
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
        
    def set_description(self, column, cell, model, it):
        frame = model.get_value(it, COLUMNS_ID['frame_data'])
        cell.set_property('text', frame.description)
        
    def set_icon(self, column, cell, model, it):
        frame = model.get_value(it, COLUMNS_ID['frame_data'])
        pixname = 'frame'
        if frame.cel is not None:
            pixname += '_cel'
        if frame.is_key:
            pixname = 'key' + pixname
        pixbuf = getattr(self.app.pixmaps, pixname)
        cell.set_property('pixbuf', pixbuf)

    def _call_penciltest(self):
        self.ani.penciltest_next()
        keep_playing = True
        if self.ani.penciltest_state == "stop":
            self.ani.select_without_undo(self.beforeplay_frame)
            keep_playing = False
            self._change_penciltest_buttons(keep_playing)
            self.ani.penciltest_state = None
            self._update()
        elif self.ani.penciltest_state == "pause":
            keep_playing = False
            self._change_penciltest_buttons(keep_playing)
            self.ani.penciltest_state = None
            self._update()
        return keep_playing

    def _play_penciltest(self):
        self.beforeplay_frame = self.ani.frames.idx
        self._change_penciltest_buttons(is_playing=True)
        # add a 24fps (almost 42ms) animation timer:
        gobject.timeout_add(42, self._call_penciltest)

    def on_penciltest_play(self, button):
        self.ani.play_penciltest()

    def on_penciltest_pause(self, button):
        self.ani.pause_penciltest()

    def on_penciltest_stop(self, button):
        self.ani.stop_penciltest()

    def on_opacityfactor_changed(self, *ignore):
        opa = self.opacity_scale.get_value()
        self.app.preferences["lightbox.factor"] = opa
        self.ani.change_opacityfactor(opa/100.0)
        self.queue_draw()

    def on_opacity_toggled(self, checkbox, attr):
        pref = "lightbox.%s" % (attr,)
        self.app.preferences[pref] = checkbox.get_active()
        self.ani.toggle_opacity(attr, checkbox.get_active())
        self.queue_draw()

    def on_insert_frame(self, button):
        self.ani.insert_frames()

    def on_remove_frame(self, button):
        self.ani.remove_frames()

    def on_cut(self, button):
        self.ani.cutcopy_cel('cut')

    def on_copy(self, button):
        self.ani.cutcopy_cel('copy')

    def on_paste(self, button):
        self.ani.paste_cel()
