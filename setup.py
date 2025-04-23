from setuptools import setup, find_packages

setup(
    name="haruquant",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "MetaTrader5",
        "pandas",
        "numpy",
        "python-dotenv",
        "pytest",
        "black",
        "flake8",
        "mypy",
    ],
    author="Your Name",
    author_email="your.email@example.com",
    description="A Python-based algorithmic trading bot for MetaTrader 5",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/haruquant",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.13.2",
) 