import subprocess
from abc import ABC, abstractmethod
from pathlib import Path

from anima.latex.tex_document import TeXDocument


class Compiler(ABC):
    """A class that encapsulates the functionality to compile LaTeX documents."""

    def __init__(self, compiler_name: str):
        self.compiler = compiler_name

    @abstractmethod
    def compile(self, tex_file: str | Path | TeXDocument) -> str:
        pass


class TeXCompiler(Compiler):
    """A class that encapsulates the functionality to compile LaTeX documents to dvi or PDF ."""

    def __init__(self, compiler_name: str = "lualatex", output_format: str = "dvi"):
        super().__init__(compiler_name)
        self.output_format = output_format.lower()
        assert self.output_format in [
            "dvi",
            "pdf",
        ], "Output format must be either 'dvi' or 'pdf'."

    def compile(self, tex_file: str | Path | TeXDocument) -> str:
        """Compile a LaTeX file using the specified compiler.

        Args:
            tex_file (str): Path to the LaTeX file to compile.
            output_format (str): Desired output format (e.g., 'dvi', 'pdf').

        Returns:
            str: Path to the compiled output file.
        """

        cmd = [
            self.compiler,
            "-interaction=nonstopmode",
            f"-output-format={self.output_format}",
            tex_file,
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            output_file = Path(tex_file).with_suffix(f".{output_format}")
            return str(output_file)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Compilation failed: {e.stderr}") from e
