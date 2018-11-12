import os
import shutil
import errno


def clearDir(directory: str) -> None:
    """ Clears a directory """

    for filename in os.listdir(directory):
        filepath = os.path.join(directory, filename)
        try:
            if os.path.isfile(filepath):
                os.unlink(filepath)

            elif os.path.isdir(filepath):
                shutil.rmtree(filepath)

        except Exception as e:
            raise e


def createDir(dir: str) -> None:
    """ Creates the given dir if not exists """
    try:
        os.makedirs(dir)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise e


def writeInputFile(content: str, filepath: str, filename: str) -> str:
    """ Writes an input file with the given code to the given path """
    filepath = os.path.join(*[filepath, filename + ".input"])

    with open(filepath, 'w+') as file:
        file.write(content)

    return filepath
