import zipfile
from shutil import rmtree
import os
import sys
import pydantic
import heapq
from datetime import datetime
from progress.bar import ShadyBar


class ProgressBar(ShadyBar):
    """A generic Progress Bar with a custom suffix.

    """
    suffix = "[%(index)d/%(max)d] [%(avg).3fs/item] [%(elapsed_td)ss/%(eta_td)ss]"


def log(msg: str, new=False) -> None:
    """Logs a message string into a log.txt

    Args:
        msg (str): The message to log.
        new (bool, optional): If set to true, erases all previous contents of the file. Defaults to False.
    """
    log = open(os.path.join(".", "log.txt"), mode="a" if not new else "w")
    log.write(f"[{str(datetime.now())}]: {msg}\n")
    log.close()


def logprint(msg: str) -> None:
    """Prints and logs at the same time.

    Args:
        msg (str): Message to print and log.
    """
    print(msg)
    log(msg)


class Metadata(pydantic.BaseModel):
    scanner: str = ""
    volume: int = 0
    chapter: int = 0
    page: int = 0
    name: str = ""
    """Pydantic data class. Used to store the metadata.
    """

    def __lt__(self, other):
        if self.volume == other.volume:
            if self.chapter == other.chapter:
                return self.page < other.page
            else:
                return self.chapter < other.chapter
        else:
            return self.volume < other.volume


def cleanStr(inputStr: str) -> str:
    """Cleans a string until it can represent a numeric.

    Args:
        inputStr (str): The string to clean.

    Returns:
        str: A string that represents a numeric.
    """
    temp = list(inputStr)
    while temp and temp[0].isdigit() is False:
        temp.pop(0)
    while temp and temp[-1].isdigit() is False:
        temp.pop(-1)

    temp = "".join(temp)

    return temp


#! In a dire need for refactoring
def fillMetadata(filename: str, format: str) -> Metadata:
    """Matches a given pattern to a filename to extract metadata.

    Args:
        filename (str): The filename containing metadata.
        format (str): The preset pattern to match with.

    Returns:
        Metadata: The extracted metadata.
    """
    data = Metadata()
    tokens = format.split(sep="|")
    log(f"Detected format: {tokens}")
    lexemes = filename.strip().split(sep=" ")
    log(f"Detected lexemes: {lexemes}")

    table = dict()

    index = 0

    for token in tokens:
        if index >= len(lexemes):
            break

        if token.startswith("["):
            tok = token[1:-1]
            if tok not in table.keys():
                table[tok] = ""

            while not lexemes[index].endswith("]"):
                table[tok] = " ".join([table[tok], lexemes[index]])
                index += 1

            table[tok] = " ".join([table[tok], lexemes[index]])
            index += 1
            table[tok] = table[tok].strip()[1:-1]
            continue

        if token.startswith("loop"):
            tok = token[4:]

            while lexemes[index] != tok:
                index += 1

            continue

        if token not in table.keys():
            table[token] = ""

        table[token] = "".join([table[token], lexemes[index]])
        index += 1

    data.volume = cleanStr(table["volume"])
    data.chapter = cleanStr(table["chapter"])
    data.page = cleanStr(table["page"])
    data.name = table["name"]
    data.scanner = table["scanner"] if "scanner" in table.keys() else ""

    return data


def genArchName(data: Metadata) -> str:
    """Generates a nice looking archive name from some metadata.

    Args:
        data (Metadata): The metadata used to generate the archive name.

    Returns:
        str: The archive name.
    """
    j2kfilename = ["Vol. " + data.volume, " Ch. " + data.chapter, " - " + data.name, ".cbz"]

    return "".join(j2kfilename)


