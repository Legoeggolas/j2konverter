import zipfile
from shutil import rmtree
import os
import sys
import pydantic
import heapq
from datetime import datetime
from progress.bar import ShadyBar


class ProgressBar(ShadyBar):
    suffix = "[%(index)d/%(max)d] [%(avg).3fs/item] [%(elapsed_td)ss/%(eta_td)ss]"


def log(msg: str, new=False):
    log = open(os.path.join(".", "log.txt"), mode="a" if not new else "w")
    log.write(f"[{str(datetime.now())}]: {msg}\n")
    log.close()


def logprint(msg: str):
    print(msg)
    log(msg)


class Metadata(pydantic.BaseModel):
    scanner: str = ""
    volume: int = 0
    chapter: int = 0
    page: int = 0
    name: str = ""

    def __lt__(self, other):
        if self.volume == other.volume:
            if self.chapter == other.chapter:
                return self.page < other.page
            else:
                return self.chapter < other.chapter
        else:
            return self.volume < other.volume


def cleanStr(inputStr: str) -> str:
    temp = list(inputStr)
    while temp and temp[0].isdigit() is False:
        temp.pop(0)
    while temp and temp[-1].isdigit() is False:
        temp.pop(-1)

    temp = "".join(temp)

    return temp


def fillMetadata(filename: str, format: str) -> Metadata:
    data = Metadata()
    tokens = format.split(sep="|")
    log(f"Detected format: {tokens}")
    lexemes = filename.strip().split(sep=" ")

    table = dict()
    for i in range(len(tokens)):
        if tokens[i].strip() not in table.keys():
            table[tokens[i].strip()] = ""

        table[tokens[i].strip()] = " ".join([table[tokens[i].strip()], lexemes[i].strip()]).strip()

    data.volume = cleanStr(table["volume"])
    data.chapter = cleanStr(table["chapter"])
    data.page = cleanStr(table["page"])
    data.name = table["name"]

    return data


def genArchName(data: Metadata) -> str:
    j2kfilename = [
        data.scanner + "_" if data.scanner else "", "Vol. " + data.volume, " Ch. " + data.chapter,
        " - " + data.name, ".cbz"
    ]

    return "".join(j2kfilename)


def decompress(archPath: str, destPath: str) -> list:
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


def compress(srcPath: str, archPath: str):
    if os.path.isfile(srcPath) is not True:
        logprint(f"No such file: {srcPath}")
        #! Add exception handling

    log(f"Compressing {srcPath}")
    log(f"Compressing in {archPath}")

    with zipfile.ZipFile(archPath, mode="a", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=9) as arch:
        filepath, filename = os.path.split(srcPath)
        arch.write(srcPath, arcname=filename)
        log(f"Compressed {srcPath} as {filename}")


def cleanUp(dir: str):
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

    if not dest:
        dest = os.path.join(".", "output")
    if os.path.isdir(dest) is True:
        cleanUp(dest)

    os.mkdir(dest)

    for filepath in archives:
        path, name = os.path.split(filepath)
        print(f"\nProcessing [{name}]")

        class ArchOrder:

            def __init__(self, filepath: str, format: str) -> None:
                self.filepath = filepath
                dir, filename = os.path.split(filepath)
                self.metadata = fillMetadata(filename, format)

            def __lt__(self, other):
                return self.metadata < other.metadata

        files = decompress(filepath, os.path.join(dest, "temp"))

        heapProgress = ProgressBar(message="Exploring files", max=len(files))
        heap = []
        for file in files:
            heapq.heappush(heap, ArchOrder(file, format))
            heapProgress.next()
        print("\n")

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
