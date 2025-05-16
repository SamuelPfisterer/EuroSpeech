from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="parliament_transcript_aligner",
    version="0.1.0",
    author="Simon Pfisterer",
    author_email="spfisterer@ethz.ch",
    description="Align parliamentary audio recordings with their corresponding transcripts",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Multimedia :: Sound/Audio :: Speech"
    ],
    python_requires=">=3.8",
    install_requires=[
        "pyannote.audio>=2.1.1",
        "pyannote.core>=4.5",
        "transformers>=4.26.0",
        "torch>=1.13.1",
        "python-Levenshtein>=0.20.9",
        "pydub>=0.25.1",
        "tqdm>=4.65.0",
        "numpy>=1.24.2",
        "python-dotenv>=1.0.0",
        "pysrt>=1.1.2"
    ],
) 