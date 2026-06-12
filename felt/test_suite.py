"""
Test Suite.
"""

import sys
import os
import unittest
import tempfile
from osgeo import gdal
from qgis.core import Qgis

try:
    from pip import main as pipmain
except ImportError:
    from pip._internal import main as pipmain

try:
    import coverage
except ImportError:
    pipmain(['install', 'coverage'])
    import coverage

__author__ = 'Alessandro Pasotti'
__revision__ = '$Format:%H$'
__date__ = '30/04/2018'
__copyright__ = (
    'Copyright 2018, North Road')


def _run_tests(test_suite, package_name, with_coverage=False):
    """Core function to test a test suite."""
    count = test_suite.countTestCases()
    print('########')
    print('%s tests has been discovered in %s' % (count, package_name))
    print('Python GDAL : %s' % gdal.VersionInfo('VERSION_NUM'))
    print('QGIS version : {}'.format(Qgis.version()))
    print('########')
    if with_coverage:
        cov = coverage.Coverage(
            source=['/processing_r'],
            omit=['*/test/*'],
        )
        cov.start()

    result = unittest.TextTestRunner(
        verbosity=3, stream=sys.stdout).run(test_suite)

    if with_coverage:
        cov.stop()
        cov.save()

        with tempfile.NamedTemporaryFile(delete=False) as report:
            cov.report(file=report)
            # Produce HTML reports in the `htmlcov` folder and open index.html
            # cov.html_report()
            report.close()

            with open(report.name, 'r', encoding='utf8') as fin:
                print(fin.read())

    return result.wasSuccessful()


def test_package(package='felt'):
    """Test package.
    This function is called by travis without arguments.

    Returns True if all tests passed.

    :param package: The package to test.
    :type package: str
    """
    # ensure a QgsApplication exists BEFORE any plugin modules are
    # imported by test discovery: on Qt6 builds, widgets created at
    # import time crash if no application instance exists
    from felt.test.utilities import get_qgis_app
    get_qgis_app()
    test_loader = unittest.defaultTestLoader
    # specify the top level directory explicitly: newer Python versions
    # no longer reliably resolve it from a package start directory, which
    # breaks the relative imports used by the test modules
    package_dir = os.path.dirname(os.path.abspath(__file__))
    try:
        test_suite = test_loader.discover(
            os.path.join(package_dir, 'test'),
            top_level_dir=os.path.dirname(package_dir))
    except ImportError:
        test_suite = unittest.TestSuite()
    return _run_tests(test_suite, package)


def test_environment():
    """Test package with an environment variable."""
    package = os.environ.get('TESTING_PACKAGE', 'felt')
    test_loader = unittest.defaultTestLoader
    test_suite = test_loader.discover(package)
    return _run_tests(test_suite, package)


def run_tests_and_exit():
    """
    Runs the test suite and exits the process with code 0 on success or
    1 on test failures.

    Exits without running interpreter teardown, as exiting a
    QgsApplication from a headless test run can crash on cleanup
    (especially on Qt6 builds), which would mask the test result.
    """
    successful = test_package()
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(0 if successful else 1)  # pylint: disable=protected-access


if __name__ == '__main__':
    run_tests_and_exit()
