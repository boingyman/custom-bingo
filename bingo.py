import os
import math
import textwrap
import random
from argparse import ArgumentParser
from multiprocessing import Process, Manager
from dataclasses import dataclass
from typing import Tuple, List, Any, Optional

from PIL import Image, ImageDraw, ImageFont


@dataclass
class BingoGeneratorInfo:
    input_board_contents: List[str]
    output_file_path: str
    number_of_cards: int
    free_space: bool
    board_size: int
    image_resolution: int
    font_size: int
    text_char_limit: int
    top_border_size: int
    left_border_size: int
    right_border_size: int
    bottom_border_size: int
    line_width: int


@dataclass
class BoardContent:
    borders: (int, int, int, int)  # top, bottom, left, right
    tile_dimensions: Tuple[float, float]
    tile_content_list: List[str]
    board_resolution: int
    board_size: int
    free_tile: bool
    font: ImageFont.FreeTypeFont
    characters_per_line: int
    line_width: int


def parse_input() -> BingoGeneratorInfo:
    parser = ArgumentParser(
        description="Generates a basic 5x5 bingo card using a new line separated list from a text file."
    )
    parser.add_argument(
        "input",
        type=str,
        default=None,
        help="Path to file containing a list of values separated by new lines.",
    )
    parser.add_argument(
        "output", type=str, default=None, help="Path to output file or folder."
    )
    parser.add_argument(
        "-n",
        "--number-of-cards",
        dest="number",
        type=int,
        default=1,
        help="Number of cards to generate. (default: 1, type: integer)",
    )
    parser.add_argument(
        "-f",
        "--free",
        dest="free_space",
        action="store_true",
        help="Whether to include a free space or not. (default: off)",
    )
    parser.add_argument(
        "-s",
        "--size",
        dest="size",
        type=int,
        default=5,
        help="Size of the bingo board. Accepts odd values greater or equal to 3. (default: 5, type: integer)",
    )
    parser.add_argument(
        "-r",
        "--resolution",
        dest="resolution",
        type=int,
        default=512,
        help="The resolution of the resulting images(s). (default: 512, type: integer)",
    )
    parser.add_argument(
        "-fs",
        "--font-size",
        dest="font_size",
        type=int,
        default=13,
        help="The font size for text. (default: 13, type: integer)",
    )
    parser.add_argument(
        "-tw",
        "--text-width",
        dest="text_width",
        type=int,
        default=12,
        help="The number of characters to try and fit on a line of text for each bingo tile. (default: 12, type: integer)",
    )
    parser.add_argument(
        "-b",
        "--borders",
        dest="border",
        type=int,
        default=10,
        help="The amount of space around all sides of the board. (default: 10, type: integer)",
    )
    parser.add_argument(
        "-btop",
        "--border-top",
        dest="border_top",
        type=int,
        default=None,
        help="The amount of space placed before the top of the board. Overrides '-b/--borders' if used.",
    )
    parser.add_argument(
        "-bleft",
        "--border-left",
        dest="border_left",
        type=int,
        default=None,
        help="The amount of space placed before the left of the board. Overrides '-b/--borders' if used.",
    )
    parser.add_argument(
        "-bright",
        "--border-right",
        dest="border_right",
        type=int,
        default=None,
        help="The amount of space placed after the right of the board. Overrides '-b/--borders' if used.",
    )
    parser.add_argument(
        "-bbottom",
        "--border-bottom",
        dest="border_bottom",
        type=int,
        default=None,
        help="The amount of space placed after the bottom of the board. Overrides '-b/--borders' if used.",
    )
    parser.add_argument(
        "-l",
        "--line-width",
        dest="line_width",
        type=int,
        default=5,
        help="The width of the cell outline. (default: 5, type: integer)",
    )

    args = parser.parse_args()

    input_content = None
    with open(args.input, "r", encoding="utf-8", errors="replace") as file:
        input_content = file.read().splitlines()

    extracted_args = BingoGeneratorInfo(
        input_content,
        args.output,
        args.number,
        args.free_space,
        args.size,
        args.resolution,
        args.font_size,
        args.text_width,
        args.border_top if args.border_top is not None else args.border,
        args.border_left if args.border_left is not None else args.border,
        args.border_right if args.border_right is not None else args.border,
        args.border_bottom if args.border_bottom is not None else args.border,
        args.line_width,
    )

    return extracted_args


