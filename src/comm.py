from collections import namedtuple
import logging, os, re, sys

XBoardEvent = namedtuple('XBoardEvent', ['command', 'args'])

logger = logging.getLogger('comm')

class XBoard:
	def __init__(self):
		self.move_exp = '[a-h]\d[a-h]\d[qnbr]?$|O-O$|O-O-O$'
		self.features = {
			'analyze': '0',
			'myname': '"Derpfish"',
			# 'ping': '1',
			'variants': '"normal"'
		}
		self.accepted = {}
		self.log = []
		self.subs = {
			'protover': [self._on_protover],
			'accepted': [self._on_accepted],
			# 'ping': [self._on_ping]
		}

	def _parse_line(self, line):
		move_match = re.match(self.move_exp, line)
		if move_match:
			return XBoardEvent(
				command='move',
				args=[move_match.group(0)]
			)
		else:
			parts = line.split()
			if len(parts):
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

	def _on_accepted(self, event):
		if(len(event.args)):
			feature_name = event.args[0]
			self.accepted[feature_name] = True

	def _on_protover(self, event):
		for feature_name in self.features:
			self.send('feature ' + feature_name + '=' + self.features[feature_name])

		self.send('feature done=1')

	def _on_ping(self, event):
		if(len(event.args)):
			self.send('pong ' + event.args[0])
		else:
			self.send('pong')

	def send(self, data):
		logger.debug('>>> ' + data)
		print(data, end=os.linesep)

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
				logger.debug('<<< ' + line)
				logger.debug(parsed)
				self._fire(parsed)