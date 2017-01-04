from bitboard import Bitboard
from constants import *
from move import Move
from gmpy2 import mpz

cache = {}

# Pregenerate all (generally) possible moves by piece and by square
# color -> piece -> square -> moves
def all_moves():
  cached = cache.get('all_moves')
  if cached:
    return cached

  moves = {}

  for color in Colors:
    local_colors = moves[color] = {}

    for piece in Pieces:
      local_moves = local_colors[piece] = {}

      for i in range(0, 64):
        square = mpz(1)<<i
        piece_moves = []
        globals()['_moves_' + piece](square, color, piece_moves)

        # Sort by length for sliding pieces, rays should evaluate near moves first
        if piece in ['queen', 'rook', 'bishop']:
          piece_moves.sort(key=lambda tup: tup.length)

        local_moves[square] = piece_moves
  
  cache['all_moves'] = moves
  return moves

def _append_if(move, moves):
  if(move is not None and move.end_pos):
    moves.append(move)

# Shifts an absolute mask along a bitboard, relative to a color
def _shift_abs(num, shift, color):
  return num<<shift if color == WHITE else (num<<(64 - shift))>>shift

# Shifts a position relative to a color
def _shift(num, shift, color):
  return num<<shift if color == WHITE else num>>shift

def _create_moves_horizontal(piece_name, piece_pos, file, moves):
  # Search left and right of piece
  _create_moves_sliding(piece_name, file, 'left', 1, piece_pos, moves)
  _create_moves_sliding(piece_name, 9 - file, 'right', 1, piece_pos, moves)

def _create_moves_vertical(piece_name, piece_pos, rank, moves):
  # Search up and down of piece
  _create_moves_sliding(piece_name, rank, 'right', 8, piece_pos, moves)
  _create_moves_sliding(piece_name, 9 - rank, 'left', 8, piece_pos, moves)

def _create_moves_diagonal_right(piece_name, piece_pos, file, rank, moves):
  # Search up-right and down-left of piece
  dist_up_right = min(8 - rank, 8 - file)
  dist_down_left = min(rank, file)
  _create_moves_sliding(piece_name, dist_up_right, 'left', 7, piece_pos, moves)
  _create_moves_sliding(piece_name, dist_down_left, 'right', 7, piece_pos, moves)

def _create_moves_diagonal_left(piece_name, piece_pos, file, rank, moves):
  # Search up-left and down-right of piece
  dist_up_left = min(8 - rank, file)
  dist_down_right = min(rank, 8 - file)
  _create_moves_sliding(piece_name, dist_up_left, 'left', 9, piece_pos, moves)
  _create_moves_sliding(piece_name, dist_down_right, 'right', 9, piece_pos, moves)

def _create_moves_sliding(piece_name, iterations, shift_direction, shift_amount, initial_pos, moves):
  for i in range(1, iterations):
    if shift_direction == 'left':
      final_pos = initial_pos<<(shift_amount * i)
    else:
      final_pos = initial_pos>>(shift_amount * i)

    # Cardinal direction
    direction = ''
    if shift_direction == 'left' and shift_amount == 9:
      direction = 'NW'
    if shift_direction == 'left' and shift_amount == 8:
      direction = 'N'
    if shift_direction == 'left' and shift_amount == 7:
      direction = 'NE'
    if shift_direction == 'left' and shift_amount == 1:
      direction = 'W'
    if shift_direction == 'right' and shift_amount == 1:
      direction = 'E'
    if shift_direction == 'right' and shift_amount == 7:
      direction = 'SW'
    if shift_direction == 'right' and shift_amount == 8:
      direction = 'S'
    if shift_direction == 'right' and shift_amount == 9:
      direction = 'SE'

    move = Move(piece_name, initial_pos, final_pos, length=i, direction=direction)
    _append_if(move, moves)

