import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
from gi.repository import Gdk

def get_textview_text(tv):
	buf = tv.get_buffer()
	return buf.get_text(buf.get_start_iter(), buf.get_end_iter(), True)

def execute_listener(widget):
	widget.tab_ref.execute()

def submit_listener(widget):
	widget.tab_ref.submit()

def buffer_listener(widget, data=None):
	widget.tab_ref.send_buffer_changed()

def entry_listener(widget, ev, data=None):
	if ev.keyval == Gdk.KEY_Return:
		widget.tab_ref.submit()

def direct_listener(widget, ev, data=None):
	widget.tab_ref.send_direct_event(ev)
	return True

class Tab:
	def __init__(self):
		self.macro = {}
		self.on_buffer_changed = None
		self.on_command = None
		self.on_direct_event = None

	def log(self, msg):
		text = str(msg)
		if text[-1] != "\n":
			text += "\n"

		buf = self.cmd_tv.get_buffer()
		buf.insert(buf.get_end_iter(), text)

		adj = self.cmd_scroller.get_vadjustment()
		adj.set_value(adj.get_upper())

	def get_buffer(self):
		return get_textview_text(self.buffer_tv)

	def set_buffer(self, text):
		buf = self.buffer_tv.get_buffer()
		buf.connect("changed", None)
		buf.set_text(text)
		buf.connect("changed", buffer_listener)

	def execute(self):
		code = compile(get_textview_text(self.code_tv), "<string>", "exec")

		self.macro = {}
		self.macro["macro"] = self
		exec(code, self.macro)

		self.on_buffer_changed = None
		self.on_command = None
		self.on_direct_event = None

		for k in self.macro:
			v = self.macro[k]
			if callable(v):
				if k == "on_buffer_changed":
					self.on_buffer_changed = v
				elif k == "on_command":
					self.on_command = v
				elif k == "on_direct_event":
					self.on_direct_event = v

	def submit(self):
		buf = self.cmd_entry.get_buffer()
		text = buf.get_text()
		buf.set_text("", -1)

		self.log("> " + text + "\n")

		if self.on_command is not None:
			self.on_command(text)

	def send_buffer_changed(self):
		if self.on_buffer_changed is not None:
			self.on_buffer_changed()

	def send_direct_event(self, ev):
		if self.on_direct_event is None:
			return

		event_type = ""
		value = 0
		x = 0
		y = 0

		if ev.type == Gdk.EventType.KEY_PRESS:
			event_type = "keydown"
			value = ev.keyval
		elif ev.type == Gdk.EventType.KEY_RELEASE:
			event_type = "keyup"
			value = ev.keyval
		elif ev.type == Gdk.EventType.BUTTON_PRESS:
			event_type = "mousedown"
			value = ev.button
			x = ev.x
			y = ev.y
		elif ev.type == Gdk.EventType.BUTTON_RELEASE:
			event_type = "mouseup"
			value = ev.button
			x = ev.x
			y = ev.y
		elif ev.type == Gdk.EventType.MOTION_NOTIFY:
			event_type = "mousemove"
			x = ev.x
			y = ev.y

		self.on_direct_event(event_type, value, x, y)

	def produce_ui(self, window, mono_style, code_text):
		code_grid = Gtk.Grid(hexpand=True, vexpand=True)
		self.code_tv = Gtk.TextView(hexpand=True, vexpand=True)
		apply_mono_style(self.code_tv, mono_style)
		self.code_tv.get_buffer().set_text(code_text)

		exec_btn = Gtk.Button(label="Execute", halign=Gtk.Align.END)
		exec_btn.connect("clicked", execute_listener)
		exec_btn.tab_ref = self

		code_grid.attach(self.code_tv, 0, 0, 2, 1)
		code_grid.attach(exec_btn, 1, 1, 1, 1)

		self.buffer_tv = Gtk.TextView(hexpand=True, vexpand=True)
		apply_mono_style(self.buffer_tv, mono_style)
		buf = self.buffer_tv.get_buffer()
		buf.tab_ref = self
		buf.connect("changed", buffer_listener)

		cmd_grid = Gtk.Grid(hexpand=True, vexpand=True)

		self.cmd_tv = Gtk.TextView(hexpand=True, vexpand=True, editable=False)
		apply_mono_style(self.cmd_tv, mono_style)

		self.cmd_scroller = Gtk.ScrolledWindow()
		self.cmd_scroller.add(self.cmd_tv)

		self.cmd_entry = Gtk.Entry(hexpand=True)
		apply_mono_style(self.cmd_entry, mono_style)
		self.cmd_entry.connect("key-press-event", entry_listener)
		self.cmd_entry.tab_ref = self

		cmd_btn = Gtk.Button(label="Submit", halign=Gtk.Align.END)
		cmd_btn.tab_ref = self
		cmd_btn.connect("clicked", submit_listener)

		cmd_grid.attach(self.cmd_scroller, 0, 0, 2, 1)
		cmd_grid.attach(self.cmd_entry, 0, 1, 1, 1)
		cmd_grid.attach(cmd_btn, 1, 1, 1, 1)

		self.draw_area = Gtk.DrawingArea(can_focus=True, events=Gdk.EventMask.ALL_EVENTS_MASK)
		self.draw_area.tab_ref = self
		self.draw_area.connect("key-press-event", direct_listener)
		self.draw_area.connect("key-release-event", direct_listener)
		self.draw_area.connect("button-press-event", direct_listener)
		self.draw_area.connect("button-release-event", direct_listener)
		self.draw_area.connect("scroll-event", direct_listener)
		self.draw_area.connect("motion-notify-event", direct_listener)

		tab_ui = Gtk.Notebook()
		tab_ui.append_page(code_grid, Gtk.Label(label="Code"))
		tab_ui.append_page(self.buffer_tv, Gtk.Label(label="Buffer"))
		tab_ui.append_page(cmd_grid, Gtk.Label(label="Command"))
		tab_ui.append_page(self.draw_area, Gtk.Label(label="Direct"))

		return tab_ui

