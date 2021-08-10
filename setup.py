import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pade",
    version="0.0.1",
    author="Fredrik Feyling",
    author_email="fredrik.feyling@hotmail.com",
    description="Python based Analog Design Environment",
    long_description=long_description,
    long_description_content_type="text/markdown",
    package_dir={'': '.'},
    packages=setuptools.find_packages(),
    python_requires='>=3.8',
    install_requires = [
        'inform',
        'matplotlib',
        'numpy',
        'psf-utils',
        'python-daemon',
        'scipy',
        'shlib',
        'pint',
        'click',
        'pandas',
        'pyyaml',
    ],
    entry_points={
        'console_scripts': [
            'pade = pade.pade:cli',
        ],
    },
)
