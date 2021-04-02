import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

exec(load_local_script("serial.py"))

import threading
import os
import select

class Comms(threading.Thread) :
	def __init__(self, io) :
		super(Comms, self).__init__()
		self.io = io
		self.running = False
		self.packages = []

		self.readfd, self.writefd = os.pipe()

	# Write a byte to our writefd, which will unblock the call to select() inside run()
	# This allows us to write data out (if len(packages) > 0) or exit this thread
	def update(self) :
		os.write(self.writefd, bytes([0]))

	# Once our interrupt has been handled, we read the byte that we wrote
	#  so that there won't be any new data to read, meaning that select() will start blocking again
	def clear(self) :
		os.read(self.readfd, 1)

	def enqueue(self, buf) :
		if self.packages is None:
			self.packages = [buf]
		else:
			self.packages.append(buf)

	def send(self, buf) :
		self.enqueue(buf)
		self.update()

	def close(self) :
		was_running = self.running

		self.packages = []
		self.running = False

		if was_running:
			self.update()
			self.join()

	def run(self) :
		self.running = True

		byte = bytearray(1)
		while (self.running) :
			# Wait for either a byte from the serial's fd or from our own self-pipe (thanks to self.update())
			fdset = [self.readfd]
			if not self.io.serial.dummy:
				fdset.append(self.io.serial.fd)

			r, w, e = select.select(fdset, [], [])
			fd = r[0]

			if fd == self.io.serial.fd:
				res = self.io.serial.read(byte, 1)
				if res == 1:
					self.io.append_byte(byte[0])

			elif fd == self.readfd:
				self.clear()

				data = bytearray()
				for buf in self.packages:
					data.extend(buf)

				if len(data) > 0:
					self.io.serial.write(data, len(data))

				self.packages = []

def str2ba(string):
	if not isinstance(string, str):
		return None

	buf = bytearray()
	idx = 0

	for c in string:
		val = ord(c)

		# if the current character is not a hex digit [0-9a-fA-F],
		#  then try the next character
		if not (val >= 0x30 and val <= 0x39) \
			and not (val >= 0x41 and val <= 0x46) \
			and not (val >= 0x61 and val <= 0x66):
			continue

		if idx % 2 == 0:
			buf.append(int(c, 16))
		else:
			buf[-1] = (buf[-1] << 4) | int(c, 16)

		idx += 1

	return buf

class IO:
	def connect_listener(widget, io):
		io.try_connect(io.device_bar.get_text())

	def send_listener(widget, io):
		s = io.out_bar.get_text()

		data = str2ba(s)
		if data is None:
			return

		io.out_bar.set_text("")
		self.comms.send(data)

	def entry_listener(widget, ev, func):
		if ev.keyval == Gdk.KEY_Return:
			func(widget, widget.io_ref)

	def __init__(self):
		self.serial = Serial()
		self.comms = Comms(self)

	def append_byte(self, byte):
		self.feed.set_editable(True)
		buf = self.feed.get_buffer()
		buf.insert(buf.get_end_iter(), "{0:02x} ".format(byte))
		self.feed.set_editable(False)

	def try_connect(self, name):
		error = True
		msg = ""
		res = self.serial.open(name)

		if isinstance(res, type):
			msg = "{0}: {1}".format(res.__name__, name)
		elif isinstance(res, int) and res < 0:
			msg = "Could not open {0} ({1})".format(name, res)
		else:
			error = False

		if error:
			dialog = Gtk.MessageDialog(message_type=Gtk.MessageType.ERROR, buttons=Gtk.ButtonsType.CLOSE, text=msg)
			dialog.run()
			dialog.destroy()
			return

		self.comms.close()
		self.comms.start()

	def populate_ui(self, window, grid, mono_style):
		self.device_bar = Gtk.Entry(hexpand=True)
		self.device_bar.io_ref = self
		self.device_bar.connect("key-press-event", IO.entry_listener, IO.connect_listener)
		apply_mono_style(self.device_bar, mono_style)
		grid.attach(self.device_bar, 0, 1, 1, 1)

		device_btn = Gtk.Button(label="Connect")
		device_btn.connect("clicked", IO.connect_listener, self)
		grid.attach(device_btn, 1, 1, 2, 1)

		self.feed = Gtk.TextView(hexpand=True, vexpand=True, editable=False)
		apply_mono_style(self.feed, mono_style)
		grid.attach(self.feed, 0, 2, 3, 1)

		self.filter_bar = Gtk.Entry(hexpand=True)
		apply_mono_style(self.filter_bar, mono_style)
		grid.attach(self.filter_bar, 0, 3, 2, 1)

		filter_cb = Gtk.CheckButton()
		grid.attach(filter_cb, 2, 3, 1, 1)

		self.out_bar = Gtk.Entry(hexpand=True)
		self.out_bar.io_ref = self
		self.out_bar.connect("key-press-event", IO.entry_listener, IO.send_listener)
		apply_mono_style(self.out_bar, mono_style)
		grid.attach(self.out_bar, 0, 4, 1, 1)

		out_btn = Gtk.Button(label="Send")
		out_btn.connect("clicked", IO.send_listener, self)
		grid.attach(out_btn, 1, 4, 2, 1)

