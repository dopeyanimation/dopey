# This file is part of MyPaint.
# Copyright (C) 2009 by Martin Renold <martinxyz@gmx.ch>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import gtk
from gettext import gettext as _

def ask_for(widget, title, ask_text, default):
    window = widget.get_toplevel()
    d = gtk.Dialog(title,
                   window,
                   gtk.DIALOG_MODAL,
                   (gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,
                    gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))

    hbox = gtk.HBox()
    d.vbox.pack_start(hbox)
    hbox.pack_start(gtk.Label(ask_text))

    d.e = e = gtk.Entry()
    e.set_text(default)
    e.select_region(0, len(default))
    def responseToDialog(entry, dialog, response):  
        dialog.response(response)  
    e.connect("activate", responseToDialog, d, gtk.RESPONSE_ACCEPT)  

    hbox.pack_start(e)
    d.vbox.show_all()
    if d.run() == gtk.RESPONSE_ACCEPT:
        result = d.e.get_text().decode('utf-8')
    else:
        result = None
    d.destroy()
    return result
