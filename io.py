import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

class IO:
	def populate_ui(self, window, grid, mono_style):
		filter_bar = Gtk.Entry(hexpand=True)
		apply_mono_style(filter_bar, mono_style)
		grid.attach(filter_bar, 0, 1, 2, 1)

		filter_cb = Gtk.CheckButton()
		grid.attach(filter_cb, 2, 1, 1, 1)

		textview = Gtk.TextView(hexpand=True, vexpand=True, editable=False)
		apply_mono_style(textview, mono_style)
		grid.attach(textview, 0, 2, 3, 1)

		out_bar = Gtk.Entry(hexpand=True)
		apply_mono_style(out_bar, mono_style)
		grid.attach(out_bar, 0, 3, 1, 1)

		out_btn = Gtk.Button(label="Send")
		grid.attach(out_btn, 1, 3, 2, 1)
