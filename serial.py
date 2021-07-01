import os
import termios

class Serial:
	def __init__(self):
		self.dev = None
		self.fd = -1
		self.dummy = False
		self.in_use = False

		self.speeds = [
			1, 2, 3, 4, 5, 6, 7, 8,
			9, 10, 11, 12, 13, 14, 15,
			4097, 4098, 4099, 4100, 4101, 4102, 4103, 4104,
			4105, 4106, 4107, 4108, 4109, 4110, 4111
		]
		self.speed_values = [
			50, 75, 110, 134, 150, 200, 300, 600,
			1200, 1800, 2400, 4800, 9600, 19200, 38400,
			57600, 115200, 230400, 460800, 500000, 576000, 921600, 1000000,
			1152000, 1500000, 2000000, 2500000, 3000000, 3500000, 4000000
		]

	def open(self, dev):
		self.dev = dev
		self.in_use = True
		flags = os.O_RDWR | os.O_NONBLOCK | os.O_SYNC | os.O_NOCTTY

		try:
			self.fd = os.open(self.dev, flags)
		except BaseException as e:
			self.fd = -1
			self.in_use = False
			return type(e)

		# simple terminal mode
		cflags = termios.CRTSCTS | termios.CLOCAL | termios.CREAD
		cc = [0] * 32

		 # this means the minimum bytes a read() can return is 1, meaning we can do blocking reads
		cc[termios.VMIN] = 1
		cc[termios.VTIME] = 1

		tio = [
			0,        # iflag
			0,        # oflag
			cflags,   # cflag
			0,        # lflag
			0,        # ispeed
			0,        # ospeed
			cc        # cc
		]
		try:
			termios.tcsetattr(self.fd, termios.TCSANOW, tio)
			self.dummy = False
		except termios.error:
			self.dummy = True

		speed_idx = -1
		speed = 0
		if not self.dummy:
			full_speed = True
			for s in self.speeds:
				tio[4] = s  # ispeed
				tio[5] = s  # ospeed
				try:
					termios.tcsetattr(self.fd, termios.TCSANOW, tio)
				except:
					full_speed = False
					break
				speed_idx += 1
				speed = s

			if not full_speed:
				tio[4] = speed
				tio[5] = speed
				termios.tcsetattr(self.fd, termios.TCSANOW, tio)

		if speed_idx >= 0:
			print("Using a baud rate of {0}bps (speed {1})".format(self.speed_values[speed_idx], speed))
			if self.speeds[speed_idx] != speed:
				print("woopsy")

		self.in_use = False
		self.flush()
		return self.fd

	def flush(self):
		if self.fd >= 0 and not self.in_use:
			try:
				termios.tcflush(self.fd, termios.TCIOFLUSH)
			except termios.error:
				pass

	def close(self):
		if self.in_use:
			return

		if self.fd >= 0:
			os.close(self.fd)

		self.fd = -1

	def read(self, buf, size, block_size = 0xf800):
		return self.transfer(buf, size, block_size, False)

	def write(self, buf, size, block_size = 0xf800):
		return self.transfer(buf, size, block_size, True)

	def transfer(self, buf, size, block_size, wr_mode):
		if self.fd < 0 or self.in_use:
			return 0

		self.in_use = True
		off = 0
		left = size

		while left > 0:
			span = left
			if span > block_size:
				span = block_size

			if wr_mode:
				chunk = buf[off:off+span]
				res = os.write(self.fd, chunk)
			else:
				chunk = os.read(self.fd, span)
				res = len(chunk)
				buf[off:off+res] = chunk

			if res < len(chunk):
				self.in_use = False
				return res

			off += span
			left -= span

		self.in_use = False
		return size