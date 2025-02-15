import os
import math
import textwrap
import random
from argparse import ArgumentParser
from multiprocessing import Process, Manager
from dataclasses import dataclass
from typing import Tuple, List, Any, Optional

from PIL import Image, ImageDraw, ImageFont


class BingoBoardPositioner:
    def __init__(
        self,
        cell_counts: Tuple[int, int],
        outline_width: int,
        borders: Tuple[int, int, int, int],
        cell_dims: Optional[Tuple[int, int]] = None,
        preferred_total_board_size: Optional[Tuple[int, int]] = None,
    ):

        # the dimensions of each cell in pixels
        self.cell_dims: Tuple[int, int] = cell_dims

        if cell_dims is None:
            total_cell_area = (
                preferred_total_board_size[0]
                - borders[0]
                - borders[1]
                - (outline_width * (cell_counts[0] + 3)),
                preferred_total_board_size[1]
                - borders[2]
                - borders[3]
                - (outline_width * (cell_counts[1] + 3)),
            )
            self.cell_dims = (
                math.ceil(total_cell_area[0] / cell_counts[0]),
                math.ceil(total_cell_area[1] / cell_counts[1]),
            )

        # outline width around each cell, outline is doubled along the borders
        self.outline_width: int = outline_width
        # the dimensions of the board in cells)
        self.cell_counts: Tuple[int, int] = cell_counts
        # the sizes of the borders (left, right, top, bottom)
        self.borders = borders
        # board size without the borders (everything contained within the outline)
        self.board_content_area = (
            (self.outline_width * 4)
            + (self.outline_width * (self.cell_counts[0] - 1))
            + (self.cell_dims[0] * self.cell_counts[0]),
            (self.outline_width * 4)
            + (self.outline_width * (self.cell_counts[1] - 1))
            + (self.cell_dims[1] * self.cell_counts[1]),
        )
        # entire area of the board (entire image)
        self.board_area = (
            self.board_content_area[0] + self.borders[0] + self.borders[1],
            self.board_content_area[1] + self.borders[2] + self.borders[3],
        )
        # positions of the top left and bottom right corners of the board
        self.board_content_pos = [
            (self.borders[0], self.borders[2]),
            (
                self.borders[0] + self.board_content_area[0] - 1,
                self.borders[2] + self.board_content_area[1] - 1,
            ),
        ]

    # returns the top left and bottom right corner of a cell
    def get_rect_position_for_index(self, x: int, y: int) -> List[Tuple[int, int]]:
        x_pos_1 = (
            self.borders[0]
            + (x * self.cell_dims[0])
            + (self.outline_width * 2)
            + (x * self.outline_width)
        )
        y_pos_1 = (
            self.borders[2]
            + (y * self.cell_dims[1])
            + (self.outline_width * 2)
            + (y * self.outline_width)
        )
        x_pos_2 = (x_pos_1 + self.cell_dims[0]) - 1
        y_pos_2 = (y_pos_1 + self.cell_dims[1]) - 1

        return [(x_pos_1, y_pos_1), (x_pos_2, y_pos_2)]

    # convenience function for one dimensional index
    def get_rect_position_for_1d_index(self, i: int) -> List[Tuple[int, int]]:
        x = i % self.cell_counts[0]
        y = math.floor(i / self.cell_counts[0])

        return self.get_rect_position_for_index(x, y)

    def get_board_area(self):
        return self.board_area

    def get_board_content_area(self):
        return self.board_content_area

    def get_board_content_pos(self):
        return self.board_content_pos

    def get_cell_dims(self):
        return self.cell_dims


@dataclass
class BingoGeneratorInfo:
    input_board_contents: List[str]
    output_file_path: str
    number_of_cards: int
    free_space: bool
    free_random: bool
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
    board_positioner: BingoBoardPositioner
    tile_content_list: List[str]
    free_tile_index: int
    font: ImageFont.FreeTypeFont
    characters_per_line: int


