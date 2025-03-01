from pathlib import Path
from datetime import datetime


def sanitise_alphanum(name: str, to_ignore = "") -> str:
    """
    Sanitise a string by removing non-alphanumeric characters.

    Args:
        name (str): The input string.
        to_ignore (str): Non alphanumeric chars that wont be removed.

    Returns:
        str: The sanitised string containing only alphanumeric characters.
    """
    return ''.join(char for char in name if char.isalnum() or char in to_ignore)


def get_ext(path: Path) -> str:
    """
    Returns the file extension of the given path.

    Args:
        path (Path): The file path.

    Returns:
        str: The file extension (excluding the leading dot).
    """
    file_ext = path.suffix.lstrip(".").lower()
    return file_ext


def get_basename_wo_ext(path: Path) -> str:
    """
    Returns the basename of the given path without its file extension.

    Args:
        path (Path): The file path.

    Returns:
        str: The basename without file extension.

    Examples:
        >>> get_basename_wo_ext(Path("path/to/example.txt"))
        'example'
        >>> get_basename_wo_ext(Path("image.jpg"))
        'image'

    Helpers:
        get_ext
    """
    file_ext = get_ext(path)
    file_name = path.name.replace(f".{file_ext}", "")
    return file_name


def output_path_validator(output: str) -> Path:
    """
    Check if the given output path is a directory.
    Returns current path if output is none.

    Args:
        output (str): The path to the output directory.

    Returns:
        Path: Path object constructed from output.

    """
    # if output == None:
    #     return Path().absolute()
    
    output_path = Path(output)

    if output_path.is_file():
        raise Exception(f"Invalid output path, output cannot be a file path!")
    
    if not output_path.exists:
        raise Exception(f"Output path {str(output_path)} does not exist")
    
    return output_path


def valid_font(path: Path) -> bool:
    """
    Check if the given path extension matches supported font types.
    Currently supports TTF, OTF, WOFF and WOFF2 files.

    Args:
        path (Path): The path to the file.

    Returns:
        bool: Does the file path match any of the supported file type?

    """
    patterns = ["*.ttf", "*.otf", "*.woff", "*.woff2"]
    return any([path.match(p) for p in patterns])


def files_to_process(input_path: str) -> list:
    """
    Returns a list of files to be processed from the given input path.

    Args:
        input_path (str): The path to the directory or file to process.

    Returns:
        list: A list of file paths to be processed.

    Helpers:
        valid_font
    """
    input_path = Path(input_path)

    if not input_path.exists():
        raise Exception(f"Input path {str(input_path)} does not exist")
    
    if input_path.is_file():
        if valid_font(input_path):
            return [input_path]
        else:
            raise Exception(f"Input path {str(input_path)} is not a compatible file")

    if input_path.is_dir():
        input_files = [p for p in input_path.iterdir() if valid_font(p)]

        if len(input_files) == 0:
            raise Exception(f"Input path {str(input_path)} does not contain any compatible files")
        return input_files


def gen_unique_apk_path(font_file_name: str, output_dir: Path) -> Path:
    """
    Generates the output apk name. Uses the same name as the font file.
    Adds a timestamp if there already exists an apk file with the same name. 

    Args:
        font_file_name (str): The font file name w/o the extension.

    Returns:
        Path: Output path plus the unique apk name.

    """
    suffix = ".apk"
    possible_path = output_dir / (font_file_name + suffix)

    if possible_path.exists():
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        suffix = f"_{timestamp}.apk"
    
    return output_dir / (font_file_name + suffix)