from collections import defaultdict, namedtuple
from copy import copy, deepcopy
from gmpy2 import mpz, bit_scan1
import logging

from constants import *
import precompute

all_moves = precompute.all_moves()

class Position:
	@staticmethod
	def start_white():
		return dict(
			color = WHITE,
			pawn = mpz(255<<8),
			knight = mpz(66),
			bishop = mpz(36),
			rook = mpz(129),
			king = mpz(8),
			queen = mpz(16)
		)

	@staticmethod
	def start_black():
		return dict(
			color = BLACK,
			pawn = mpz(255<<48),
			knight = mpz(66<<56),
			bishop = mpz(36<<56),
			rook = mpz(129<<56),
			king = mpz(8<<56),
			queen = mpz(16<<56)
		)

	@staticmethod
	def algebraic_coords(moves):
		return list(map(as_algebraic_coords, moves))

	@staticmethod
	def as_algebraic_coords(move):
		# buf = ''
		start_file = Bitboard._file(move.start_pos)
		start_rank = Bitboard._rank(move.start_pos)
		end_rank = Bitboard._rank(move.end_pos)
		end_file = Bitboard._file(move.end_pos)

		return start_file + start_rank + end_file + end_rank

	@staticmethod
	def _rank_index(pos):
		rank = 0
		for i in range(8):
			if(pos & (MASK_RANK_1<<(8 * i))):
				rank = i + 1
				break

		return rank

	@staticmethod
	def _rank(pos):
		return str(Bitboard._rank_index(pos));

	@staticmethod
	def _file_index(pos):
		file = 0
		for i in range(8):
			if(pos & (MASK_FILE_A>>i)):
				file = i + 1
				break

		return file

	@staticmethod
	def _file(pos):
		return Files[Bitboard._file_index(pos) - 1]

	def __init__(self, on_move_color=WHITE, state=None):
		if state is not None:
			self.state = state
		else:
			on_move = Bitboard.start_white() if on_move_color == WHITE else Bitboard.start_black()
			off_move = Bitboard.start_black() if on_move_color == WHITE else Bitboard.start_white()
			pos_bb = on_move_bb | off_move_bb

			# Sanity check
			# if pos_bb != (player_bb ^ opponent_bb):
			# 	logging.error('Player:')
			# 	logging.error(Bitboard.format_bb('player'))
			# 	logging.error('Opponent:')
			# 	logging.error(Bitboard.format_bb('opponent'))
			# 	raise RuntimeException('Invalid position: Player and opponent cannot occupy the same square');

			self.state = {
				'pos_bb': pos_bb,

				'on_move': on_move,
				'off_move': -on_move,

				'on_move_bb': Bitboard._pos_bb(on_move),
				'off_move_bb': Bitboard._pos_bb(off_move),

				# Populated by analysis
				'on_move_controlled': None,
				'off_move_controlled': None,

				# Disparities in controlled squares - negative favors black, positive favors white
				'controlled_delta': None
			}

		self._analyze()

	def __repr__(self):
		return self.format()

	@staticmethod
	def _pos_bb(board):
		all = mpz(0)
		for item in Pieces:
			all = all ^ board[item]

		return all

	def format_bb(self, side=None):
		return self.format(side, binary=True)

	def format(self, side=None, binary=False):
		squares = ['.' for x in range(64)]

		if side is None:
			self._format_side(self.state['on_move'], binary, squares)
			self._format_side(self.state['off_move'], binary, squares)
		else:
			self._format_side(self.state[side], binary, squares)

		return '\n ' + ' '.join(sq + '\n' * (n % 8 == 7) for n, sq in enumerate(reversed(squares)))

	def _format_side(self, side, binary, squares):
		for piece in Pieces:
			bit_index = -1
			while(1):
				bit_index = bit_scan1(side[piece], bit_index + 1)
				if bit_index is None: break

				symbol = PieceSymbols[piece] if not binary else '1'
				squares[bit_index] = symbol if side['color'] == WHITE else symbol.lower()

	def hash(self):
		hash = 0
		for index in range(len(Pieces)):
			key = Pieces[index]
			hash += (getattr(self.state['on_move'], key) | getattr(self.state['off_move'], key)) * (index + 1)

		return hash.digits(10)

	def bb_from_algebraic(self, file, rank):
		file_index = 8 - FileIndexes[file.lower()]
		return mpz(1)<<((8 * (int(rank) - 1)) + file_index)

	def _piece_at(self, pos, side):
		found = None
		for piece_name in Pieces:
			if(side[piece_name] & pos):
				found = piece_name
				break

		return found

	def create_move_from_algebraic_coords(self, notation):
		# TODO: O-O, O-O-O
		start_file = notation[0]
		start_rank = notation[1]
		end_file = notation[2]
		end_rank = notation[3]

		start_pos = self.bb_from_algebraic(start_file, start_rank)
		end_pos = self.bb_from_algebraic(end_file, end_rank)
		side = self.state['on_move']
		other_side = self.state['off_move']
		piece = self._piece_at(start_pos, side)

		move = self._characterize(piece, start_pos, end_pos)
		logging.debug(notation + '->' + str(move))
		return move

	def make_move(self, move, promote_to='queen'):
		on_move = self.state['on_move']
		off_move = self.state['off_move']
		piece_bb = on_move[move.piece]

		logging.debug('pre-move state:')
		logging.debug(self)

		# Sanity check
		if not (piece_bb & move.start_pos):
			logging.error('Impossible move:' + self.as_algebraic_coords(move))
			logging.error(move)
			return

		logging.debug('Making move:')
		logging.debug(move)

		# TODO: Promotions, castling
		on_move[move.piece] = piece_bb & ~move.start_pos | move.end_pos

		if(move.capture):
			logging.debug('Capturing: ' + move.capture)
			cap_piece_bb = off_move[move.capture]
			off_move[move.capture] = cap_piece_bb & ~move.end_pos

		# swap on move state
		new_state = {}
		new_state['on_move'] = off_move
		new_state['off_move'] = on_move

		# update bitboards
		on_move_bb = self._pos_bb(off_move)
		off_move_bb = self._pos_bb(on_move)
		pos_bb = on_move_bb | off_move_bb
		new_state['pos_bb'] = pos_bb
		new_state['on_move_bb'] = on_move_bb
		new_state['off_move_bb'] = off_move_bb

		logging.debug('post-move state:')
		logging.debug(self)

		return Bitboard(state=new_state)

	def _analyze(self):
		analysis = {
			'on_move_controlled': defaultdict(mpz),
			'off_move_controlled': defaultdict(mpz)
		}

		# Count controlled, attacked, and defended squares
		pos_bb = self.state['pos_bb']
		for side_index in ['on_move', 'off_move']:
			side = self.state[side_index]
			for piece in Pieces:
				bit_index = -1
				while(1):
					bit_index = bit_scan1(side[piece], bit_index + 1)
					if bit_index is None: break

					square = mpz(1)<<bit_index
					moves = []
					if piece == 'pawn':
						pawn_moves = all_moves[on_move['color']][piece][square]
						piece_moves = [x for x in pawn_moves if x.requires_capture]
					elif piece in ['queen', 'rook', 'bishop']:
						# Generate rays and count squares for sliding pieces
						for vector in Movement[piece]:
							# TODO: Pre-index by movement vector?
							vector_moves = [x for x in all_moves[on_move['color']][piece][square] if x.direction == vector]

							# Precompute moves are already sorted by length, so we can just loop naively
							for move in vector_moves:
								moves.append(move)
								if move.end_pos & pos_bb:
									# We found another piece, record this square and end the vector
									break
					else:
						moves = all_moves[on_move['color']][piece][square]

					# Add counts to matrix
					for move in moves:
						analysis[side_index + '_controlled'][move.end_pos] += 1

		self.state.update(analysis)

	def from_fen(self):
		return None

	def to_fen(self):
		return None

if __name__ == "__main__":
	iterations = 100
	# import timeit
	# print(timeit.timeit(stmt="b._analyze()", setup="from __main__ import Bitboard;b=Bitboard(WHITE)", number=iterations) / iterations)

	import cProfile
	# b = Bitboard(WHITE)
	# cProfile.run('for t in range(0, iterations): b._analyze()', sort='tottime')

	b = Bitboard(WHITE)
	print(b)
	print(b.format_bb())
	print(b.format_bb('on_move'))
	print(b.format_bb('off_move'))
	# b._analyze()
	# moves = b.state['possible_moves']
	# print(list(moves))
	# print(list(b.algebraic_coords(moves)))
	# list(map(lambda m: print(b.format_bb(m.end_pos)), b.moves()))
