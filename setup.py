from setuptools import setup, find_packages

setup(
    name='easunpy',
    version='0.1.21',
    description='A tool for monitoring Easun ISolar inverters',
    author_email='vgsolar2@proton.me',
    url='https://github.com/vgsolar2/easunpy',
    packages=find_packages(),
    install_requires=[
        'rich',  # Add other dependencies here
    ],
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
)