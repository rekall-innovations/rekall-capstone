Local patches generated using:

diff -Nur capstone_source/bindings/python/capstone/  capstone/ > patches/000001.patch

Apply the patch with (Already done by setup.py sdist):

patch -d capstone/ -i patches/000001.patch
