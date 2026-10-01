import sys

import random

<<<<<<< HEAD
#This version creates a conflict
=======
#This file will accept a single filename as a command line argument,
#read the file line by line, output each line with a 1% probability,
#preserve the original line order, and print the sampled lines as the output
>>>>>>> hw_1b

if len(sys.argv) != 2:

    print("Usage: python samplit-davidflanagan04.py <filename>", file=sys.stderr)

    sys.exit(1)

 
filename = sys.argv[1]

 
with open(filename) as f:
<<<<<<< HEAD
    for j in f:
        if random.random() < 0.01:
            print(j, end="")
=======

    for i in f:

        if random.random() < 0.01:

            print(i, end="")
>>>>>>> hw_1b