def _moves_pawn(pawn, color, moves):
  start_rank_mask = _shift_abs(255, 8, color)
  is_moved = pawn & ~start_rank_mask

  en_passant_rank_mask = _shift_abs(255, 32, color)
  can_en_passant = pawn & en_passant_rank_mask

  def _pawn_move_1(pawn):
    new_pos = _shift(pawn, 8, color)
    return Move('pawn', pawn, new_pos)

  def _pawn_move_2(pawn):
    if not is_moved:
      move_1 = _pawn_move_1(pawn).end_pos
      new_pos = _shift(move_1, 8, color) if move_1 else 0
      return Move('pawn', pawn, new_pos)

  def _pawn_promote(pawn):
    # Pawn can promote if it can move forward and is on the second to last rank
    new_pos = _pawn_move_1(pawn).end_pos & _shift_abs(255, 48, color)
    return Move('pawn', pawn, new_pos, is_promotion=True)

  def _pawn_capture_left(pawn):
    new_pos = _shift(pawn & ~MASK_FILE_A, 9, color)
    return Move('pawn', pawn, new_pos, requires_capture=True)

  def _pawn_capture_right(pawn):
    new_pos = _shift(pawn & ~MASK_FILE_H, 7, color)
    return Move('pawn', pawn, new_pos, requires_capture=True)

  def _pawn_en_passant_left(pawn):
    new_pos = _shift(pawn & ~MASK_FILE_A, 9, color)
    return Move('pawn', pawn, new_pos, requires_capture=True, en_passant=True)

  def _pawn_en_passant_right(pawn):
    new_pos = _shift(pawn & ~MASK_FILE_H, 7, color)
    return Move('pawn', pawn, new_pos, requires_capture=True, en_passant=True)

  _append_if(_pawn_move_1(pawn), moves)
  _append_if(_pawn_capture_left(pawn), moves)
  _append_if(_pawn_capture_right(pawn), moves)
  _append_if(_pawn_promote(pawn), moves)

  if not is_moved:
    _append_if(_pawn_move_2(pawn), moves)

  if can_en_passant:
    _append_if(_pawn_en_passant_right(pawn), moves)
    _append_if(_pawn_en_passant_left(pawn), moves)

def _moves_knight(knight, color, moves):
  def _knight_move_left_down(knight):
    on_ab_files = knight & (MASK_FILE_A | MASK_FILE_B)
    on_first_rank = knight & MASK_RANK_1
    new_pos = knight>>6 if not (on_ab_files or on_first_rank) else 0
    return Move('knight', knight, new_pos)

  def _knight_move_left_up(knight):
    on_ab_files = knight & (MASK_FILE_A | MASK_FILE_B)
    on_last_rank = knight & MASK_RANK_8
    new_pos = knight<<10 if not (on_ab_files or on_last_rank) else 0
    return Move('knight', knight, new_pos)

  def _knight_move_up_left(knight):
    on_first_file = knight & MASK_FILE_A
    on_78_rank = knight & (MASK_RANK_7 | MASK_RANK_8)
    new_pos = knight<<17 if not (on_first_file or on_78_rank) else 0
    return Move('knight', knight, new_pos)

  def _knight_move_up_right(knight):
    on_last_file = knight & MASK_FILE_H
    on_78_rank = knight & (MASK_RANK_7 | MASK_RANK_8)
    new_pos = knight<<15 if not (on_last_file or on_78_rank) else 0
    return Move('knight', knight, new_pos)

  def _knight_move_right_up(knight):
    on_gh_files = knight & (MASK_FILE_G | MASK_FILE_H)
    on_last_rank = knight & MASK_RANK_8
    new_pos = knight<<6 if not (on_gh_files or on_last_rank) else 0
    return Move('knight', knight, new_pos)

  def _knight_move_right_down(knight):
    on_gh_files = knight & (MASK_FILE_G | MASK_FILE_H)
    on_first_rank = knight & MASK_RANK_1
    new_pos = knight>>10 if not (on_gh_files or on_first_rank) else 0
    return Move('knight', knight, new_pos)

  def _knight_move_down_right(knight):
    on_last_file = knight & MASK_FILE_H
    on_12_rank = knight & (MASK_RANK_1 | MASK_RANK_2)
    new_pos = knight>>17 if not (on_last_file or on_12_rank) else 0
    return Move('knight', knight, new_pos)

  def _knight_move_down_left(knight):
    on_first_file = knight & MASK_FILE_A
    on_12_rank = knight & (MASK_RANK_1 | MASK_RANK_2)
    new_pos = knight>>15 if not (on_first_file or on_12_rank) else 0
    return Move('knight', knight, new_pos)

  _append_if(_knight_move_left_down(knight), moves)
  _append_if(_knight_move_left_up(knight), moves)
  _append_if(_knight_move_up_left(knight), moves)
  _append_if(_knight_move_up_right(knight), moves)
  _append_if(_knight_move_right_up(knight), moves)
  _append_if(_knight_move_right_down(knight), moves)
  _append_if(_knight_move_down_right(knight), moves)
  _append_if(_knight_move_down_left(knight), moves)

