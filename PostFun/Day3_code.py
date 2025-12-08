import numpy as np
import os
import pandas as pd

# List_numb = [987654321111111, 811111111111119 ,234234234234278, 818181911112111]
os.chdir("Y:\\December_challenge")  # Change to the directory containing your simulation files
import pandas as pd

# Read as strings to avoid integer overflow
lines = pd.read_csv("Day3.txt", header=None, dtype=str)[0]

K = 12  # number of digits to keep

def max_subsequence_12(s):
    # Greedy algorithm for lexicographically largest subsequence of length K
    keep = []
    to_remove = len(s) - K  # how many digits we must skip/drop
    
    for digit in s:
        # while we can drop and the previous digit is smaller → drop it
        while to_remove > 0 and keep and keep[-1] < digit:
            keep.pop()
            to_remove -= 1
        keep.append(digit)
    
    # take only the first K digits
    return ''.join(keep[:K])

total = 0

for row in lines:
    best = max_subsequence_12(row)
    total += int(best)

print(total)
