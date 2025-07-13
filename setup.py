from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="ai-research-workflow",
    version="1.0.0",
    author="AI Research Team",
    author_email="contact@example.com",
    description="AI驱动的研究工作流本地化程序",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/example/ai-research-workflow",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Scientific/Engineering :: Information Analysis",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "ai-research=main:main",
        ],
    },
    keywords="ai, research, workflow, search, llm, automation",
    project_urls={
        "Bug Reports": "https://github.com/example/ai-research-workflow/issues",
        "Source": "https://github.com/example/ai-research-workflow",
        "Documentation": "https://github.com/example/ai-research-workflow/blob/main/README.md",
    },
)