def generate(args: BingoGeneratorInfo):
    total_cells = args.board_size**2

    if args.number_of_cards < 1:
        raise ValueError("Number of cards must be 1 or more.")
    if (args.board_size % 2) == 0 or args.board_size < 3:
        raise ValueError("Only odd numbers are supported for board size.")
    if args.image_resolution < 1:
        raise ValueError("Resolution must be greater than 0.")
    if len(args.input_board_contents) < total_cells:
        raise ValueError(
            f"Input must have equal to or more than {total_cells} values. Values are separated on to new lines."
        )
    if (
        (args.top_border_size is not None and args.top_border_size < 0)
        or (args.left_border_size is not None and args.left_border_size < 0)
        or (args.right_border_size is not None and args.right_border_size < 0)
        or (args.bottom_border_size is not None and args.bottom_border_size < 0)
    ):
        raise ValueError("Borders must be equal to or more than 0.")

    center_cell = math.floor(float(total_cells) / 2.0)

    board_cells_area = (
        args.image_resolution - args.left_border_size - args.right_border_size,
        args.image_resolution - args.top_border_size - args.bottom_border_size,
    )
    cell_dimensions = (
        board_cells_area[0] / args.board_size,
        board_cells_area[1] / args.board_size,
    )

    font = ImageFont.truetype("arial.ttf", args.font_size)

    proc_list = []
    manager = Manager()
    return_dict = manager.dict()

    for b in range(0, args.number_of_cards, 1):
        cells_text = random.sample(args.input_board_contents, total_cells)

        if args.free_space:
            cells_text[center_cell] = "FREE"

        proc = Process(
            target=mproc_generate_board,
            args=(
                BoardContent(
                    (
                        args.top_border_size,
                        args.bottom_border_size,
                        args.left_border_size,
                        args.right_border_size,
                    ),
                    cell_dimensions,
                    cells_text,
                    args.image_resolution,
                    args.board_size,
                    args.free_space,
                    font,
                    args.text_char_limit,
                    args.line_width,
                ),
                b,
                return_dict,
            ),
        )
        proc_list.append(proc)
        proc.start()

    for i in range(0, len(proc_list), 1):
        proc_list[i].join()
        if args.number_of_cards == 1:
            if (
                os.path.basename(args.output_file_path) == ""
                or os.path.splitext(args.output_file_path)[1] == ""
            ):
                args.output_file_path = os.path.join(args.output_file_path, "board.jpg")

            return_dict[i].save(args.output_file_path, "JPEG")
        else:
            if not os.path.exists(args.output_file_path):
                os.makedirs(args.output_file_path)

            return_dict[i].save(
                os.path.join(args.output_file_path, f"board__{i}.jpg"), "JPEG"
            )


def mproc_generate_board(contents, proc_num, return_dict):
    img = Image.new(
        "RGB", (contents.board_resolution, contents.board_resolution), (255, 255, 255)
    )

    class RectTilingPositioning:
        def __init__(self, width, height, row_length, outline_width):
            self.row_length = row_length
            self.outline_width = outline_width
            outline_overlap_loss = (row_length - 1) * outline_width
            self.width = width + (outline_overlap_loss / float(self.row_length))
            self.height = height + (outline_overlap_loss / float(self.row_length))

        def get_rect_position_for_index(self, index):
            x_pos_1 = ((index % self.row_length) * self.width) - (
                index % self.row_length * self.outline_width
            )
            y_pos_1 = (math.floor(index / self.row_length) * self.height) - (
                math.floor(index / self.row_length) * self.outline_width
            )
            x_pos_2 = x_pos_1 + self.width - 1
            y_pos_2 = y_pos_1 + self.height - 1

            return [(x_pos_1, y_pos_1), (x_pos_2, y_pos_2)]

    positioner = RectTilingPositioning(
        contents.tile_dimensions[0],
        contents.tile_dimensions[1],
        contents.board_size,
        contents.line_width,
    )

    for t in range(0, len(contents.tile_content_list), 1):
        drawing = ImageDraw.Draw(img)

        pos = positioner.get_rect_position_for_index(t)

        pos[0] = (contents.borders[2] + pos[0][0], contents.borders[0] + pos[0][1])
        pos[1] = (contents.borders[2] + pos[1][0], contents.borders[0] + pos[1][1])

        drawing.rectangle(pos, width=contents.line_width, outline="#000000")

        lines = textwrap.wrap(
            contents.tile_content_list[t], contents.characters_per_line
        )
        text_color = (0, 0, 0)

        text_height = contents.font.getbbox(lines[0])[3]

        # there is a bug here where the text will drift off to the side the more down and right
        # the cells are
        #
        # issue is not terribly obvious on line widths <= 5 and higher resolutions

        text_y_pos = (
            pos[0][1]
            + (contents.tile_dimensions[1] / 2.0)
            - (len(lines) * (text_height / 2))
            + 1
        )

        for line in lines:
            text_width = contents.font.getbbox(line)[2]
            drawing.text(
                (
                    (pos[0][0] + (contents.tile_dimensions[0] / 2) - (text_width / 2))
                    + 1,
                    text_y_pos,
                ),
                line,
                font=contents.font,
                fill=text_color,
            )
            text_y_pos += text_height

    return_dict[proc_num] = img


if __name__ == "__main__":
    user_args = parse_input()
    generate(user_args)
