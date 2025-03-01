import re
import logging
import subprocess
from pathlib import Path


logger = logging.getLogger(__name__)

JAVA_PATH = "java" 


def java_check():
    """
    Checks for java by running `java --version`
    """
    command = JAVA_PATH + " --version"
    try:
        run_subp(command)
    except FileNotFoundError as e:
        raise Exception("Java not found on path! Install java before continuing.")


def run_subp(command, shell=False, cwd=None, log_output=True):
    """
    Run commands using subprocess.run

    Args:
        command (str): Command to be executed.
        shell (bool): To use shell or not.
        cwd (str): Work directory.
        log_output (bool): Logs output at debug level.
    """
    if not shell:
        command = shell_split(command)
    
    logger.debug(f"Running command: {command}")
    output = subprocess.run(command, capture_output=True, shell=shell, cwd=cwd)

    if output.returncode != 0:
        raise Exception(output.stderr.decode(errors="ignore"))
    elif output.stdout and log_output:
        logger.debug(output.stdout.decode(errors="ignore"))


class JarHandler:
    """
    Base class for handling JAR files. On init the given file path
    is checked for being a valid jar file. 

    Args:
        jar_path (Path): The path to the JAR file.
    """
    def __init__(self, jar_path: Path):
        validate_file(jar_path, "*.jar")

        self.path = jar_path
        self.command = f'{JAVA_PATH} -jar "{jar_path}"'

    def run(self, args, shell=False, cwd=None, log_output=True):
        full_command = f"{self.command} {args}"

        run_subp(full_command, shell, cwd, log_output)


def validate_file(file_path: Path, pattern: str):
    if not file_path.exists():
        raise Exception(f"Given file path does not exist: {file_path}")

    if not file_path.match(pattern):
        raise Exception(f"Given {file_path = } does not match the {pattern = }")


def shell_split(command: str) -> list:
    """
    Splits the command by whitespace. Double quoted portions are not split.

    Args:
        command (str): Command to be executed.

    Returns:
        list: Command split into individual portions
    """
    pattern = r'"[^"]*"|[^"\s]\S*'
    matches = re.findall(pattern, command)
    return [match.strip('"') for match in matches]


class APKToolJar(JarHandler):
    """
    This class inherits from `JarHandler`. It encapsulates operations
    that can be performed using APKTool.

    Links:
        https://apktool.org/
    
    Args:
        jar_path (Path): The path to APKTool JAR executable.
    """
    def __init__(self, jar_path):
        super().__init__(jar_path)

    def build(self, apk_dir, output_path, work_dir):
        if apk_dir.is_file():
            raise Exception(f"Given apk_dir is a file, needs to be a directory: {apk_dir}")

        self.run(f'b {apk_dir} -o "{output_path}"', cwd=work_dir)


class APKSignerJar(JarHandler):
    """
    This class inherits from `JarHandler`. It encapsulates operations
    that can be performed using uber-apk-signer. This is used to sign
    the apk after it is built by APKTool.
    
    Links:
        https://github.com/patrickfav/uber-apk-signer
    
    Args:
        jar_path (Path): The path to uber-apk-signer JAR executable.
    """
    def __init__(self, jar_path):
        super().__init__(jar_path)

    def sign(self, apk_path, work_dir):
        validate_file(apk_path, "*.apk")
        self.run(f'--overwrite -a "{apk_path}"', cwd=work_dir)