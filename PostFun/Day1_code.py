dp = 0
dp_old = 0
dp_cum = 0
qq = 0
nums = [2,2,3,3,3,4]
nn = len(nums)
points = 0
for ii,val in enumerate(nums):
    c_num = nums.count(val)
    c_low = nums.count(val - 1)
    c_high = nums.count(val + 1)
    points += max (c_high,c_low,c_num)