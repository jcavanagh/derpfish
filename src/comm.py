from collections import namedtuple
import sys

XBoardEvent = namedtuple('XBoardEvent', ['command', 'args'])

class XBoard:
	def __init__(self):
		self.features = {
			'myname': '"Derpfish"',
			'ping': '1',
			'usermove': '1',
			'variants': '"normal"'
		}
		self.log = []
		self.subs = {
			'protover': [self._on_protover],
			'ping': [self._on_ping]
		}

	def _parse_line(self, line):
		parts = line.split()
		# if len(parts):
		return XBoardEvent(
			command=parts[0],
			args=parts[1:]
		)

	def _fire(self, event):
		try:
			evtsubs = self.subs[event.command]
		except KeyError:
			evtsubs = None

		if evtsubs is not None:
			for handler in evtsubs:
				handler(event)

	def _on_protover(self, event):
		for feature_name in self.features:
			self.send('feature ' + feature_name + '=' + self.features[feature_name])

	def _on_ping(self, event):
		if(len(event.args)):
			self.send('pong ' + event.args[0])
		else:
			self.send('pong')

	def send(self, data):
		sys.stdout.write(data + '\n')

	def on(self, event, callback):
		try:
			subs = self.subs[event]
		except KeyError:
			self.subs[event] = []
			subs = self.subs[event]

		subs.append(callback)

	def listen(self):
		for line in sys.stdin:
			parsed = self._parse_line(line)
			if(parsed):
				self._fire(parsed)