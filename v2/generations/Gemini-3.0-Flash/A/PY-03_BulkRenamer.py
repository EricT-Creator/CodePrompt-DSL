import os

def generate_rename_plan(filenames: list[str], pattern: str, start: int = 1) -> list[tuple[str, str]]:
    plan = []
    for i, old_name in enumerate(filenames, start=start):
        base, ext = os.path.splitext(old_name)
        new_base = pattern.format(n=i)
        new_name = f"{new_base}{ext}"
        plan.append((old_name, new_name))
    return plan

if __name__ == "__main__":
    files = ["img_1.png", "vacation.jpg", "notes.txt"]
    template = "photo_{n:03d}"
    print(generate_rename_plan(files, template))
    # Expected: [('img_1.png', 'photo_001.png'), ('vacation.jpg', 'photo_002.jpg'), ('notes.txt', 'photo_003.txt')]