def parse_input() -> BingoGeneratorInfo:
    parser = ArgumentParser(
        description="Generates a custom bingo card using provided inputs."
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
        "-fr",
        "--free-random",
        dest="free_random",
        action="store_true",
        help="Whether to have the free space take up a random space. (default: off)",
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
        default=2048,
        help="The preferred resolution of the resulting image. Script will determine a resolution that fits the board. (default: 512, type: integer)",
    )
    parser.add_argument(
        "-fs",
        "--font-size",
        dest="font_size",
        type=int,
        default=43,
        help="The font size for text. (default: 13, type: integer)",
    )
    parser.add_argument(
        "-tw",
        "--text-width",
        dest="text_width",
        type=int,
        default=15,
        help="The number of characters to try and fit on a line of text for each bingo tile. (default: 12, type: integer)",
    )
    parser.add_argument(
        "-b",
        "--borders",
        dest="border",
        type=int,
        default=10,
        help="The amount of empty space around all sides of the board. (default: 10, type: integer)",
    )
    parser.add_argument(
        "-btop",
        "--border-top",
        dest="border_top",
        type=int,
        default=None,
        help="The amount of empty space placed before the top of the board. Overrides '-b/--borders' if used.",
    )
    parser.add_argument(
        "-bleft",
        "--border-left",
        dest="border_left",
        type=int,
        default=None,
        help="The amount of empty space placed before the left of the board. Overrides '-b/--borders' if used.",
    )
    parser.add_argument(
        "-bright",
        "--border-right",
        dest="border_right",
        type=int,
        default=None,
        help="The amount of empty space placed after the right of the board. Overrides '-b/--borders' if used.",
    )
    parser.add_argument(
        "-bbottom",
        "--border-bottom",
        dest="border_bottom",
        type=int,
        default=None,
        help="The amount of empty space placed after the bottom of the board. Overrides '-b/--borders' if used.",
    )
    parser.add_argument(
        "-l",
        "--line-width",
        dest="line_width",
        type=int,
        default=5,
        help="The width of the cell outline. Width is double along the borders. (default: 5, type: integer)",
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
        args.free_random,
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
    if args.board_size < 2:
        raise ValueError("Board size must be 2 or more.")
    if (args.board_size % 2) == 0 and args.free_space and not args.free_random:
        raise ValueError("Only odd numbers are supported for free spaces.")
    if args.image_resolution < 400:
        raise ValueError("Resolution must be greater than 400.")
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
        raise ValueError("Borders must be 0 or more.")

    font = ImageFont.truetype("arial.ttf", args.font_size)

    positioner = BingoBoardPositioner(
        (args.board_size, args.board_size),
        args.line_width,
        (
            args.left_border_size,
            args.right_border_size,
            args.top_border_size,
            args.bottom_border_size,
        ),
        preferred_total_board_size=(args.image_resolution, args.image_resolution),
    )

    proc_list = []
    manager = Manager()
    return_dict = manager.dict()
    free_space_index = -1

    for b in range(0, args.number_of_cards, 1):
        cells_text = random.sample(args.input_board_contents, total_cells)

        if args.free_space:
            free_space_index = (
                (math.floor(float(total_cells) / 2.0))
                if not args.free_random
                else random.randint(0, total_cells - 1)
            )

        proc = Process(
            target=mproc_generate_board,
            args=(
                BoardContent(
                    positioner,
                    cells_text,
                    free_space_index,
                    font,
                    args.text_char_limit,
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


def mproc_generate_board(input_contents, proc_num, return_dict):

    img = Image.new(
        "RGB", input_contents.board_positioner.get_board_area(), (255, 255, 255)
    )

    drawing = ImageDraw.Draw(img)

    drawing.rectangle(
        input_contents.board_positioner.get_board_content_pos(), fill="#000000"
    )

    for t in range(0, len(input_contents.tile_content_list), 1):

        pos = input_contents.board_positioner.get_rect_position_for_1d_index(t)

        drawing.rectangle(pos, fill="#FFFFFF")

        lines = textwrap.wrap(
            (
                "FREE"
                if t == input_contents.free_tile_index
                else input_contents.tile_content_list[t]
            ),
            input_contents.characters_per_line,
        )
        text_color = (0, 0, 0)

        text_height = input_contents.font.getbbox(lines[0])[3]

        text_y_pos = (
            pos[0][1]
            + (input_contents.board_positioner.get_cell_dims()[1] / 2.0)
            - (len(lines) * (text_height / 2))
            + 1
        )

        for line in lines:
            text_width = input_contents.font.getbbox(line)[2]
            drawing.text(
                (
                    (
                        pos[0][0]
                        + (input_contents.board_positioner.get_cell_dims()[0] / 2)
                        - (text_width / 2)
                    )
                    + 1,
                    text_y_pos,
                ),
                line,
                font=input_contents.font,
                fill=text_color,
            )
            text_y_pos += text_height

    return_dict[proc_num] = img


if __name__ == "__main__":
    user_args = parse_input()
    generate(user_args)