class Macros:
	def __init__(self):
		self.tabs = {}

	def read_config(self, config):
		files_temp = {}

		for l in config:
			if os.path.exists(l):
				with open(l, "r") as f:
					files_temp[l] = f.read()
					self.tabs[l] = Tab()

		return files_temp

	def populate_ui(self, window, grid, mono_style):
		files_temp = {}

		if os.path.exists("config.cfg"):
			with open("config.cfg") as f:
				config = f.read().splitlines()
				files_temp = self.read_config(config)
		else:
			if "Untitled" not in self.tabs:
				self.tabs["Untitled"] = Tab()

		notebook = Gtk.Notebook()
		for t in self.tabs:
			close_image = Gtk.Image(xpad=0, ypad=0)
			close_image.set_from_icon_name("window-close-symbolic", Gtk.IconSize.SMALL_TOOLBAR)

			header = Gtk.HBox(spacing=8)
			header.pack_start(Gtk.Label(label=t), True, True, 0)
			header.pack_end(Gtk.Button(image=close_image, relief=Gtk.ReliefStyle.NONE), False, False, 0)
			header.show_all()

			code_text = ""
			if t in files_temp:
				code_text = files_temp[t]

			page = self.tabs[t].produce_ui(window, mono_style, code_text)
			notebook.append_page(page, header)

		grid.attach(notebook, 0, 1, 1, 1)

	def add_new_tab(self):
		name = "Untitled"
		num = 1

		for i in range(0, 100):
			if name not in self.tabs:
				self.tabs[name] = Tab()
				return

			num += 1
			name = "Untitled " + str(num)

	def open_file(self):
		dialog = Gtk.FileChooserDialog(title="Open Script", action=Gtk.FileChooserAction.OPEN)
		dialog.add_button(Gtk.STOCK_OPEN, Gtk.ResponseType.ACCEPT)
		dialog.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)

		res = dialog.run()
		if res == Gtk.ResponseType.ACCEPT:
			name = dialog.get_filename()
			print(name)

		dialog.destroy()

	def save_current_tab(self):
		pass

