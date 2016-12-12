from collections import namedtuple
import sys

XBoardEvent = namedtuple('XBoardEvent', ['command', 'args'])

class XBoard:
	def __init__(self):
		self.log = []
		self.subs = {}
		self._listen()

	def _listen(self):
		for line in sys.stdin:
			self._fire(self._parse_line(line))

	def _parse_line(self, line):
		parts = line.split()
		return XBoardEvent(
			command=parts[0],
			args=parts[1:]
		)

	def _fire(self, event):
		evtsubs = self.subs[event.command]
		if evtsubs is not None:
			for handler in evtsubs:
				handler(event)

	def on(self, event, callback):
		self.subs[event] = self.subs[event] or []
		self.subs[event].push(listener)

