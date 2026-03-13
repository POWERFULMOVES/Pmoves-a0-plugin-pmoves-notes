"""PMOVES.Notes Plugin for Agent Zero."""

from setuptools import setup, find_packages

setup(
    name="a0-plugin-pmoves-notes",
    version="1.0.0",
    description="Persistent note-taking integration for Agent Zero with PMOVES.AI Open Notebook",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="POWERFULMOVES",
    url="https://github.com/POWERFULMOVES/a0-plugin-pmoves-notes",
    license="MIT",
    packages=[],
    package_data={
        "": ["*.yaml", "*.md"],
        "extensions": ["**/*.py"],
        "tools": ["**/*.py"],
    },
    install_requires=[
        "aiohttp>=3.9.0",
        "nats-py>=2.7.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-aiohttp>=1.0.0",
            "pytest-cov>=4.1.0",
        ],
    },
    python_requires=">=3.10",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
