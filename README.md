# custom-bingo
A simple, custom bingo script written in Python, using PIL.

# How to Use
1. Transfer the bingo.py script file to your machine.
2. Via command line, cd to the scipt's directory.
3. Type `python bingo.py input output`, substituting input and output for your desired paths, and press enter.
4. Open the JPG file at the output path you gave to confirm the input values were used to create the board.

# Requirements
This script uses [Pillow](https://pypi.org/project/pillow/) to write a bingo board to an image file.

# Additional Details
I don't plan to update or maintain this regularly.

This was created because other similar projects or guides I tried were too inconvenient with set up, did not display properly, was created in unfamiliar language, or was an online service. I didn't find exactly what I wanted so I made this.

This script was pretty quickly glued together from other projects' code and guides, you can probably pick out elements that I wanted to impliment, but ultimately I do not have the time for it.

As is, this script will generate an image of a simple bingo board, with each tile containing a random value from the input file. There's additional arguments you can read to customize the bingo board.
