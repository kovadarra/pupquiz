import setuptools

with open("README.md", "r") as f:
    long_description = f.read()

setuptools.setup(
    name="pupquiz",
    version="0.0.6",
    author="kovadarra",
    author_email="kovadarra@users.noreply.github.com",
    description="Facilitates vocabulary acquisition",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/kovadarra/pupquiz",
    packages=setuptools.find_packages(),
    install_requires=[
        'pillow', 'ujson', 'pysimplegui'
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
    package_data={'': ['default-assets.zip', 'icon.ico']}
)
