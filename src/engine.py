from bitboard import Bitboard, Move
import random

class Engine:
	def __init__(self):
		self.history = []
		self.reset()

	def set_output(self, output):
		self.output = output

	def reset(self):
		self.position = None
		self.first_move_made = False

	def new(self):
		self.position = Bitboard('black')

	def go(self):
		if(self.first_move_made):
			self.think()
		else:
			self.position = Bitboard('white')
			self.think()

	def move(self, move):
		self._execute_move(move)
		formatted = self.position.as_algebraic_coords(move)
		self.output.send('move ' + formatted)

	def user_move(self, move_notation):
		move = self.position.create_move_from_algebraic_coords(move_notation)
		self._execute_move(move)
		self.think()

	def think(self):
		# Random legal move in the position
		moves = self.position.state['possible_moves']

		if(len(moves)):
			self.move(random.choice(moves))
		else:
			self.output.send('resign')

	def _execute_move(self, move):
		self.position.make_move(move)
		# self.history.append(self.position)
		self.position.analyze()