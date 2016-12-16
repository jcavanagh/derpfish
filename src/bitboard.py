from collections import namedtuple
from copy import copy, deepcopy
from gmpy2 import mpz, bit_scan1
import logging
import pdb

BitboardFields = ['pawn', 'knight', 'bishop', 'rook', 'king', 'queen']
BitboardSymbols = ['', 'N', 'B', 'R', 'K', 'Q']
BitboardFiles = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']

Move = namedtuple('Move', [
	'piece',
	'start_pos',
	'end_pos',
	'is_check',
	'is_promotion',
	'capture',
	'attacks'
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

	@staticmethod
	def defaults(color):
		start_player = Bitboard.start_white() if color == 'white' else Bitboard.start_black()
		start_opp = Bitboard.start_black() if color == 'white' else Bitboard.start_white()

		return {
			'player': start_player,
			'opponent': start_opp,
			'on_move': start_player if color == 'white' else start_opp,
			'off_move': start_opp if color == 'white' else start_player,
			'possible_moves': None,
			# Lists of piece moves that control empty squares or squares occupied by the side in question (defending pieces)
			'player_controlled_squares': [],
			'opponent_controlled_squares': [],
			'history': [],
			'move_list': [],
			'future_pos': False
		}

	def __init__(self, color, state=None):
		if state:
			self.state = state
		else:
			self.state = Bitboard.defaults(color)
			self.state['possible_moves'] = self.moves()
			self.state['player_controlled_squaresx']

	def __repr__(self):
		return self.format(self._pos_bb())

	def __copy__(self):
		player = self.state['player']
		opp = self.state['opponent']
		player_copy = copy(player)
		opp_copy = copy(opp)
		on_move_copy = player == id(player) == id(self.state['on_move']) else opp

		copiable_state = {
			'color': self.state['color'],
			'player': player_copy,
			'opponent': opp_copy,
			'on_move': on_move_copy,
			# Historical structures should not be modified in position copies
			'history': self.state['history'],
			'move_list': self.state['move_list'],
			'future_pos': True
		}

		return Bitboard(self.state['color'], copiable_state)

	def _clone(self):
		return copy(self)

	def _pos_bb(self, board=None):
		if board is None:
			return (self._pos_bb(self.state['player']) | self._pos_bb(self.state['opponent']))
		else:
			all = mpz(0)
			for item in board:
				all = all ^ board[item]

			return all

	def format(self, board):
		digits = board.digits(2).rjust(64, '0')
		index = 0
		formatted = ''
		while index < 64:
			formatted += digits[index:index+8]+'\n'
			index += 8
		return formatted

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
		file_index = 7 - BitboardFiles.index(file.lower())
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
		for piece_name in side:
			if(side[piece_name] & pos):
				found = piece_name
				break

		return found

	def _next_pos_controlled_squares(self, move):
		evil_twin = self._clone()
		evil_twin.make_move(move)
		return evil_twin._pos_attacked_squares(evil_twin.state['on_move'])

	def _pos_controlled_squares(self, side):
		pos = self._pos_bb(side)
		controlled = []
		if(piece == 'pawn'):
			# TODO: en passant counts as "attacked"
			self._captures_pawn(move.end_pos, self._pos_bb(self.state['opponent']), controlled)
		else:
			getattr(self, '_moves_' + piece)(move.end_pos, controlled)

		return controlled

	def create_move(self, piece_name, initial, final, capture=None, promotion=None):
		check = self.is_check(final)
		if self.state['future_pos']:
			attacks = None
		else:
			attacks = self._next_pos_attacked_squares(Move(piece_name, initial, final, check, promotion, capture, None))
		return Move(piece_name, initial, final, check, promotion, capture, attacks)

	def _create_moves_horizontal(self, piece_name, piece_pos, pos_us, pos_opp, file, moves):
		# Search left and right of piece
		self._create_moves_sliding(piece_name, file, 'left', 1, piece_pos, pos_us, pos_opp, moves)
		self._create_moves_sliding(piece_name, 9 - file, 'right', 1, piece_pos, pos_us, pos_opp, moves)

	def _create_moves_vertical(self, piece_name, piece_pos, pos_us, pos_opp, rank, moves):
		# Search up and down of piece
		self._create_moves_sliding(piece_name, rank, 'right', 8, piece_pos, pos_us, pos_opp, moves)
		self._create_moves_sliding(piece_name, 9 - rank, 'left', 8, piece_pos, pos_us, pos_opp, moves)

	def _create_moves_diagonal_right(self, piece_name, piece_pos, pos_us, pos_opp, file, rank, moves):
		# Search up-right and down-left of piece
		dist_up_right = min(8 - rank, 8 - file)
		dist_down_left = min(rank, file)
		self._create_moves_sliding(piece_name, dist_up_right, 'left', 7, piece_pos, pos_us, pos_opp, moves)
		self._create_moves_sliding(piece_name, dist_down_left, 'right', 7, piece_pos, pos_us, pos_opp, moves)

	def _create_moves_diagonal_left(self, piece_name, piece_pos, pos_us, pos_opp, file, rank, moves):
		# Search up-left and down-right of piece
		dist_up_left = min(8 - rank, file)
		dist_down_right = min(rank, 8 - file)
		self._create_moves_sliding(piece_name, dist_up_left, 'left', 9, piece_pos, pos_us, pos_opp, moves)
		self._create_moves_sliding(piece_name, dist_down_right, 'right', 9, piece_pos, pos_us, pos_opp, moves)

	def _create_moves_sliding(self, piece_name, iterations, shift_direction, shift_amount, initial_pos, pos_us, pos_opp, moves):
		for i in range(1, iterations):
			if shift_direction == 'left':
				final_pos = initial_pos<<(shift_amount * i)
			else:
				final_pos = initial_pos>>(shift_amount * i)

			if(pos_us & final_pos):
				break
			else:
				if(pos_opp & final_pos):
					self._move_append_if(piece_name, initial_pos, final_pos, moves)
					break
				else:
					self._move_append_if(piece_name, initial_pos, final_pos, moves)

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

		return self.create_move(piece, start_pos, end_pos, self._piece_at(end_pos, other_side))

	def make_move(self, move):
		if not self.state['future_pos']:
			self.state['history'].append(self._clone())
			self.state['move_list'].append(move)

		on_move_bb = self.state['on_move']
		piece_bb = on_move_bb[move.piece]

		if not (piece_bb & move.start_pos):
			logging.error('Impossible move:' + self.as_algebraic_coords(move))
			logging.error(move)
			return

		# TODO: Promotions, castling
		on_move_bb[move.piece] = piece_bb & ~move.start_pos | move.end_pos

		if(move.capture):
			off_move_bb = self.state['opponent'] if self.state['on_move'] else self.state['player']
			cap_piece_bb = off_move_bb[move.capture]
			off_move_bb[move.capture] = cap_piece_bb & ~move.end_pos

		if not self.state['future_pos']:
			self.state['on_move'] = not self.state['on_move']

	def moves(self, side=None):
		side = side or self.state['player']
		moves = []

		for move_list in map(lambda key: getattr(self, '_moves_' + key)(side[key], moves), BitboardFields):
			pass

		return moves

	def _move_bb_gen(self, pieces_bb):
		index = -1
		while(1):
			index = bit_scan1(pieces_bb, index + 1)
			if index is None: raise StopIteration
			yield mpz(1)<<index

	def _move_append_if(self, piece_name, initial_pos, final_pos, moves):
		if(final_pos):
			move_list = self.state['move_list']
			
			# Do not consider move if the last was check, and this move does not avoid check
			# TODO: Can I work backward from pieces capable of interposing and king moves?
			# TODO: How to handle double check efficiently?  Some kind of attack counting matrix, perhaps
			if(len(move_list)):
				last_was_check = move_list[-1].is_check
				if last_was_check:
					avoids_check = True
					for move in self.state['history'][-1]['opponent']

			capture = self._piece_at(final_pos, self.state['opponent'])
			moves.append(self.create_move(piece_name, initial_pos, final_pos, capture))

	def _moves_pawn(self, pawns, moves):
		prev_pos = self.state['history'][:-2] if len(self.state['history']) > 1 else None

		rank_mask_rel = self._shift_abs(255, 8)
		moved_pawns = pawns & ~rank_mask_rel
		unmoved_pawns = pawns & rank_mask_rel

		inv_pos_us = ~self._pos_bb()
		pos_opp = self._pos_bb(self.state['opponent'])

		def _pawn_move_1(pawn):
			return self._shift(pawn, 8) & inv_pos_us

		def _pawn_move_2(pawn):
			move_1 = _pawn_move_1(pawn)
			return self._shift(move_1, 8) & inv_pos_us if move_1 else 0

		def _pawn_promote(pawn):
			return _pawn_move_1(pawn) & rank_mask_rel

		for pawn in self._move_bb_gen(pawns):
			self._move_append_if('pawn', pawn, _pawn_move_1(pawn), moves)
			self._captures_pawn(pawn, pos_opp, moves)
		
		for pawn in self._move_bb_gen(unmoved_pawns):
			self._move_append_if('pawn', pawn, _pawn_move_2(pawn), moves)

	def _captures_pawn(self, pawn, pos_opp, moves):
		def _pawn_capture_left(pawn):
			return self._shift(pawn & ~MASK_FILE_A, 9) & pos_opp

		def _pawn_capture_right(pawn):
			return self._shift(pawn & ~MASK_FILE_H, 7) & pos_opp

		def _pawn_en_passant(pawn):
			# TODO: En passant
			pass

		# TODO: Promotion can generate an attack

		self._move_append_if('pawn', pawn, _pawn_capture_left(pawn), moves)
		self._move_append_if('pawn', pawn, _pawn_capture_right(pawn), moves)

	def _moves_knight(self, knights, moves):
		def _knight_move_left_down(knight):
			on_ab_files = knight & (MASK_FILE_A | MASK_FILE_B)
			on_first_rank = knight & MASK_RANK_1
			return knight>>6 & inv_pos_us if not (on_ab_files or on_first_rank) else 0
		def _knight_move_left_up(knight):
			on_ab_files = knight & (MASK_FILE_A | MASK_FILE_B)
			on_last_rank = knight & MASK_RANK_8
			return knight<<10 & inv_pos_us if not (on_ab_files or on_last_rank) else 0
		def _knight_move_up_left(knight):
			on_first_file = knight & MASK_FILE_A
			on_78_rank = knight & (MASK_RANK_7 | MASK_RANK_8)
			return knight<<17 & inv_pos_us if not (on_first_file or on_78_rank) else 0
		def _knight_move_up_right(knight):
			on_last_file = knight & MASK_FILE_H
			on_78_rank = knight & (MASK_RANK_7 | MASK_RANK_8)
			return knight<<15 & inv_pos_us if not (on_last_file or on_78_rank) else 0
		def _knight_move_right_up(knight):
			on_gh_files = knight & (MASK_FILE_G | MASK_FILE_H)
			on_last_rank = knight & MASK_RANK_8
			return knight<<6 & inv_pos_us if not (on_gh_files or on_last_rank) else 0
		def _knight_move_right_down(knight):
			on_gh_files = knight & (MASK_FILE_G | MASK_FILE_H)
			on_first_rank = knight & MASK_RANK_1
			return knight>>10 & inv_pos_us if not (on_gh_files or on_first_rank) else 0
		def _knight_move_down_right(knight):
			on_last_file = knight & MASK_FILE_H
			on_12_rank = knight & (MASK_RANK_1 | MASK_RANK_2)
			return knight>>17 & inv_pos_us if not (on_last_file or on_12_rank) else 0
		def _knight_move_down_left(knight):
			on_first_file = knight & MASK_FILE_A
			on_12_rank = knight & (MASK_RANK_1 | MASK_RANK_2)
			return knight>>15 & inv_pos_us if not (on_first_file or on_12_rank) else 0

		inv_pos_us = ~self._pos_bb(self.state['player'])

		for knight in self._move_bb_gen(knights):
			self._move_append_if('knight', knight, _knight_move_left_down(knight), moves)
			self._move_append_if('knight', knight, _knight_move_left_up(knight), moves)
			self._move_append_if('knight', knight, _knight_move_up_left(knight), moves)
			self._move_append_if('knight', knight, _knight_move_up_right(knight), moves)
			self._move_append_if('knight', knight, _knight_move_right_up(knight), moves)
			self._move_append_if('knight', knight, _knight_move_right_down(knight), moves)
			self._move_append_if('knight', knight, _knight_move_down_right(knight), moves)
			self._move_append_if('knight', knight, _knight_move_down_left(knight), moves)

	def _moves_bishop(self, bishops, moves):
		pos_us = self._pos_bb(self.state['player'])
		pos_opp = self._pos_bb(self.state['opponent'])

		for bishop in self._move_bb_gen(bishops):
			rank = self._rank_index(bishop)
			file = self._file_index(bishop)

			self._create_moves_diagonal_right('bishop', bishop, pos_us, pos_opp, file, rank, moves)
			self._create_moves_diagonal_left('bishop', bishop, pos_us, pos_opp, file, rank, moves)

	def _moves_rook(self, rooks, moves):
		pos_us = self._pos_bb(self.state['player'])
		pos_opp = self._pos_bb(self.state['opponent'])

		for rook in self._move_bb_gen(rooks):
			rank = self._rank_index(rook)
			file = self._file_index(rook)

			self._create_moves_vertical('rook', rook, pos_us, pos_opp, rank, moves)
			self._create_moves_horizontal('rook', rook, pos_us, pos_opp, file, moves)

	def _moves_king(self, kings, moves):
		def _king_move_left_down(king):
			on_first_file = king & MASK_FILE_A
			on_first_rank = king & MASK_RANK_1
			return (king>>7) & inv_pos_us if not (on_first_file or on_first_rank) else 0
		def _king_move_left(king):
			on_first_file = king & MASK_FILE_A
			return (king<<1) & inv_pos_us if not on_first_file else 0
		def _king_move_left_up(king):
			on_first_file = king & MASK_FILE_A
			on_last_rank = king & MASK_RANK_8
			return (king<<7) & inv_pos_us if not (on_first_file or on_last_rank) else 0
		def _king_move_up(king):
			on_last_rank = king & MASK_RANK_8
			return (king<<8) & inv_pos_us if not on_last_rank else 0
		def _king_move_right_up(king):
			on_last_file = king & MASK_FILE_H
			on_last_rank = king & MASK_RANK_8
			return (king<<9) & inv_pos_us if not (on_last_file or on_last_rank) else 0
		def _king_move_right(king):
			on_last_file = king & MASK_FILE_H
			return (king>>1) & inv_pos_us if not on_last_file else 0
		def _king_move_right_down(king):
			on_last_file = king & MASK_FILE_H
			on_first_rank = king & MASK_RANK_1
			return (king>>9) & inv_pos_us if not (on_last_file or on_first_rank) else 0
		def _king_move_down(king):
			on_first_rank = king & MASK_RANK_1
			return (king>>8) & inv_pos_us if not on_first_rank else 0

		inv_pos_us = ~self._pos_bb(self.state['player'])

		for king in self._move_bb_gen(kings):
			self._move_append_if('king', king, _king_move_left_down(king), moves)
			self._move_append_if('king', king, _king_move_left(king), moves)
			self._move_append_if('king', king, _king_move_left_up(king), moves)
			self._move_append_if('king', king, _king_move_up(king), moves)
			self._move_append_if('king', king, _king_move_right_up(king), moves)
			self._move_append_if('king', king, _king_move_right(king), moves)
			self._move_append_if('king', king, _king_move_right_down(king), moves)
			self._move_append_if('king', king, _king_move_down(king), moves)

	def _moves_queen(self, queens, moves):
		pos_us = self._pos_bb(self.state['player'])
		pos_opp = self._pos_bb(self.state['opponent'])

		for queen in self._move_bb_gen(queens):
			rank = self._rank_index(queen)
			file = self._file_index(queen)

			self._create_moves_vertical('queen', queen, pos_us, pos_opp, rank, moves)
			self._create_moves_horizontal('queen', queen, pos_us, pos_opp, file, moves)
			self._create_moves_diagonal_right('queen', queen, pos_us, pos_opp, file, rank, moves)
			self._create_moves_diagonal_left('queen', queen, pos_us, pos_opp, file, rank, moves)

	def is_check(self, move):
		# pos_opp = self._pos_bb(self.state['opponent'])
		opp_king = self.state['opponent']['king']
		for attack in move.attacks:
			if attack & opp_king:
				return True

		return False

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
	iterations = 10000
	import timeit
	print(timeit.timeit(stmt="b.moves()", setup="from __main__ import Bitboard;b=Bitboard('white')", number=iterations) / iterations)

	# import cProfile
	# b = Bitboard('white')
	# cProfile.run('for t in range(0, iterations): b.moves()', sort='tottime')

	# b = Bitboard('white')
	# moves = b.moves()
	# print(list(moves))
	# print(list(b.algebraic_coords(moves)))
	# list(map(lambda m: print(b.format(m.end_pos)), b.moves()))
