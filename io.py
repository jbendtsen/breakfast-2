import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
from gi.repository import GObject

exec(load_local_script("serial.py"))

import threading
import select
import queue
import time

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

class IO(GObject.GObject):
	def __init__(self):
		GObject.GObject.__init__(self)

		GObject.type_register(IO)
		GObject.signal_new("data-available", IO, GObject.SignalFlags.RUN_FIRST, GObject.TYPE_NONE, ())

		self.connect("data-available", self.on_data_available)
		self.writing = False

		self.data_queue = queue.Queue()
		self.output = bytearray()

		self.serial = Serial()
		self.comms = Comms(self)

	def on_data_available(self, sender):
		if self.data_queue.empty():
			return

		while self.writing:
			pass

		self.writing = True

		data = bytearray()
		while not self.data_queue.empty():
			data.append(self.data_queue.get())

		text = ""
		if ui.io_output_ascii.get_active():
			text = str(data, "utf8")
		else:
			for d in data:
				text += "{0:02x} ".format(d)

		buf = ui.io_output_tv.get_buffer()
		buf.insert(buf.get_end_iter(), text)

		adj = ui.io_output_scroller.get_vadjustment()
		adj.set_value(adj.get_upper())

		self.writing = False

	def send_byte_string(self, s):
		data = str2ba(s)
		if data is None:
			return

		self.comms.send(data)

	def append_byte(self, byte):
		macros.data_queue.put(byte)
		self.data_queue.put(byte)
		self.output.append(byte)
		self.emit("data-available")

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

		style = ui.device_bar.get_style_context()

		if error:
			if style.has_class("green"):
				style.remove_class("green")

			dialog = Gtk.MessageDialog(message_type=Gtk.MessageType.ERROR, buttons=Gtk.ButtonsType.CLOSE, text=msg)
			dialog.run()
			dialog.destroy()
			return

		if not style.has_class("green"):
			style.add_class("green")

		if self.comms.running:
			self.comms.close()
			self.comms = Comms(self)

		self.comms.start()