def _moves_bishop(bishop, color, moves):
  rank = Bitboard.rank_index(bishop)
  file = Bitboard.file_index(bishop)

  _create_moves_diagonal_right('bishop', bishop, file, rank, moves)
  _create_moves_diagonal_left('bishop', bishop, file, rank, moves)

def _moves_rook(rook, color, moves):
  rank = Bitboard.rank_index(rook)
  file = Bitboard.file_index(rook)

  _create_moves_vertical('rook', rook, rank, moves)
  _create_moves_horizontal('rook', rook, file, moves)

def _moves_king(king, color, moves):
  def _king_move_left_down(king):
    on_first_file = king & MASK_FILE_A
    on_first_rank = king & MASK_RANK_1
    new_pos = king>>7 if not (on_first_file or on_first_rank) else 0
    return Move('king', king, new_pos)

  def _king_move_left(king):
    on_first_file = king & MASK_FILE_A
    new_pos = king<<1 if not on_first_file else 0
    return Move('king', king, new_pos)

  def _king_move_left_up(king):
    on_first_file = king & MASK_FILE_A
    on_last_rank = king & MASK_RANK_8
    new_pos = king<<7 if not (on_first_file or on_last_rank) else 0
    return Move('king', king, new_pos)

  def _king_move_up(king):
    on_last_rank = king & MASK_RANK_8
    new_pos = king<<8 if not on_last_rank else 0
    return Move('king', king, new_pos)

  def _king_move_right_up(king):
    on_last_file = king & MASK_FILE_H
    on_last_rank = king & MASK_RANK_8
    new_pos = king<<9 if not (on_last_file or on_last_rank) else 0
    return Move('king', king, new_pos)

  def _king_move_right(king):
    on_last_file = king & MASK_FILE_H
    new_pos = king>>1 if not on_last_file else 0
    return Move('king', king, new_pos)

  def _king_move_right_down(king):
    on_last_file = king & MASK_FILE_H
    on_first_rank = king & MASK_RANK_1
    new_pos = king>>9 if not (on_last_file or on_first_rank) else 0
    return Move('king', king, new_pos)

  def _king_move_down(king):
    on_first_rank = king & MASK_RANK_1
    new_pos = king>>8 if not on_first_rank else 0
    return Move('king', king, new_pos)

  _append_if(_king_move_left_down(king), moves)
  _append_if(_king_move_left(king), moves)
  _append_if(_king_move_left_up(king), moves)
  _append_if(_king_move_up(king), moves)
  _append_if(_king_move_right_up(king), moves)
  _append_if(_king_move_right(king), moves)
  _append_if(_king_move_right_down(king), moves)
  _append_if(_king_move_down(king), moves)

def _moves_queen(queen, color, moves):
  rank = Bitboard._rank_index(queen)
  file = Bitboard._file_index(queen)

  _create_moves_vertical('queen', queen, rank, moves)
  _create_moves_horizontal('queen', queen, file, moves)
  _create_moves_diagonal_right('queen', queen, file, rank, moves)
  _create_moves_diagonal_left('queen', queen, file, rank, moves)
