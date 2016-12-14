from collections import namedtuple
import sys

XBoardEvent = namedtuple('XBoardEvent', ['command', 'args'])

class XBoard:
	def __init__(self):
		self.features = {
			'myname': 'Derpfish',
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
				print('handling:', event)
				handler(event)

	def _on_protover(self, event):
		for arg in event.args:
			split_arg = arg.split('=')
			feature_name = split_arg[0]
			feature_value = split_arg[1]

			feature_setting = self.features.get(feature_name)

			if(feature_setting and feature_setting == feature_value):
				self.send('accepted ' + feature_name)
			else:
				self.send('rejected ' + feature_name)

	def _on_ping(self, event):
		self.send('pong ' + event.args[0])

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
			self._fire(self._parse_line(line))