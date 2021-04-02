#!/usr/bin/python

import os
import sys
import traceback

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

green_style = Gtk.CssProvider()
green_style.load_from_data(b"""
	.green {
		background-color: #8ea;
		color: black;
	}
""")

io = IO()
macros = Macros()

def close_window(widget):
	Gtk.main_quit()

def macro_new(widget, window):
	macros.add_new_tab()
	macros.populate_notebook()
	macros.window.show_all()

def macro_open(widget, window):
	macros.open_file()

def macro_save(widget, window):
	macros.save_current_tab()

def connect_press_listener(widget, ev, ui):
	if ev.keyval == Gdk.KEY_Return:
		ui.connect()

def send_press_listener(widget, ev, ui):
	if ev.keyval == Gdk.KEY_Return:
		ui.send()

class UI:
	def __init__(self):
		self.window = Gtk.Window()
		self.window.set_title("Breakfast")
		self.window.set_border_width(10)

		wnd_w = 600
		wnd_h = 400
		self.window.set_default_size(wnd_w, wnd_h)

		wnd_x = 200
		wnd_y = 200
		self.window.move(wnd_x, wnd_y)

		self.window.connect("destroy", close_window)

		accel = Gtk.AccelGroup()
		self.window.add_accel_group(accel)

		self.grid = Gtk.Grid(hexpand=True, vexpand=True)
		self.grid.set_row_spacing(10)
		self.grid.set_column_spacing(10)
		self.window.add(self.grid)

		m_file = Gtk.Menu()
		m_wnds = Gtk.Menu()

		top_file = Gtk.MenuItem(label="File")
		top_file.set_submenu(m_file)

		file1 = Gtk.MenuItem(label="New")
		file1.connect("activate", macro_new, self.window)
		file1.add_accelerator("activate", accel, Gdk.KEY_n, Gdk.ModifierType.CONTROL_MASK, Gtk.AccelFlags.VISIBLE)
		m_file.append(file1)

		file2 = Gtk.MenuItem(label="Open")
		file2.connect("activate", macro_open, self.window)
		file2.add_accelerator("activate", accel, Gdk.KEY_o, Gdk.ModifierType.CONTROL_MASK, Gtk.AccelFlags.VISIBLE)
		m_file.append(file2)

		file3 = Gtk.MenuItem(label="Save")
		file3.connect("activate", macro_save, self.window)
		file3.add_accelerator("activate", accel, Gdk.KEY_s, Gdk.ModifierType.CONTROL_MASK, Gtk.AccelFlags.VISIBLE)
		m_file.append(file3)

		mb = Gtk.MenuBar()
		mb.append(top_file)
		self.grid.attach(mb, 0, 0, 1, 1)

		self.device_bar = Gtk.Entry(hexpand=True)
		self.device_bar.io_ref = self
		self.device_bar.connect("key-press-event", connect_press_listener, self)

		apply_mono_style(self.device_bar, mono_style)
		self.device_bar.get_style_context().add_provider(green_style, Gtk.STYLE_PROVIDER_PRIORITY_USER)

		self.grid.attach(self.device_bar, 0, 1, 1, 1)

		device_btn = Gtk.Button(label="Connect")
		device_btn.connect("clicked", lambda widget, ui : ui.connect(), self)
		self.grid.attach(device_btn, 1, 1, 1, 1)

		self.notebook = Gtk.Notebook(hexpand=True, vexpand=True)
		self.grid.attach(self.notebook, 0, 2, 2, 1)

		self.out_bar = Gtk.Entry(hexpand=True)
		self.out_bar.connect("key-press-event", send_press_listener, self)
		apply_mono_style(self.out_bar, mono_style)
		self.grid.attach(self.out_bar, 0, 3, 1, 1)

		out_btn = Gtk.Button(label="Send")
		out_btn.connect("clicked", lambda widget, ui : ui.send(), self)
		self.grid.attach(out_btn, 1, 3, 1, 1)

	def connect(self):
		io.try_connect(self.device_bar.get_text())

	def send(self):
		s = self.out_bar.get_text()
		self.out_bar.set_text("")
		io.send_byte_string(s)

ui = UI()
macros.populate_notebook()
ui.window.show_all()

try:
	Gtk.main()
except BaseException as e:
	traceback.print_exc()
	pass

io.comms.close()
