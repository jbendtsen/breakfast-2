import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
from gi.repository import Gdk

def get_textview_text(tv):
	buf = tv.get_buffer()
	return buf.get_text(buf.get_start_iter(), buf.get_end_iter(), True)

class Tab:
	def close_button_listener(widget):
		page = widget.get_parent().page_ref
		page.tab_ref.macros_ref.close_tab(page)

	def execute_listener(widget):
		widget.tab_ref.execute()

	def submit_listener(widget):
		widget.tab_ref.submit()

	def buffer_listener(widget, data=None):
		if not widget.tab_ref.disable_buffer_change_event:
			widget.tab_ref.send_buffer_changed()

	def entry_listener(widget, ev, data=None):
		if ev.keyval == Gdk.KEY_Return:
			widget.tab_ref.submit()

	def direct_listener(widget, ev, data=None):
		widget.tab_ref.send_direct_event(ev)
		return True

	def name_from_path(path):
		name = path

		if path[0] == '&':
			name = path[1:]
		else:
			start = path.rfind('/') + 1
			name = path[start:]

		return name

	def __init__(self, path, macros):
		self.macros_ref = macros
		self.macro = {}
		self.disable_buffer_change_event = False
		self.on_buffer_changed = None
		self.on_command = None
		self.on_direct_event = None

		self.id = path
		self.name = Tab.name_from_path(self.id)

	def log(self, msg):
		text = str(msg)
		if len(text) == 0 or text[-1] != "\n":
			text += "\n"

		buf = self.cmd_tv.get_buffer()
		buf.insert(buf.get_end_iter(), text)

		adj = self.cmd_scroller.get_vadjustment()
		adj.set_value(adj.get_upper())

	def get_buffer(self):
		return get_textview_text(self.buffer_tv)

	def set_buffer(self, text):
		buf = self.buffer_tv.get_buffer()
		self.disable_buffer_change_event = True
		buf.set_text(text)
		self.disable_buffer_change_event = False

	def execute(self):
		try:
			code = compile(get_textview_text(self.code_tv), self.name, "exec")
		except BaseException as e:
			self.log("".join(traceback.format_exception_only(type(e), e)))
			return

		self.macro = {}
		self.macro["macro"] = self

		try:
			exec(code, self.macro)
		except BaseException as e:
			trace = traceback.extract_tb(sys.exc_info()[2])
			exc = "".join(traceback.format_exception_only(type(e), e))
			self.log("".join(traceback.format_list(trace[1:])) + exc)

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
		elif ev.type == Gdk.EventType.MOTTabN_NOTIFY:
			event_type = "mousemove"
			x = ev.x
			y = ev.y

		self.on_direct_event(event_type, value, x, y)

	def produce_ui(self, window, mono_style, code_text):
		code_grid = Gtk.Grid(hexpand=True, vexpand=True)
		self.code_tv = Gtk.TextView(hexpand=True, vexpand=True)
		apply_mono_style(self.code_tv, mono_style)
		self.code_tv.get_buffer().set_text(code_text)

		code_scroller = Gtk.ScrolledWindow()
		code_scroller.add(self.code_tv)

		exec_btn = Gtk.Button(label="Execute", halign=Gtk.Align.END)
		exec_btn.connect("clicked", Tab.execute_listener)
		exec_btn.tab_ref = self

		code_grid.attach(code_scroller, 0, 0, 2, 1)
		code_grid.attach(exec_btn, 1, 1, 1, 1)

		self.buffer_tv = Gtk.TextView(hexpand=True, vexpand=True)
		apply_mono_style(self.buffer_tv, mono_style)
		buf = self.buffer_tv.get_buffer()
		buf.tab_ref = self
		buf.connect("changed", Tab.buffer_listener)

		buffer_scroller = Gtk.ScrolledWindow()
		buffer_scroller.add(self.buffer_tv)

		cmd_grid = Gtk.Grid(hexpand=True, vexpand=True)

		self.cmd_tv = Gtk.TextView(hexpand=True, vexpand=True, editable=False)
		apply_mono_style(self.cmd_tv, mono_style)

		self.cmd_scroller = Gtk.ScrolledWindow()
		self.cmd_scroller.add(self.cmd_tv)

		self.cmd_entry = Gtk.Entry(hexpand=True)
		apply_mono_style(self.cmd_entry, mono_style)
		self.cmd_entry.connect("key-press-event", Tab.entry_listener)
		self.cmd_entry.tab_ref = self

		cmd_btn = Gtk.Button(label="Submit", halign=Gtk.Align.END)
		cmd_btn.tab_ref = self
		cmd_btn.connect("clicked", Tab.submit_listener)

		cmd_grid.attach(self.cmd_scroller, 0, 0, 2, 1)
		cmd_grid.attach(self.cmd_entry, 0, 1, 1, 1)
		cmd_grid.attach(cmd_btn, 1, 1, 1, 1)

		self.draw_area = Gtk.DrawingArea(can_focus=True, events=Gdk.EventMask.ALL_EVENTS_MASK)
		self.draw_area.tab_ref = self
		self.draw_area.connect("key-press-event", Tab.direct_listener)
		self.draw_area.connect("key-release-event", Tab.direct_listener)
		self.draw_area.connect("button-press-event", Tab.direct_listener)
		self.draw_area.connect("button-release-event", Tab.direct_listener)
		self.draw_area.connect("scroll-event", Tab.direct_listener)
		self.draw_area.connect("motion-notify-event", Tab.direct_listener)

		tab_ui = Gtk.Notebook()
		tab_ui.append_page(code_grid, Gtk.Label(label="Code"))
		tab_ui.append_page(buffer_scroller, Gtk.Label(label="Buffer"))
		tab_ui.append_page(cmd_grid, Gtk.Label(label="Command"))
		tab_ui.append_page(self.draw_area, Gtk.Label(label="Direct"))

		tab_ui.tab_ref = self
		return tab_ui

