#!/usr/bin/python

import os

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

def apply_mono_style(widget, mono_style):
	ctx = widget.get_style_context()
	ctx.add_provider(mono_style, Gtk.STYLE_PROVIDER_PRIORITY_USER)
	ctx.add_class("mono")

def load_local_script(fname):
	with open(fname) as f:
		return compile(f.read(), fname, "exec")

exec(load_local_script("io.py"))
exec(load_local_script("macros.py"))

mono_style = Gtk.CssProvider()
mono_style.load_from_data(b"""
	.mono {
		font-family: monospace;
	}
""")

io = IO()
macros = Macros()

window_names = ["I/O", "Macros"]
windows = []

def close_window(widget):
	idx = 0
	for w in windows:
		if widget == w:
			break
		idx += 1

	if idx >= len(windows):
		return

	windows[idx] = None
	for w in windows:
		if w is not None:
			return

	Gtk.main_quit()

def try_open_window(idx, obj):
	if windows[idx] is not None:
		return

	wnd, grid = create_window(idx)
	windows[idx] = wnd

	obj.populate_ui(wnd, grid, mono_style)
	wnd.show_all()

def macro_new(widget):
	macros.add_new_tab()

def macro_open(widget):
	macros.open_file()

def macro_save(widget):
	macros.save_current_tab()

def open_io_window(widget):
	try_open_window(0, io)

def open_macros_window(widget):
	try_open_window(1, macros)

def create_window(idx, wnd_w=600, wnd_h=400):
	window = Gtk.Window()
	window.set_title("Breakfast - " + window_names[idx])
	window.set_border_width(10)
	window.set_default_size(wnd_w, wnd_h)
	window.connect("destroy", close_window)

	wnd_x = 200 + (idx * 64)
	wnd_y = 200 + (idx * 48)
	window.move(wnd_x, wnd_y)

	grid = Gtk.Grid(hexpand=True, vexpand=True)
	grid.set_row_spacing(10)
	grid.set_column_spacing(10)
	window.add(grid)

	m_file = Gtk.Menu()
	m_wnds = Gtk.Menu()

	top_file = Gtk.MenuItem(label="File")
	top_file.set_submenu(m_file)
	file1 = Gtk.MenuItem(label="New")
	file1.connect("activate", macro_new)
	m_file.append(file1)
	file2 = Gtk.MenuItem(label="Open")
	file2.connect("activate", macro_open)
	m_file.append(file2)
	file3 = Gtk.MenuItem(label="Save")
	file3.connect("activate", macro_save)
	m_file.append(file3)

	top_wnds = Gtk.MenuItem(label="Window")
	top_wnds.set_submenu(m_wnds)

	wnds_io = Gtk.MenuItem(label="I/O")
	wnds_io.connect("activate", open_io_window)
	m_wnds.append(wnds_io)

	wnds_macros = Gtk.MenuItem(label="Macros")
	wnds_macros.connect("activate", open_macros_window)
	m_wnds.append(wnds_macros)

	mb = Gtk.MenuBar()
	mb.append(top_file)
	mb.append(top_wnds)
	grid.attach(mb, 0, 0, 1, 1)

	return (window, grid)

wnd_io, grid_io = create_window(0)
wnd_macros, grid_macros = create_window(1)

windows.append(wnd_io)
windows.append(wnd_macros)

io.populate_ui(wnd_io, grid_io, mono_style)
macros.populate_ui(wnd_macros, grid_macros, mono_style)

wnd_io.show_all()
wnd_macros.show_all()
Gtk.main()
