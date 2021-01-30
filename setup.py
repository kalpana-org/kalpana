import setuptools
import site
import sys
# This is a workaround to allow --user and -e combined
# See https://github.com/pypa/pip/issues/7953
site.ENABLE_USER_SITE = "--user" in sys.argv[1:]
setuptools.setup()
