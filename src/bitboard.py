from constants import *

class Bitboard:
  @staticmethod
  def rank_index(pos):
    rank = 0
    for i in range(8):
      if(pos & (MASK_RANK_1<<(8 * i))):
        rank = i + 1
        break

    return rank

  @staticmethod
  def rank(pos):
    return str(Bitboard._rank_index(pos));

  @staticmethod
  def file_index(pos):
    file = 0
    for i in range(8):
      if(pos & (MASK_FILE_A>>i)):
        file = i + 1
        break

    return file

  @staticmethod
  def file(pos):
    return Files[Bitboard._file_index(pos) - 1]

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