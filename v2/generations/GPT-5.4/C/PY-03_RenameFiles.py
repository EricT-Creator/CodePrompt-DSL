def _split_extension(filename: str) -> tuple[str, str]:
    stem, dot, suffix = filename.rpartition(".")
    if not dot or not stem:
        return filename, ""
    return stem, f".{suffix}"


def generate_rename_plan(filenames: list[str], pattern: str, start: int = 1) -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []
    counter = start
    for filename in filenames:
        _, extension = _split_extension(filename)
        result.append((filename, f"{pattern.format(n=counter)}{extension}"))
        counter += 1
    return result
