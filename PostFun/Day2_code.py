import numpy as np
import pandas as pd
import os 

list_range='959516-995437,389276443-389465477,683-1336,15687-26722,91613-136893,4-18,6736-12582,92850684-93066214,65-101,6868676926-6868700146,535033-570760,826141-957696,365650-534331,1502-2812,309789-352254,79110404-79172400,18286593-18485520,34376-65398,26-63,3333208697-3333457635,202007-307147,1859689-1936942,9959142-10053234,2318919-2420944,5142771457-5142940464,1036065-1206184,46314118-46413048,3367-6093,237-481,591751-793578'
# list_range = '11-22,95-115,998-1012,1188511880-1188511890,222220-222224,1698522-1698528,446443-446449,38593856-38593862,565653-565659,824824821-824824827,2121212118-2121212124'
list_range = list_range.split(',')
# sum = 0
# for ii in range(len(list_range)):
#     range_part = list_range[ii]
#     start = int(range_part.split('-')[0])
#     end = int(range_part.split('-')[1])
#     for num in range(start, end + 1):
#         check = 0
#         counter = 1
#         tens = num
#         while check == 0:
#             tens = int(tens / 10)
#             if tens > 0:
#                 counter +=1
#             else:
#                 check = 1
#         num_sec = num % pow(10,counter/2) 
#         num_first = int(num / pow(10,counter/2)) 
#         # num_sec = num_sec * pow(10,counter/2)  
#         if num_sec == num_first:
#             sum += num
            
# print(sum)


sum = 0
for ii in range(len(list_range)):
    range_part = list_range[ii]
    start = int(range_part.split('-')[0])
    end = int(range_part.split('-')[1])
    for num in range(start, end + 1):
        check = 0
        counter = 1
        tens = num
        while check == 0:
            tens = int(tens / 10)
            if tens > 0:
                counter +=1
            else:
                check = 1
        s = str(num)
        L = len(s)
        is_rep = False

        for block in range(1, L // 2 + 1):
            if L % block == 0:
                piece = s[:block]
                if piece * (L // block) == s:
                    is_rep = True
                    break

        if is_rep:
            sum += num
        
        # rem = num
        # rem_old = -1
        # check_2 = 0
        # qq = 1
        # if num == 1011:
        #     AA = 1
        # while check_2 == 0:
        #     rem = num % pow(10,qq)
        #     if rem == rem_old:
        #         break
        #     rem_old = rem
        #     integ_num = int(num / pow(10,qq))
        #     qq += 1
        #     if rem == 0:
        #         continue
        #     if integ_num == 0:
        #         check_2 = 1
        #     temp1 = integ_num / rem
            
        #     temp2 = np.mod(temp1,10)
        #     for kk in str(int(temp1)):
        #             if kk != '0' and kk != '1':
        #                 temp2 = 0
        #     if temp2 == 1:
        #         print(num)
        #         sum += num
        #         check_2 = 1
            
print(sum)