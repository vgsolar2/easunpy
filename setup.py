from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="easunpy",
    version="0.1.0",
    author="Your Name",
    author_email="galindus@gmail.com",
    description="A Python tool for communicating with Easun/PowMr inverters",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/galindus/easunpy",
    packages=find_packages(),
    package_data={
        'easunpy': ['commands.json'],
    },
    install_requires=[
        'rich>=10.0.0',
        'pandas>=1.0.0',
    ],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
    python_requires=">=3.6",
    entry_points={
        'console_scripts': [
            'easunpy=easunpy.__main__:main',
        ],
    },
)