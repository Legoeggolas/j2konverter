import script.j2konverter as j2k
from script.j2konverter import log

import pytest
import random
import os
import zipfile


def test_arch():
    log("\n\nBegin test session")

    tempPath = os.path.join(".", "tests", "temp")
    log(f"Set tempPath = {tempPath}")
    if os.path.isdir(tempPath) is False:
        os.mkdir(tempPath)
        log(f"Created {tempPath} since did not exist")
    else:
        j2k.cleanUp(tempPath)
        os.mkdir(tempPath)
        log(f"Cleaned and created {tempPath}")

    srcPath = os.path.join(tempPath, "src")
    log(f"Set srcPath to {srcPath}")
    if os.path.isdir(srcPath) is False:
        os.mkdir(srcPath)
        log(f"Created {srcPath}")

    n = list(range(1000))
    random.shuffle(n)
    files = []
    for i in n:
        filepath = os.path.join(srcPath, str(i) + ".txt")
        with open(filepath, mode="w") as textfile:
            textfile.writelines([str(os.urandom(random.randint(5, 10))) for _ in range(10)])
        files.append(filepath)

    archPath = os.path.join(tempPath, "test.cbz")
    log(f"Set archPath = {archPath}")
    for file in files:
        j2k.compress(file, archPath)

    assert zipfile.is_zipfile(archPath) == True

    destPath = os.path.join(tempPath, "dest")
    log(f"Set destPath = {destPath}")
    if os.path.isdir(destPath) is False:
        os.mkdir(destPath)
        log(f"Created {destPath}")
    decompFiles = j2k.decompress(archPath, destPath)

    assert len(decompFiles) == len(files)

    for i in range(len(files)):
        original = files[i]
        mirror = decompFiles[i]

        path, ogfname = os.path.split(original)
        path, mrfname = os.path.split(mirror)
        assert ogfname == mrfname

        with open(original, "r") as og, open(mirror, "r") as mr:
            ogdata = og.readlines()
            mrdata = mr.readlines()

            assert len(ogdata) == len(mrdata)

            for j in range(len(ogdata)):
                assert ogdata[j] == mrdata[j]

    j2k.cleanUp(tempPath)
    if os.path.isdir(tempPath):
        os.rmdir(tempPath)
