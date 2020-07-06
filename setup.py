import setuptools

with open("README.md", "r") as f:
    long_description = f.read()

setuptools.setup(
    name="pupquiz",
    version="0.0.19",
    author="kovadarra",
    author_email="kovadarra@users.noreply.github.com",
    description="Facilitates vocabulary acquisition",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/kovadarra/pupquiz",
    packages=setuptools.find_packages(),
    install_requires=[
        'pillow>=7.1.2', 'pysimplegui>=4.20.0', 'gTTS>=2.1.1', 'playsound>=1.2.2', 'matplotlib>=3.1.3'
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
    package_data={'': ['default-assets.zip',
                       'icon.ico', 'folder-off.png', 'folder-on.png']}
)
