import numpy as np
import pandas as pd
import os
os.chdir("Y:\\December_challenge")  # Change to the directory containing your simulation files
df = pd.read_csv("Day1.csv")
turn =''
clicker = ''
number = 50
counter = 0
check = 0
for row in df['data']:
    turn =''
    clicker = ''
    for char in row:
        if char.isalpha():
            # turn.append(char)
            turn = char
        elif char.isdigit():
            clicker+= char
    clicker_no = int(clicker)
    dev_no = int(clicker_no/100)
    if dev_no >0:
        ff = 1
    counter = counter + dev_no
    mod_no = np.mod(clicker_no,100)
    if turn == 'L':
        number -= mod_no
        if check == 1:
            check = 0
            number = 100 + number
            continue
        if number < 0 :
            number = 100 + number 
            counter += 1
            continue
    elif turn == 'R':
        number += mod_no
        if check == 1:
            check = 0
            number = number - 100
            continue
        if number > 100:
            number = number - 100
            counter += 1
            continue
    print(number)
    if number == 100:
        number = 0
      
    if  number == 0:
        counter += 1  
        check = 1     
print(counter)
