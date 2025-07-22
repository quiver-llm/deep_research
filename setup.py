# Copyright (c) 2025 Leonardo Marques Rocha
# All rights reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, modification, public performance, or public display of the
# materials, via any medium is strictly prohibited.


from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="deep-research",
    version="0.1.0",
    author="Leonardo Marques Rocha",
    author_email="leonardo.marques.rocha@gmail.com",
    description="A deep research tool for web content analysis",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/deep-research",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: Other/Proprietary License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "pydantic>=2.0.0",
        "python-dateutil>=2.8.2",
        "pyyaml>=6.0",
        "requests>=2.28.0",
        "aiohttp>=3.8.0",
        "python-dotenv>=0.21.0",
    ],
    extras_require={
        'dev': [
            'pytest>=6.0',
            'pytest-asyncio>=0.23.0',
            'black>=22.0',
            'flake8>=5.0.0',
            'mypy>=0.991',
        ],
    },
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'deep-research=deep_research.main_loop:main',
        ],
    },
)