def decompress(archPath: str, destPath: str) -> list:
    """Decompresses a CBZ archive.

    Args:
        archPath (str): Path to the archive.
        destPath (str): Path to the output folder.

    Returns:
        list: A list of extracted files.
    """
    if os.path.isfile(archPath) is not True:
        logprint(f"No such file: {archPath}")
        #! Add exception handling

    log(f"Decompressing: {archPath}")
    log(f"Extracting to: {destPath}")
    extractedFiles = list()

    with zipfile.ZipFile(archPath, mode="r") as arch:
        path, name = os.path.split(archPath)
        bar = ProgressBar(message="Decompressing", max=len(arch.namelist()))

        log(f"Extracting to: {destPath}")
        for file in arch.namelist():
            arch.extract(file, path=destPath)
            log(f"Extracted {file}")
            extractedFiles.append(os.path.join(destPath, file))
            bar.next()
    print("\n")
    return extractedFiles


def compress(srcPath: str, archPath: str) -> None:
    """Adds a single file to an archive.

    Args:
        srcPath (str): Path to the file.
        archPath (str): Path to the archive.
    """
    if os.path.isfile(srcPath) is not True:
        logprint(f"No such file: {srcPath}")
        #! Add exception handling

    log(f"Compressing {srcPath}")
    log(f"Compressing in {archPath}")

    with zipfile.ZipFile(archPath, mode="a", compression=zipfile.ZIP_STORED,
                         compresslevel=None) as arch:
        filepath, filename = os.path.split(srcPath)
        arch.write(srcPath, arcname=filename)
        log(f"Compressed {srcPath} as {filename}")


def cleanUp(dir: str) -> None:
    """Recursively deletes everything in a directory.

    Args:
        dir (str): Path to the directory.
    """
    log(f"Removing temporary directory: {dir}")
    rmtree(dir)
    pass


def main():
    log("New Session", new=True)
    src = sys.argv[1].strip()
    format = sys.argv[2].strip()
    dest = ""
    if len(sys.argv) >= 4:
        dest = sys.argv[3].strip()

    # Generate a list of archives to process
    archives = list()
    if os.path.isfile(src):
        if zipfile.is_zipfile(src):
            archives.append(src)
        else:
            logprint(f"Not an archive: {src}")
    elif os.path.isdir(src):
        for filename in os.listdir(src):
            filepath = os.path.join(src, filename)
            if zipfile.is_zipfile(filepath):
                archives.append(filepath)
    else:
        logprint("No archives found")

    # If the output folder already exists, clean it
    if not dest:
        dest = os.path.join(".", "output")
    if os.path.isdir(dest) is True:
        cleanUp(dest)

    os.mkdir(dest)

    # Process each archive
    for filepath in archives:
        path, name = os.path.split(filepath)
        print(f"\nProcessing [{name}]")

        class ArchOrder:
            """Helper class to facilitate ordered sorting of pages using a priority queue.
            """

            def __init__(self, filepath: str, format: str) -> None:
                self.filepath = filepath
                dir, filename = os.path.split(filepath)
                self.metadata = fillMetadata(filename, format)

            def __lt__(self, other):
                return self.metadata < other.metadata

        # Decompress the current archive into a temporary directory
        files = decompress(filepath, os.path.join(dest, "temp"))

        # Add all files to the heap, using the metadata to sort them in an ascending order for reading
        heapProgress = ProgressBar(message="Exploring files", max=len(files))
        heap = []
        for file in files:
            heapq.heappush(heap, ArchOrder(file, format))
            heapProgress.next()
        print("\n")

        # Compress back into smaller archives based on chapters
        # Remove all the temporary files after done, leaving only an archive
        compressProgress = ProgressBar(message="Compressing", max=len(files))
        lastArchName = ""
        while heap:
            curr = heapq.heappop(heap)
            archName = genArchName(curr.metadata)
            if not lastArchName:
                lastArchName = archName
            if archName != lastArchName:
                log(f"{lastArchName} - DONE!")
                lastArchName = archName

            archPath = os.path.join(dest, archName)
            compress(curr.filepath, archPath)
            compressProgress.next()
        print("\n")

        # Remove temp files
        cleanUp(os.path.join(dest, "temp"))

    logprint("All done!")


if __name__ == "__main__":
    main()
