from collections import defaultdict, namedtuple
from copy import copy, deepcopy
from gmpy2 import mpz, bit_scan1
import logging
import pdb

BitboardFields = ['pawn', 'knight', 'bishop', 'rook', 'king', 'queen']
BitboardSymbols = {
	'pawn': 'P',
	'knight': 'N',
	'bishop': 'B',
	'rook': 'R',
	'king': 'K',
	'queen': 'Q'
}
BitboardFiles = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']
BitboardFileIndexes = {
	'a': 1,
	'b': 2,
	'c': 3,
	'd': 4,
	'e': 5,
	'f': 6,
	'g': 7,
	'h': 8
}

Move = namedtuple('Move', [
	'piece',
	'start_pos',
	'end_pos',
	'is_check',
	'capture',
	'is_promotion',
	'next_moves'
])

MASK_RANK_1 = mpz(255)
MASK_RANK_2 = MASK_RANK_1<<8
MASK_RANK_3 = MASK_RANK_1<<16
MASK_RANK_4 = MASK_RANK_1<<24
MASK_RANK_5 = MASK_RANK_1<<32
MASK_RANK_6 = MASK_RANK_1<<40
MASK_RANK_7 = MASK_RANK_1<<48
MASK_RANK_8 = MASK_RANK_1<<56

MASK_FILE_A = mpz(1)<<7 | mpz(1)<<15 | mpz(1)<<23 | mpz(1)<<31 | mpz(1)<<39 | mpz(1)<<47 | mpz(1)<<55 | mpz(1)<<63
MASK_FILE_B = MASK_FILE_A>>1
MASK_FILE_C = MASK_FILE_A>>2
MASK_FILE_D = MASK_FILE_A>>3
MASK_FILE_E = MASK_FILE_A>>4
MASK_FILE_F = MASK_FILE_A>>5
MASK_FILE_G = MASK_FILE_A>>6
MASK_FILE_H = MASK_FILE_A>>7

KNIGHT_MASK = 0

