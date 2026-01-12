#!/usr/bin/env python3

# 
# This installs the module vahabzadeh2026a and its dependencies.
# The exact revisions used are listed in the table below.
# However, note that this script may also apply further patches.
# If so, all patches are required to be the current folder, or,
# in the one that you specified as argument to this script.
# 
# 
#  |              module name              |      branch name      |                 commit sha                 |         commit date         |
#  |---------------------------------------|-----------------------|--------------------------------------------|-----------------------------|
#  |              dune-subgrid             |  origin/releases/2.9  |  41ab447c59ea508c4b965be935b81928e7985a6b  |  2023-12-16 13:51:43 +0000  |
#  |            vahabzadeh2026a            |      origin/main      |                      -                     |                             |
#  |          dune-localfunctions          |  origin/releases/2.9  |  f2c7cfb96327fbfd29744dccf5eac015a1dfa06f  | 2023-12-16 13:51:43 +0000  |
#  |             dune-geometry             |  origin/releases/2.9  |  7d5b1d81ad997f81637ac97f753f80a64ff9cdb0  | 2023-12-16 13:50:03 +0000  |
#  |              dune-common              |  origin/releases/2.9  |  ad69f2ab2d78313e1111069fdd2539104fc4dab1  | 2023-12-26 20:29:09 +0000  |
#  |                 dumux                 |  origin/releases/3.8  |  c8f61c1f81ca511415c656e834cc0ded17572025  | 2023-12-01 10:12:26 +0000  |
#  |              dune-uggrid              |  origin/releases/2.9  |  e26f81ff7d84f5d7b228edb3313beae592d502f7  | 2023-12-16 13:51:01 +0000  |
#  |               dune-grid               |  origin/releases/2.9  |  75b66b0ebf0656e21af08798188b3d2848c9574d  | 2023-12-16 13:50:39 +0000  |
#  |               dune-istl               |  origin/releases/2.9  |  1582b9e200ad098d0f00de2c135f9eed38508319  | 2023-10-19 09:15:16 +0000  |

import os
import sys
import subprocess

top = "DUMUX"
os.makedirs(top, exist_ok=True)


def runFromSubFolder(cmd, subFolder):
    folder = os.path.join(top, subFolder)
    try:
        subprocess.run(cmd, cwd=folder, check=True)
    except Exception as e:
        cmdString = ' '.join(cmd)
        sys.exit(
            "Error when calling:\n{}\n-> folder: {}\n-> error: {}"
            .format(cmdString, folder, str(e))
        )


def installModule(subFolder, url, branch, revision):
    targetFolder = url.split("/")[-1]
    if targetFolder.endswith(".git"):
        targetFolder = targetFolder[:-4]
    if not os.path.exists(targetFolder):
        runFromSubFolder(['git', 'clone', url, targetFolder], '.')
        runFromSubFolder(['git', 'checkout', branch], subFolder)
        runFromSubFolder(['git', 'reset', '--hard', revision], subFolder)
    else:
        print(
            f"Skip cloning {url} since target '{targetFolder}' already exists."
        )

print("Installing dune-subgrid")
installModule("dune-subgrid", "https://gitlab.dune-project.org/extensions/dune-subgrid.git", "origin/releases/2.9", "41ab447c59ea508c4b965be935b81928e7985a6b", )

print("Installing Mixing-in-UHS")
installModule("Mixing-in-UHS", "https://github.com/ehsan-vahabzadeh/Mixing-in-UHS", "origin/main", "origin/main", )

print("Installing dune-localfunctions")
installModule("dune-localfunctions", "https://gitlab.dune-project.org/core/dune-localfunctions.git", "origin/releases/2.9", "f2c7cfb96327fbfd29744dccf5eac015a1dfa06f", )

print("Installing dune-geometry")
installModule("dune-geometry", "https://gitlab.dune-project.org/core/dune-geometry.git", "origin/releases/2.9", "7d5b1d81ad997f81637ac97f753f80a64ff9cdb0", )

print("Installing dune-common")
installModule("dune-common", "https://gitlab.dune-project.org/core/dune-common.git", "origin/releases/2.9", "ad69f2ab2d78313e1111069fdd2539104fc4dab1", )

print("Installing dumux")
installModule("dumux", "https://git.iws.uni-stuttgart.de/dumux-repositories/dumux.git", "origin/releases/3.8", "c8f61c1f81ca511415c656e834cc0ded17572025", )

print("Installing dune-uggrid")
installModule("dune-uggrid", "https://gitlab.dune-project.org/staging/dune-uggrid", "origin/releases/2.9", "e26f81ff7d84f5d7b228edb3313beae592d502f7", )

print("Installing dune-grid")
installModule("dune-grid", "https://gitlab.dune-project.org/core/dune-grid.git", "origin/releases/2.9", "75b66b0ebf0656e21af08798188b3d2848c9574d", )

print("Installing dune-istl")
installModule("dune-istl", "https://gitlab.dune-project.org/core/dune-istl.git", "origin/releases/2.9", "1582b9e200ad098d0f00de2c135f9eed38508319", )

print("Configuring project")
runFromSubFolder(
    ['./dune-common/bin/dunecontrol', '--opts=dumux/cmake.opts', 'all'],
    '.'
)
