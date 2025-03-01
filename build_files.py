import shutil
import logging
from pathlib import Path
from tempfile import TemporaryDirectory

from font import FontData, FontFile
from utils import sanitise_alphanum


logger = logging.getLogger(__name__)


class BuildContext(TemporaryDirectory):
    """
    This class inherits from `TemporaryDirectory` and provides a temp 
    directory for building files. It copies the apk files to the temp dir
    and encapsulates the paths for the apk dir and jar tools. The temp
    directory is cleaned up on exit.

    Args:
        build_files (Path): The path to the build files.

    Example:
        with BuildContext(build_files=Path("apk_build_files")) as bc:
            # Perform build operations within the temporary directory
            pass
    """
    def __init__(self, build_files: Path):
        super().__init__()

        if not build_files.exists():
            raise Exception(f"Apk build files not found: {build_files}")
        
        apk_dir = build_files / "app-debug"
        if not apk_dir.exists():
            raise Exception(f"Apk dir not found in apk build files: {apk_dir}")
        
        self.tmp_dir = Path(self.name)
        self.apk_dir = self.tmp_dir / "app-debug"
        shutil.copytree(apk_dir, self.apk_dir)

        self.apktool_path = build_files / "apktool.jar"
        self.apksigner_path = build_files / "uber-apk-signer-1.2.1.jar"
        
    def __enter__(self):
        return self


class FontAPK:
    """
    Encapsulates the paths and operations to be performed on the apk
    directory.

    Args:
        apk_base_dir (Path): Path to the apk directory.
    """
    def __init__(self, apk_base_dir: Path):
        self.root_path = apk_base_dir
        self.font_data_path = apk_base_dir / "assets/font.dat"
        self.font_xml_path = apk_base_dir / "assets/font.xml"
        self.font_ttf_path = apk_base_dir / "assets/font.ttf"
        self.manifest_path = apk_base_dir / "AndroidManifest.xml"
        self.strings_path = apk_base_dir / "res/values/strings.xml"

        self.compile_reqs = {
            "font_data": False,
            "font_xml": False,
            "font_ttf": False,
            "manifest": False,
            "strings": False,
        }

        self.compiled_apk_path = None

    def set_font_xml(self, value: str):
        value = sanitise_alphanum(value)
        replace_content(
            self.font_xml_path,
            "$$FONT_NAME$$",
            value
        )
        self.compile_reqs["font_xml"] = True
        
    def set_font_ttf(self, font_file: FontFile):
        font_file.save_to(self.font_ttf_path)
        self.compile_reqs["font_ttf"] = True

    def set_manifest(self, value: str):
        value = sanitise_alphanum(value)
        replace_content(
            self.manifest_path,
            "$$FONT_NAME$$",
            value
        )
        self.compile_reqs["manifest"] = True

    def set_strings(self, value: str):
        replace_content(
            self.strings_path,
            "$$FONT_NAME$$",
            value
        )
        self.compile_reqs["strings"] = True

    def set_font_data(self):
        if not self.compile_reqs["font_ttf"]:
            raise Exception("font_ttf needs to be set before calling set_font_data")

        font_data = FontData(self.font_ttf_path)
        value = font_data.get_font_data()

        with open(self.font_data_path, 'wb') as fdat:
            fdat.write(value)
            self.compile_reqs["font_data"] = True

    def is_read_to_complie(self) -> bool:
        return all(self.compile_reqs.values())


def replace_content(file_path, old_str, new_str):
    with open(file_path, "r") as target:
        contents = target.read()
        if old_str not in contents:
            logger.warning(f'replace_content: "{old_str}" not found in "{file_path}"')

    with open(file_path, "w") as target:
        target.write(contents.replace(old_str, new_str))