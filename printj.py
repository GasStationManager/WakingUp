import jsonlines


import sys


fn=sys.argv[1]
fields=sys.argv[2:]

with jsonlines.open(fn) as reader:
  for jo in reader:
    o=jo
    for f in fields:
        o=o[f]
    print(o)
