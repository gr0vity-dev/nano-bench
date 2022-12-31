. venv_nanolocal/bin/activate
cd speedsuite/testcases/nanolocal/saved_ledgers/ && for f in $(ls  *.7z); do py7zr x $f ; done && cd -
cd speedsuite/testcases/nanolocal/saved_blocks/ && for f in $(ls  *.7z); do py7zr x $f ; done && cd -
