import os
from glob import glob
from difflib import unified_diff

def test(in_file):
    print "Testint the file:", in_file
    out_file = "/tmp/_pyvascript_test.out"
    os.system("python %s > %s" % (in_file, out_file))
    out_file_correct = os.path.splitext(in_file)[0] + ".out"
    f1 = open(out_file_correct).read()
    f2 = open(out_file).read()
    if f1 == f2:
        print "    [OK]"
    else:
        print "    [FAIL]"

def main():
    files = glob("examples/*.py")
    for file in files:
        test(file)

main()
