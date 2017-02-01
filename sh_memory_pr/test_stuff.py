import time
print"something else",
time.sleep(1)
print"lolo"

import sys
import time

for i in range(10):
    sys.stdout.write("\r{0}>".format("="*i))
    sys.stdout.flush()
    time.sleep(0.5)

# print"2345"
