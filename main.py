import logging
import argparse
from pathlib import Path

from font import FontFile
from build_files import BuildContext, FontAPK
from jar_tools import APKToolJar, APKSignerJar, java_check
from utils import (
    files_to_process,
    output_path_validator,
    gen_unique_apk_path
)


logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

fontTools_logger = logging.getLogger("fontTools")
fontTools_logger.setLevel(logging.ERROR)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

file_handler = logging.FileHandler('log_file.log')
file_handler.setLevel(logging.DEBUG)

console_formatter = logging.Formatter(
    '%(name)s - %(levelname)s - %(message)s'
)
file_formatter = logging.Formatter(
    '%(asctime)s - %(name)s:%(lineno)d - %(levelname)s - %(message)s'
)

console_handler.setFormatter(console_formatter)
file_handler.setFormatter(file_formatter)

logger.addHandler(console_handler)
logger.addHandler(file_handler)

args_help = {
    "input": """Input path, can be a file or a directory 
                containing fonts. Currently supports TTF, 
                OTF, WOFF and WOFF2 files.""",
    "output": """Output directory, the generated apk files
                should appear here. The apk files will have 
                the same name as the font file. This cannot 
                be a file path."""
}


def main():
    parser = argparse.ArgumentParser(description='LG Font Gen')
    parser.add_argument(
        '-o', 
        '--output', 
        type=output_path_validator, 
        help=args_help['output']
    )
    parser.add_argument(
        'input_path', 
        type=files_to_process, 
        help=args_help['input']
    )
    args = parser.parse_args()

    java_check()

    files = args.input_path
    output_path = args.output if args.output != None else Path().absolute()

    logger.info(f"Input path: {args.input_path}")
    logger.info(f"Output path: {output_path}")

    file_count = len(files)
    logger.info(f"Found {len(files)} compatible font files: {files}")

    for count, font_path in enumerate(files, start=1):
        count_str = f"[{count}/{file_count}]"
        logger.info(f"Processing font {count_str}: {font_path}")
        font_file = FontFile(font_path)
        font_file.sanitise_name()
        font_file.subset_font()

        logger.info("Preparing build files")
        build_files = Path("apk_build_files")
        
        with BuildContext(build_files) as bc:
            logger.info("Setting files and values")
            font_apk = FontAPK(bc.apk_dir)
            font_apk.set_font_ttf(font_file)
            font_apk.set_font_data()

            full_name = font_file.get_combined_name(sep=" - ")
            font_apk.set_font_xml(full_name)
            font_apk.set_manifest(full_name)
            font_apk.set_strings(full_name)

            logger.info("Building apk")
            apktool = APKToolJar(bc.apktool_path.absolute())
            apk_path = gen_unique_apk_path(font_file.font_file_name, output_path)
            apktool.build(bc.apk_dir, apk_path, output_path)

            logger.info("Signing apk")
            apksigner = APKSignerJar(bc.apksigner_path.absolute())
            apksigner.sign(apk_path, output_path)
            logger.info(f"Saved apk to: {apk_path}")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger.error(e)
        raise e