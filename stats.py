import sys
import os

path = sys.argv[1]
match_count = 0
mismatch_count = 0
files = os.listdir(path + '/original')
for file in files:
    if os.path.exists(path + '/examples-ttl/' + file.replace('.json', '.ttl')):
        match_count += 1
    else:
        mismatch_count += 1
print(len(files))
print(match_count, mismatch_count)

