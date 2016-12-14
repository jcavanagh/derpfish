from bitboard import Bitboard, Move
import random

class Engine:
	def __init__(self):
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
		self.position.make_move(move, self.position.player)
		formatted = self.position.algebraic_move(move)
		self.output.send_move(formatted)

	def user_move(self, move_notation):
		self.position.create_move_from_algebraic(move_notation)
		self.position.make_move(move, self.position.opponent)
		self.think()

	def think(self):
		print('thinking')
		# Random legal move in the position
		moves = self.position.moves()

		if(len(moves)):
			return random.choice(moves)
		else:
			self.output.send('resign')
