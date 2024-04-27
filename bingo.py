from argparse import ArgumentParser
import os
import math
import textwrap
import random

from PIL import Image, ImageDraw, ImageFont


def main():
    # arguments to work with the app
    parser = ArgumentParser(description="Generates a basic 5x5 bingo card using a new line separated list from a text file.")
    parser.add_argument("-i", required=True, type=str, default=None, help="Path to file containing a list of values separated by new lines.")
    parser.add_argument("-o", required=True, type=str, default=None, help="Path to output file or folder.")
    parser.add_argument("-n", type=int, default=1, help="Number of cards to generate. A value greater than 1 will create an additional directory with the generated content within it. Accepts values greater than 0.")
    parser.add_argument("-fr", action='store_true', help="Whether to include a free space or not.")
    parser.add_argument("-l", type=int, default=5, help="Size of the bingo board. Accepts odd values greater or equal to 3.")
    parser.add_argument("-r", type=int, default=1024, help="The resolution of the resulting images(s).")
    parser.add_argument("-fo", type=int, default=20, help="The font size for text.")
    parser.add_argument("-tw", type=int, default=19, help="The number of characters to try and fit on a line of text for each bingo tile.")
    args = parser.parse_args()

    if args.n < 1:
        raise Exception("Number of cards must be 1 or more.")
    if args.i == None:
        raise Exception("An input file must be specified.")
    if args.o == None:
        raise Exception("An output path must be specified.")
    if (args.l % 2) == 0 or args.l < 3:
        raise Exception("This generator only supports odd number length boards.")
    if args.r < 1:
        raise Exception("Resolution must be greater than 0.")

    input_content = None
    with open(args.i, 'r', encoding='utf-8', errors='replace') as file:
        input_content = file.read().split

    if len(input_content) < (args.l ** 2):
        raise Exception(f"Input must have more than {(args.l ** 2)} values. Values are separated by new line characters.")

    total_tiles = args.l ** 2
    center_tile = math.floor(float(total_tiles) / 2.0)

    borders = (20, 20, 20, 20) # borders for left, right, top, bottom of the board in pixels
    workable_area = (args.r - borders[0] - borders[1], args.r - borders[2] - borders[3])
    tile_dimensions = (workable_area[0] / args.l, workable_area[1] / args.l)

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

    positioner = RectTilingPositioning(tile_dimensions[0], tile_dimensions[1], args.l, 5)
    tile_area = (tile_dimensions[0] - 5, tile_dimensions[1] - 5)

    font = ImageFont.truetype("arial.ttf", args.fo)

    for b in range(0, args.n, 1):
        tiles = random.sample(input_content, total_tiles)

        if args.fr:
            tiles[center_tile] = "FREE"

        img = Image.new('RGB', (args.r, args.r), (255, 255, 255))

        for t in range(0, total_tiles, 1):
            drawing = ImageDraw.Draw(img)

            pos = positioner.get_rect_position_for_index(t)

            pos[0] = (borders[0] + pos[0][0], borders[1] + pos[0][1])
            pos[1] = (borders[0] + pos[1][0], borders[1] + pos[1][1])

            drawing.rectangle(pos, width=5, outline="#000000")

            lines = textwrap.wrap(tiles[t], args.tw)
            text_color = (0, 0, 0)

            text_height = font.getbbox(lines[0])[3]

            text_y_pos = pos[0][1] + (tile_area[1] / 2) - (len(lines) *  (text_height / 2))

            for line in lines:
                text_width = font.getbbox(line)[2]
                drawing.text((pos[0][0] + (tile_area[0] - text_width) / 2, text_y_pos), line, font=font, fill=text_color)
                text_y_pos += text_height

        if args.n == 1:
            img.save(args.o, "JPEG")
        else:
            if not os.path.exists(args.o):
                os.makedirs(args.o)

            img.save(os.path.join(args.o, f"board__{b}.jpg"), "JPEG")

if __name__ == "__main__":
    main()