class Macros:
	def __init__(self):
		self.tabs = {}
		self.notebook = None

	def add_new_tab(self):
		name = "&Untitled"
		num = 1

		for i in range(0, 100):
			if name not in self.tabs:
				self.tabs[name] = Tab(name, self)
				return

			num += 1
			name = "&Untitled " + str(num)

	def read_config(self, config):
		files_temp = {}

		for l in config:
			if os.path.exists(l):
				with open(l, "r") as f:
					files_temp[l] = f.read()
					self.tabs[l] = Tab(l, self)

		return files_temp

	def populate_notebook(self):
		files_temp = {}

		if os.path.exists("config.cfg"):
			with open("config.cfg") as f:
				config = f.read().splitlines()
				files_temp = self.read_config(config)

		if len(self.tabs) == 0:
			self.add_new_tab()

		for p in self.notebook.get_children():
			self.notebook.remove(p)

		for t in self.tabs:
			close_image = Gtk.Image(xpad=0, ypad=0)
			close_image.set_from_icon_name("window-close-symbolic", Gtk.IconSize.SMALL_TOOLBAR)

			close_button = Gtk.Button(image=close_image, relief=Gtk.ReliefStyle.NONE)
			close_button.connect("clicked", Tab.close_button_listener)

			header = Gtk.HBox(spacing=8)
			header.pack_start(Gtk.Label(label=self.tabs[t].name), True, True, 0)
			header.pack_end(close_button, False, False, 0)
			header.show_all()

			code_text = ""
			if t in files_temp:
				code_text = files_temp[t]

			page = self.tabs[t].produce_ui(self.window, self.mono_style, code_text)
			header.page_ref = page
			self.notebook.append_page(page, header)

	def populate_ui(self, window, grid, mono_style):
		self.window = window
		self.wnd_grid = grid
		self.mono_style = mono_style

		self.notebook = Gtk.Notebook()
		self.populate_notebook()
		grid.attach(self.notebook, 0, 1, 1, 1)

	def close_tab(self, page):
		tab = page.tab_ref
		path = tab.id

		del self.tabs[path]
		self.notebook.remove(page)

		if self.notebook.get_n_pages() <= 0:
			if os.path.exists("config.cfg"):
				os.remove("config.cfg")

			self.populate_notebook()
			self.window.show_all()
			return

		if os.path.exists("config.cfg"):
			with open("config.cfg") as f:
				lines = f.read().splitlines()

			try:
				lines.remove(path)
			except ValueError:
				pass

			with open("config.cfg", "w") as f:
				f.write("\n".join(lines))

	def open_file(self):
		dialog = Gtk.FileChooserDialog(title="Open Code", action=Gtk.FileChooserAction.OPEN)
		dialog.add_button(Gtk.STOCK_OPEN, Gtk.ResponseType.ACCEPT)
		dialog.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)

		res = dialog.run()
		if res == Gtk.ResponseType.ACCEPT:
			name = dialog.get_filename()

			config = []
			if os.path.exists("config.cfg"):
				with open("config.cfg") as f:
					config = f.read().splitlines()

			config.append(name)
			with open("config.cfg", "w") as f:
				f.write("\n".join(config))

			self.populate_notebook()
			self.window.show_all()

		dialog.destroy()

	def save_as(self, page, tab):
		dialog = Gtk.FileChooserDialog(title="Save Code", action=Gtk.FileChooserAction.SAVE)
		dialog.add_button(Gtk.STOCK_SAVE, Gtk.ResponseType.ACCEPT)
		dialog.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)

		res = dialog.run()
		if res == Gtk.ResponseType.ACCEPT:
			path = dialog.get_filename()
			with open(path, "w") as f:
				f.write(get_textview_text(tab.code_tv))

			config = []
			if os.path.exists("config.cfg"):
				with open("config.cfg") as f:
					config = f.read().splitlines()

			config.append(path)
			with open("config.cfg", "w") as f:
				f.write("\n".join(config))

			self.tabs[path] = self.tabs.pop(tab.id)
			tab.id = path
			tab.name = Tab.name_from_path(tab.id)

			self.notebook.get_tab_label(page).get_children()[0].set_text(tab.name)

		dialog.destroy()

	def save_current_tab(self):
		idx = self.notebook.get_current_page()
		page = self.notebook.get_nth_page(idx)
		tab = page.tab_ref
		path = tab.id

		if path[0] == '&':
			self.save_as(page, tab)
			return

		with open(path, "w") as f:
			f.write(get_textview_text(tab.code_tv))

