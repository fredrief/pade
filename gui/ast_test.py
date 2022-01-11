import ast

with open("/home/fredrief/projects/cbadcsim/Projects/Comparison/compare_nominal/compare_nominal_tb.py", "r") as source:
    tree = ast.parse(source.read())
    print(tree)
