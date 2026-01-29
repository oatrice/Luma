
import os
try:
    with open("test_out.txt", "w") as f:
        f.write("IT WORKS")
    print("Wrote file")
except Exception as e:
    print(e)
