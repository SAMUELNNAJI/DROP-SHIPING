import io
import os
import sys

os.chdir(r"C:\Users\ADMIN\Desktop\DROP SHIPING")

f = sys.argv[1] if len(sys.argv) > 1 else "templates/dashboards/admin/featured.html"
start = int(sys.argv[2]) if len(sys.argv) > 2 else 0
end = int(sys.argv[3]) if len(sys.argv) > 3 else 99999
t = io.open(f, encoding="utf-8").read()
print("LEN", len(t))
print(t[start:end])