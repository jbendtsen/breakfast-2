import os
import termios

class Serial:
	def __init__(self, dev="/dev/ttyUSB0"):
		Serial.dev = dev
		Serial.fd = -1
		Serial.dummy = False
		Serial.in_use = False

		Serial.speeds = [
			1, 2, 3, 4, 5, 6, 7, 8,
			9, 10, 11, 12, 13, 14, 15,
			4097, 4098, 4099, 4100, 4101, 4102, 4103, 4104,
			4105, 4106, 4107, 4108, 4109, 4110, 4111
		]
		Serial.speed_values = [
			50, 75, 110, 134, 150, 200, 300, 600,
			1200, 1800, 2400, 4800, 9600, 19200, 38400,
			57600, 115200, 230400, 460800, 500000, 576000, 921600, 1000000,
			1152000, 1500000, 2000000, 2500000, 3000000, 3500000, 4000000
		]

	def open(self):
		if Serial.fd >= 0:
			return Serial.fd

		Serial.in_use = True
		flags = os.O_RDWR | os.O_NONBLOCK | os.O_SYNC | os.O_NOCTTY

		try:
			Serial.fd = os.open(Serial.dev, flags)
		except FileNotFoundError as e:
			Serial.fd = -1
			Serial.in_use = False
			return Serial.fd

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
			termios.tcsetattr(Serial.fd, termios.TCSANOW, tio)
			Serial.dummy = False
		except termios.error:
			Serial.dummy = True

		speed_idx = -1
		speed = 0
		if not Serial.dummy:
			full_speed = True
			for s in Serial.speeds:
				tio[4] = s  # ispeed
				tio[5] = s  # ospeed
				try:
					termios.tcsetattr(Serial.fd, termios.TCSANOW, tio)
				except:
					full_speed = False
					break
				speed_idx += 1
				speed = s

			if not full_speed:
				tio[4] = speed
				tio[5] = speed
				termios.tcsetattr(Serial.fd, termios.TCSANOW, tio)

		if speed_idx >= 0:
			print("Using a baud rate of {0}bps (speed {1})".format(Serial.speed_values[speed_idx], speed))
			if Serial.speeds[speed_idx] != speed:
				print("woopsy")

		Serial.in_use = False
		self.flush()
		return Serial.fd

	def flush(self):
		if Serial.fd >= 0 and not Serial.in_use:
			try:
				termios.tcflush(Serial.fd, termios.TCIOFLUSH)
			except termios.error:
				pass

	def close(self):
		if Serial.in_use:
			return

		if Serial.fd >= 0:
			os.close(Serial.fd)

		Serial.fd = -1

	def read(self, buf, size, block_size = 0xf800):
		return self.transfer(buf, size, block_size, False)

	def write(self, buf, size, block_size = 0xf800):
		return self.transfer(buf, size, block_size, True)

	def transfer(self, buf, size, block_size, wr_mode):
		if (Serial.fd < 0 or Serial.in_use):
			return 0

		Serial.in_use = True
		off = 0
		left = size

		while left > 0:
			span = left
			if span > block_size:
				span = block_size

			if wr_mode:
				chunk = buf[off:off+span]
				res = os.write(Serial.fd, chunk)
			else:
				chunk = os.read(Serial.fd, span)
				res = len(chunk)
				buf[off:off+res] = chunk

			if res < len(chunk):
				Serial.in_use = False
				return res

			off += span
			left -= span

		Serial.in_use = False
		return size

