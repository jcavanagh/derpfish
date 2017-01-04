from bitboard import Bitboard
from constants import *
from position import Position
from search import Search

class Engine:
	def __init__(self):
		self.pos_history = []
		self.move_history = []
		self.search = Search()
		self.reset()

	def set_output(self, output):
		self.output = output

	def reset(self):
		self.position = None
		self.first_move_made = False

	def new(self):
		self.position = Position(BLACK)

	def go(self):
		if(self.first_move_made):
			self.think()
		else:
			self.position = Position(WHITE)
			self.think()

	def move(self, move):
		self._execute_move(move)
		formatted = Bitboard.as_algebraic_coords(move)
		self.output.send('move ' + formatted)

	def user_move(self, move_notation):
		move = Bitboard.create_move_from_algebraic_coords(move_notation)
		self._execute_move(move)
		self.think()

	def think(self):
		move = self.search.think(self.position, 10000)
		self.output.send(move)

	def _execute_move(self, move):
		self.position = self.position.make_move(move)
		self.pos_history.append(self.position)
		self.move_history.append(move)