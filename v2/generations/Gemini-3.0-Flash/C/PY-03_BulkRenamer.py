import os

def generate_rename_plan(filenames, pattern, start=1):
    plan = []
    for idx, old in enumerate(filenames, start):
        ext = os.path.splitext(old)[1]
        new = pattern.format(n=idx) + ext
        plan.append((old, new))
    return plan
