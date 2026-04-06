import re

def generate_rename_plan(filenames: list[str], pattern: str, start: int = 1) -> list[tuple[str, str]]:
    plan = []
    counter = start
    for filename in filenames:
        ext = ""
        if "." in filename:
            parts = filename.rsplit(".", 1)
            filename_without_ext = parts[0]
            ext = "." + parts[1]
        else:
            filename_without_ext = filename
        try:
            new_name = pattern.replace("{n:03d}", f"{counter:03d}").replace("{n}", str(counter))
        except:
            new_name = pattern + "_" + str(counter)
        if "{n" not in pattern and "{" not in pattern:
            new_name = pattern
        new_filename = new_name + ext
        plan.append((filename, new_filename))
        counter += 1
    return plan