class Bitboard:
	@staticmethod
	def start_white():
		return dict(
			color = 'white',
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
			color = 'black',
			pawn = mpz(255<<48),
			knight = mpz(66<<56),
			bishop = mpz(36<<56),
			rook = mpz(129<<56),
			king = mpz(8<<56),
			queen = mpz(16<<56)
		)

	def __init__(self, color='black', player=None, opponent=None, on_move=None, future_pos=False):
		if on_move is None:
			on_move = color == 'white'

		if player is None:
			player = Bitboard.start_white() if color == 'white' else Bitboard.start_black()

		if opponent is None:
			opponent = Bitboard.start_black() if color == 'white' else Bitboard.start_white()

		player_bb = Bitboard._pos_bb(player)
		opponent_bb = Bitboard._pos_bb(opponent)

		if on_move is True:
			on_move = player
			on_move_bb = player_bb
			off_move = opponent
			off_move_bb = opponent_bb
		else:
			on_move = opponent
			on_move_bb = opponent_bb
			off_move = player
			off_move_bb = player_bb

		pos_bb = player_bb | opponent_bb

		# Sanity check
		if pos_bb != (player_bb ^ opponent_bb):
			logging.error('Player:')
			logging.error(Bitboard.format_bb('player'))
			logging.error('Opponent:')
			logging.error(Bitboard.format_bb('opponent'))
			raise RuntimeException('Invalid position: Player and opponent cannot occupy the same square');

		self.state = {
			'future_pos': future_pos,

			'player': player,
			'opponent': opponent,

			'pos_bb': pos_bb,
			'inv_pos_bb': ~pos_bb,

			'player_bb': player_bb,
			'opponent_bb': opponent_bb,

			'on_move': on_move,
			'off_move': off_move,

			'on_move_bb': on_move_bb,
			'inv_on_move_bb': ~on_move_bb,
			'off_move_bb': off_move_bb,
			'inv_off_move_bb': ~off_move_bb,

			# Populated by analysis
			'possible_moves': None,

			'player_controlled': None,
			'player_attacked': None,
			'player_defended': None,
			'player_pinned': mpz(0),

			'opponent_controlled': None,
			'opponent_attacked': None,
			'opponent_defended': None,
			'opponent_pinned': mpz(0)
		}

	def __repr__(self):
		return self.format()

	def _clone(self):
		return Bitboard(
			self.state['player']['color'],
			copy(self.state['player']),
			copy(self.state['opponent']),
			self.state['on_move'],
			True
		)

	@staticmethod
	def _pos_bb(board):
		all = mpz(0)
		for item in BitboardFields:
			all = all ^ board[item]

		return all

	def format_bb(self, side=None):
		return self.format(side, binary=True)

	def format(self, side=None, binary=False):
		squares = ['.' for x in range(64)]

		if side is None:
			self._format_side(self.state['player'], binary, squares)
			self._format_side(self.state['opponent'], binary, squares)
		else:
			self._format_side(self.state[side], binary, squares)

		return '\n ' + ' '.join(sq + '\n' * (n % 8 == 7) for n, sq in enumerate(reversed(squares)))

	def _format_side(self, side, binary, squares):
		for piece in BitboardFields:
			bit_index = -1
			while(1):
				bit_index = bit_scan1(side[piece], bit_index + 1)
				if bit_index is None: break

				symbol = BitboardSymbols[piece] if not binary else '1'
				squares[bit_index] = symbol if side['color'] == 'white' else symbol.lower()

	# Shifts an absolute mask relative to a bitboard
	def _shift_abs(self, num, shift):
		return num<<shift if self.state['on_move']['color'] == 'white' else (num<<(64 - shift))>>shift

	# Shifts a position relative to a bitboard
	def _shift(self, num, shift):
		return num<<shift if self.state['on_move']['color'] == 'white' else num>>shift

	def hash(self):
		hash = 0
		for index in range(len(BitboardFields)):
			key = BitboardFields[index]
			hash += (getattr(self.state['player'], key) | getattr(self.state['opponent'], key)) * (index + 1)

		return hash.digits(10)

	def bb_from_algebraic(self, file, rank):
		file_index = 8 - BitboardFileIndexes[file.lower()]
		return mpz(1)<<((8 * (int(rank) - 1)) + file_index)

	def _rank_index(self, pos):
		rank = 0
		for i in range(8):
			if(pos & (MASK_RANK_1<<(8 * i))):
				rank = i + 1
				break

		return rank

	def _rank(self, pos):
		return str(self._rank_index(pos));

	def _file_index(self, pos):
		file = 0
		for i in range(8):
			if(pos & (MASK_FILE_A>>i)):
				file = i + 1
				break

		return file

	def _file(self, pos):
		return BitboardFiles[self._file_index(pos) - 1]

	def _piece_at(self, pos, side):
		found = None
		for piece_name in BitboardFields:
			if(side[piece_name] & pos):
				found = piece_name
				break

		return found

	def _create_moves_horizontal(self, piece_name, piece_pos, file, moves):
		# Search left and right of piece
		self._create_moves_sliding(piece_name, file, 'left', 1, piece_pos, moves)
		self._create_moves_sliding(piece_name, 9 - file, 'right', 1, piece_pos, moves)

	def _create_moves_vertical(self, piece_name, piece_pos, rank, moves):
		# Search up and down of piece
		self._create_moves_sliding(piece_name, rank, 'right', 8, piece_pos, moves)
		self._create_moves_sliding(piece_name, 9 - rank, 'left', 8, piece_pos, moves)

	def _create_moves_diagonal_right(self, piece_name, piece_pos, file, rank, moves):
		# Search up-right and down-left of piece
		dist_up_right = min(8 - rank, 8 - file)
		dist_down_left = min(rank, file)
		self._create_moves_sliding(piece_name, dist_up_right, 'left', 7, piece_pos, moves)
		self._create_moves_sliding(piece_name, dist_down_left, 'right', 7, piece_pos, moves)

	def _create_moves_diagonal_left(self, piece_name, piece_pos, file, rank, moves):
		# Search up-left and down-right of piece
		dist_up_left = min(8 - rank, file)
		dist_down_right = min(rank, 8 - file)
		self._create_moves_sliding(piece_name, dist_up_left, 'left', 9, piece_pos, moves)
		self._create_moves_sliding(piece_name, dist_down_right, 'right', 9, piece_pos, moves)

	def _create_moves_sliding(self, piece_name, iterations, shift_direction, shift_amount, initial_pos, moves):
		pos_us = self.state['on_move_bb']
		pos_opp = self.state['off_move_bb']

		x_ray = False
		for i in range(1, iterations):
			if shift_direction == 'left':
				final_pos = initial_pos<<(shift_amount * i)
			else:
				final_pos = initial_pos>>(shift_amount * i)

			if(x_ray):
				if(pos_us & final_pos):
					break
				
				self._characterize(piece_name, initial_pos, final_pos, moves, { 'x_ray': True })
			else:
				if(pos_us & final_pos):
					# TODO: Detect discoveries?
					break
				else:
					if(pos_opp & final_pos):
						# TODO: Continue if king follows line, mark single piece directly between as pinned
						self._characterize(piece_name, initial_pos, final_pos, moves)
						x_ray = True
					else:
						self._characterize(piece_name, initial_pos, final_pos, moves)

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
		self.state['on_move'] = off_move
		self.state['off_move'] = on_move

		# update bitboards
		on_move_bb = self._pos_bb(off_move)
		off_move_bb = self._pos_bb(on_move)
		pos_bb = on_move_bb | off_move_bb
		self.state['pos_bb'] = pos_bb
		self.state['inv_pos_bb'] = ~pos_bb
		self.state['on_move_bb'] = on_move_bb
		self.state['inv_on_move_bb'] = ~on_move_bb
		self.state['off_move_bb'] = off_move_bb
		self.state['inv_off_move_bb'] = ~off_move_bb

		logging.debug('post-move state:')
		logging.debug(self)

	def analyze(self, pos_history=[], move_history=[]):
		player = self.state['player']
		player_moves = self._moves(player)
		self.state['player_controlled'] = self._controlled(player, player_moves)
		self.state['player_attacked'] = self._attacked(player, player_moves)
		# self.state['player_defended'] = self._defended(player, player_moves)

		opponent = self.state['opponent']
		opponent_moves = self._moves(opponent)
		self.state['opponent_controlled'] = self._controlled(opponent, opponent_moves)
		self.state['opponent_attacked'] = self._attacked(opponent, opponent_moves)
		# self.state['opponent_defended'] = self._defended(opponent, opponent_moves)

		if id(player) == id(self.state['on_move']):
			on_move_moves = player_moves
			off_move_moves = opponent_moves
		else:
			on_move_moves = opponent_moves
			off_move_moves = player_moves

		off_move_attacks = mpz(0)
		for move in off_move_moves['moves']:
			off_move_attacks |= move.end_pos

		off_move_x_ray = off_move_attacks
		for move in off_move_moves['x_ray']:
			off_move_x_ray |= move.end_pos

		# Filter certain classes of illegal moves using controlled squares data
		def _must_move_out_of_check(move, moves):
			# TODO: Double check
			if len(move_history):
				last_move = move_history[-1]
				logging.debug('Move History')
				logging.debug(last_move)
				x_rays = moves['moves'] + moves['x_ray']
				if last_move.is_check:
					logging.debug('Last move was check')
					# Move away
					return move.end_pos & ~off_move_x_ray

		def _king_moving_into_check(move, moves):
			return move.piece == 'king' and (off_move_attacks & move.end_pos)

		def _piece_pinned(move, moves):
			return False

		def _post_analysis_move_filter(move, moves):
			return not (
				_king_moving_into_check(move, moves) or 
				_piece_pinned(move, moves) or
				_must_move_out_of_check(move, moves)
			)

		on_move_moves = [x for x in on_move_moves['moves'] if _post_analysis_move_filter(x, on_move_moves)]
		self.state['possible_moves'] = on_move_moves

	def _moves(self, side):
		moves = {
			'moves': [],
			'x_ray': []
		}

		self._moves_pawn(side['pawn'], moves)
		self._moves_knight(side['knight'], moves)
		self._moves_bishop(side['bishop'], moves)
		self._moves_rook(side['rook'], moves)
		self._moves_king(side['king'], moves)
		self._moves_queen(side['queen'], moves)

		return moves

	def _controlled(self, side, moves):
		inv_pos_bb = self.state['inv_pos_bb']
		controlled_bb = mpz(0)
		controlled = defaultdict(mpz)
		for move in moves['moves']:
			if(move.end_pos & inv_pos_bb):
				controlled[move.end_pos] += 1
				controlled_bb |= move.end_pos

		return (controlled, controlled_bb)

	def _attacked(self, side, moves):
		off_move_bb = self.state['off_move_bb']
		attacked_bb = mpz(0)
		attacked = defaultdict(mpz)
		for move in moves['moves']:
			if(move.end_pos & off_move_bb):
				attacked[move.end_pos] += 1
				attacked_bb |= move.end_pos

		return (attacked, attacked_bb)

	def _move_bb_gen(self, pieces_bb):
		index = -1
		while(1):
			index = bit_scan1(pieces_bb, index + 1)
			if index is None: raise StopIteration
			yield mpz(1)<<index

	def _characterize(self, piece_name, initial_pos, final_pos, moves=None, meta={}):
		if(final_pos):
			off_move = self.state['off_move']
			off_move_bb = self.state['off_move_bb']

			next_moves = {
				'moves': [],
				'x_ray': []
			}

			if not self.state['future_pos']:
				next_pos = self._clone()
				getattr(next_pos, '_moves_' + piece_name)(final_pos, next_moves)

			capture = None
			check = False

			# Capture
			if(final_pos & off_move_bb):
				capture = self._piece_at(final_pos, off_move)
				if capture is None:
					logging.error('Failed to find capture piece for move:')
					logging.error(move)

			# Check
			for future_move in next_moves['moves']:
				if(future_move.end_pos & off_move['king']):
					check = True
					break

			# Promotion
			promotion = meta.get('promote')

			move = Move(piece_name, initial_pos, final_pos, check, capture, promotion, next_moves)
			if moves is not None:
				if meta.get('x_ray'):
					moves['x_ray'].append(move)
				else:
					moves['moves'].append(move)

			return move

	def _moves_pawn(self, pawns, moves):
		# prev_pos = self.state['history'][:-2] if len(self.state['history']) > 1 else None

		characterize = self._characterize
		shift = self._shift
		shift_abs = self._shift_abs

		rank_mask_rel = shift_abs(255, 8)
		moved_pawns = pawns & ~rank_mask_rel
		unmoved_pawns = pawns & rank_mask_rel

		inv_pos = self.state['inv_pos_bb']
		pos_opp = self.state['off_move_bb']

		def _pawn_move_1(pawn):
			return shift(pawn, 8) & inv_pos

		def _pawn_move_2(pawn):
			move_1 = _pawn_move_1(pawn)
			return shift(move_1, 8) & inv_pos if move_1 else 0

		def _pawn_promote(pawn):
			# Pawn can promote if it can move forward and is on the second to last rank
			return _pawn_move_1(pawn) & shift_abs(255, 48)

		def _pawn_capture_left(pawn):
			return shift(pawn & ~MASK_FILE_A, 9) & pos_opp

		def _pawn_capture_right(pawn):
			return shift(pawn & ~MASK_FILE_H, 7) & pos_opp

		def _pawn_en_passant(pawn):
			# TODO: En passant
			return 0

		for pawn in self._move_bb_gen(pawns):
			characterize('pawn', pawn, _pawn_move_1(pawn), moves)
			characterize('pawn', pawn, _pawn_capture_left(pawn), moves)
			characterize('pawn', pawn, _pawn_capture_right(pawn), moves)
			characterize('pawn', pawn, _pawn_promote(pawn), moves, { 'promote': True })
			characterize('pawn', pawn, _pawn_en_passant(pawn), moves, { 'en_passant': True })

		for pawn in self._move_bb_gen(unmoved_pawns):
			characterize('pawn', pawn, _pawn_move_2(pawn), moves)

	def _moves_knight(self, knights, moves):
		def _knight_move_left_down(knight):
			on_ab_files = knight & (MASK_FILE_A | MASK_FILE_B)
			on_first_rank = knight & MASK_RANK_1
			return knight>>6 & inv_on_move_bb if not (on_ab_files or on_first_rank) else 0

		def _knight_move_left_up(knight):
			on_ab_files = knight & (MASK_FILE_A | MASK_FILE_B)
			on_last_rank = knight & MASK_RANK_8
			return knight<<10 & inv_on_move_bb if not (on_ab_files or on_last_rank) else 0

		def _knight_move_up_left(knight):
			on_first_file = knight & MASK_FILE_A
			on_78_rank = knight & (MASK_RANK_7 | MASK_RANK_8)
			return knight<<17 & inv_on_move_bb if not (on_first_file or on_78_rank) else 0

		def _knight_move_up_right(knight):
			on_last_file = knight & MASK_FILE_H
			on_78_rank = knight & (MASK_RANK_7 | MASK_RANK_8)
			return knight<<15 & inv_on_move_bb if not (on_last_file or on_78_rank) else 0

		def _knight_move_right_up(knight):
			on_gh_files = knight & (MASK_FILE_G | MASK_FILE_H)
			on_last_rank = knight & MASK_RANK_8
			return knight<<6 & inv_on_move_bb if not (on_gh_files or on_last_rank) else 0

		def _knight_move_right_down(knight):
			on_gh_files = knight & (MASK_FILE_G | MASK_FILE_H)
			on_first_rank = knight & MASK_RANK_1
			return knight>>10 & inv_on_move_bb if not (on_gh_files or on_first_rank) else 0

		def _knight_move_down_right(knight):
			on_last_file = knight & MASK_FILE_H
			on_12_rank = knight & (MASK_RANK_1 | MASK_RANK_2)
			return knight>>17 & inv_on_move_bb if not (on_last_file or on_12_rank) else 0

		def _knight_move_down_left(knight):
			on_first_file = knight & MASK_FILE_A
			on_12_rank = knight & (MASK_RANK_1 | MASK_RANK_2)
			return knight>>15 & inv_on_move_bb if not (on_first_file or on_12_rank) else 0

		characterize = self._characterize
		inv_on_move_bb = self.state['inv_on_move_bb']

		for knight in self._move_bb_gen(knights):
			characterize('knight', knight, _knight_move_left_down(knight), moves)
			characterize('knight', knight, _knight_move_left_up(knight), moves)
			characterize('knight', knight, _knight_move_up_left(knight), moves)
			characterize('knight', knight, _knight_move_up_right(knight), moves)
			characterize('knight', knight, _knight_move_right_up(knight), moves)
			characterize('knight', knight, _knight_move_right_down(knight), moves)
			characterize('knight', knight, _knight_move_down_right(knight), moves)
			characterize('knight', knight, _knight_move_down_left(knight), moves)

	def _moves_bishop(self, bishops, moves):
		for bishop in self._move_bb_gen(bishops):
			rank = self._rank_index(bishop)
			file = self._file_index(bishop)

			self._create_moves_diagonal_right('bishop', bishop, file, rank, moves)
			self._create_moves_diagonal_left('bishop', bishop, file, rank, moves)

	def _moves_rook(self, rooks, moves):
		for rook in self._move_bb_gen(rooks):
			rank = self._rank_index(rook)
			file = self._file_index(rook)

			self._create_moves_vertical('rook', rook, rank, moves)
			self._create_moves_horizontal('rook', rook, file, moves)

	def _moves_king(self, kings, moves):
		def _king_move_left_down(king):
			on_first_file = king & MASK_FILE_A
			on_first_rank = king & MASK_RANK_1
			return king>>7 & inv_on_move_bb if not (on_first_file or on_first_rank) else 0

		def _king_move_left(king):
			on_first_file = king & MASK_FILE_A
			return king<<1 & inv_on_move_bb if not on_first_file else 0

		def _king_move_left_up(king):
			on_first_file = king & MASK_FILE_A
			on_last_rank = king & MASK_RANK_8
			return king<<7 & inv_on_move_bb if not (on_first_file or on_last_rank) else 0

		def _king_move_up(king):
			on_last_rank = king & MASK_RANK_8
			return king<<8 & inv_on_move_bb if not on_last_rank else 0

		def _king_move_right_up(king):
			on_last_file = king & MASK_FILE_H
			on_last_rank = king & MASK_RANK_8
			return king<<9 & inv_on_move_bb if not (on_last_file or on_last_rank) else 0

		def _king_move_right(king):
			on_last_file = king & MASK_FILE_H
			return king>>1 & inv_on_move_bb if not on_last_file else 0

		def _king_move_right_down(king):
			on_last_file = king & MASK_FILE_H
			on_first_rank = king & MASK_RANK_1
			return king>>9 & inv_on_move_bb if not (on_last_file or on_first_rank) else 0

		def _king_move_down(king):
			on_first_rank = king & MASK_RANK_1
			return king>>8 & inv_on_move_bb if not on_first_rank else 0

		characterize = self._characterize
		inv_on_move_bb = self.state['inv_on_move_bb']

		for king in self._move_bb_gen(kings):
			characterize('king', king, _king_move_left_down(king), moves)
			characterize('king', king, _king_move_left(king), moves)
			characterize('king', king, _king_move_left_up(king), moves)
			characterize('king', king, _king_move_up(king), moves)
			characterize('king', king, _king_move_right_up(king), moves)
			characterize('king', king, _king_move_right(king), moves)
			characterize('king', king, _king_move_right_down(king), moves)
			characterize('king', king, _king_move_down(king), moves)

	def _moves_queen(self, queens, moves):
		for queen in self._move_bb_gen(queens):
			rank = self._rank_index(queen)
			file = self._file_index(queen)

			self._create_moves_vertical('queen', queen, rank, moves)
			self._create_moves_horizontal('queen', queen, file, moves)
			self._create_moves_diagonal_right('queen', queen, file, rank, moves)
			self._create_moves_diagonal_left('queen', queen, file, rank, moves)

	def algebraic_coords(self, moves):
		return list(map(self.as_algebraic_coords, moves))

	def as_algebraic_coords(self, move):
		# buf = ''
		start_file = self._file(move.start_pos)
		start_rank = self._rank(move.start_pos)
		end_rank = self._rank(move.end_pos)
		end_file = self._file(move.end_pos)

		return start_file + start_rank + end_file + end_rank

	def from_fen(self):
		return None

	def to_fen(self):
		return None

if __name__ == "__main__":
	iterations = 100
	# import timeit
	# print(timeit.timeit(stmt="b.analyze()", setup="from __main__ import Bitboard;b=Bitboard('white')", number=iterations) / iterations)

	import cProfile
	# b = Bitboard('white')
	# cProfile.run('for t in range(0, iterations): b.analyze()', sort='tottime')

	b = Bitboard('white')
	print(b)
	print(b.format_bb())
	print(b.format_bb('player'))
	print(b.format_bb('opponent'))
	# b.analyze()
	# moves = b.state['possible_moves']
	# print(list(moves))
	# print(list(b.algebraic_coords(moves)))
	# list(map(lambda m: print(b.format_bb(m.end_pos)), b.moves()))
