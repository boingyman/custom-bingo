from argparse import ArgumentParser
import os
import math
import textwrap
import random
from multiprocessing import Process, Manager
from dataclasses import dataclass
from typing import Tuple, List, Any

from PIL import Image, ImageDraw, ImageFont


def main():
    # arguments to work with the app
    parser = ArgumentParser(description="Generates a basic 5x5 bingo card using a new line separated list from a text file.")
    parser.add_argument("-n", "--number_of_cards", dest="number", type=int, default=1, help="Number of cards to generate. (default: 1)")
    parser.add_argument("-f", "--free", dest="free_space", action='store_true', help="Whether to include a free space or not. (default: off)")
    parser.add_argument("-s", "--size", dest="size", type=int, default=5, help="Size of the bingo board. Accepts odd values greater or equal to 3. (default: 5)")
    parser.add_argument("-r", "--resolution", dest="resolution", type=int, default=512, help="The resolution of the resulting images(s). (default: 512)")
    parser.add_argument("-fs", "--font_size", dest="font_size", type=int, default=13, help="The font size for text. (default: 13)")
    parser.add_argument("-tw", "--text_width", dest="text_width", type=int, default=12, help="The number of characters to try and fit on a line of text for each bingo tile. (default: 12)")
    parser.add_argument("input", type=str, default=None, help="Path to file containing a list of values separated by new lines.")
    parser.add_argument("output", type=str, default=None, help="Path to output file or folder.")
    args = parser.parse_args()

    if args.number < 1:
        raise Exception("Number of cards must be 1 or more.")
    # these two are covered by argparse
    # if args.i == None:
    #     raise Exception("An input file must be specified.")
    # if args.o == None:
    #     raise Exception("An output path must be specified.")
    if (args.size % 2) == 0 or args.size < 3:
        raise Exception("Only odd numbers are supported for board size.")
    if args.resolution < 1:
        raise Exception("Resolution must be greater than 0.")

    input_content = None
    with open(args.input, 'r', encoding='utf-8', errors='replace') as file:
        input_content = file.read().splitlines()

    if len(input_content) < (args.size ** 2):
        raise Exception(f"Input must have equal to or more than {(args.size ** 2)} values. Values are separated by new line characters.")

    total_tiles = args.size ** 2
    center_tile = math.floor(float(total_tiles) / 2.0)

    borders = (20, 20, 20, 20) # borders for left, right, top, bottom of the board in pixels
    workable_area = (args.resolution - borders[0] - borders[1], args.resolution - borders[2] - borders[3])
    tile_dimensions = (workable_area[0] / args.size, workable_area[1] / args.size)

    font = ImageFont.truetype("arial.ttf", args.font_size)

    proc_list = []
    manager = Manager()
    return_dict = manager.dict()

    for b in range(0, args.number, 1):
        tiles = random.sample(input_content, total_tiles)

        if args.free_space:
            tiles[center_tile] = "FREE"

        proc = Process(target=generate_board, args=(BoardContent(borders, tile_dimensions, tiles, args.resolution, args.size, args.free_space, font, args.text_width), b, return_dict))
        proc_list.append(proc)
        proc.start()

    for i in range(0, len(proc_list), 1):
        proc_list[i].join()
        if args.number == 1:
            if os.path.basename(args.output) == "" or os.path.splitext(args.output)[1] == "":
                args.output = os.path.join(args.output, "board.jpg")

            return_dict[i].save(args.output, "JPEG")
        else:
            if not os.path.exists(args.output):
                os.makedirs(args.output)

            return_dict[i].save(os.path.join(args.output, f"board__{i}.jpg"), "JPEG")

def generate_board(contents, proc_num, return_dict):
    img = Image.new('RGB', (contents.board_resolution, contents.board_resolution), (255, 255, 255))

    class RectTilingPositioning:
        def __init__(self, width, height, row_length, outline_width):
            self.row_length = row_length
            self.outline_width = outline_width
            self.outline_overlap_loss = (((row_length * 2) - 2) / 2) * outline_width
            self.width = width + (self.outline_overlap_loss / float(self.row_length))
            self.height = height + (self.outline_overlap_loss / float(self.row_length))

        def get_rect_position_for_index(self, index):
            x_pos_1 = ((index % self.row_length) * self.width) - \
                    (index % self.row_length * self.outline_width)
            y_pos_1 = (math.floor(index / self.row_length) * self.height) - \
                    (math.floor(index / self.row_length) * self.outline_width)
            x_pos_2 = x_pos_1 + self.width
            y_pos_2 = y_pos_1 + self.height

            return [(x_pos_1, y_pos_1), (x_pos_2, y_pos_2)]

    positioner = RectTilingPositioning(contents.tile_dimensions[0], contents.tile_dimensions[1], contents.board_size, 5)
    tile_area = (contents.tile_dimensions[0] - 5, contents.tile_dimensions[1] - 5)

    for t in range(0, len(contents.tile_content_list), 1):
        drawing = ImageDraw.Draw(img)

        pos = positioner.get_rect_position_for_index(t)

        pos[0] = (contents.borders[0] + pos[0][0], contents.borders[1] + pos[0][1])
        pos[1] = (contents.borders[0] + pos[1][0], contents.borders[1] + pos[1][1])

        drawing.rectangle(pos, width=5, outline="#000000")

        lines = textwrap.wrap(contents.tile_content_list[t], contents.characters_per_line)
        text_color = (0, 0, 0)

        text_height = contents.font.getbbox(lines[0])[3]

        text_y_pos = pos[0][1] + (tile_area[1] / 2) - (len(lines) *  (text_height / 2))

        for line in lines:
            text_width = contents.font.getbbox(line)[2]
            drawing.text(((pos[0][0] + (tile_area[0] - text_width) / 2) + 4, text_y_pos), line, font=contents.font, fill=text_color)
            text_y_pos += text_height

    return_dict[proc_num] = img

@dataclass
class BoardContent:
    borders: Tuple[float, float, float, float]
    tile_dimensions: Tuple[float, float]
    tile_content_list: List[str]
    board_resolution: int
    board_size: int
    free_tile: bool
    font: ImageFont.FreeTypeFont
    characters_per_line: int

if __name__ == "__main__":
    main()
