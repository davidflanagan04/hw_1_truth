import sys
import random
 
if len(sys.argv) != 2:
    print("Usage: python samplit-davidflanagan04.py <filename>", file=sys.stderr)
    sys.exit(1)
 
filename = sys.argv[1]
 
with open(filename) as f:
    for line in f:
        if random.random() < 0.01:
            print(line, end="")