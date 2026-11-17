import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from collections.abc import Iterator, Sequence
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from math import isfinite
from pathlib import Path

import svgpathtools as svgtools
from svgpathtools.parser import parse_transform
from svgpathtools.path import transform as transform_svg_path

from anima.diagnostics import format_output, logger
from anima.latex.tex_cache import (
    CachedTexOutputs,
    clear_tex_cache as clear_tex_cache,
    read_tex_cache,
    tex_cache_enabled,
    tex_cache_key,
    tex_cache_root,
    write_tex_cache,
)
from anima.latex.tex_document import TeXDocument

TEX_DEBUG_MODE = True  # Print LaTeX and DVI logs to console
SVG_NAMESPACE = {"svg": "http://www.w3.org/2000/svg"}  # Namespace for SVG elements in XML
_PART_MARKER_PREFIX = "anima-part-"

GlyphPathsType = dict[str, svgtools.Path]  # Maps glyph IDs to their SVG paths
GlyphPositionsType = list[tuple[str, tuple[float, float], str | None, str | None]]
# (glyph ID, (x, y), character, optional display label)


class TeXPartMappingError(ValueError):
    """Raised when rendered SVG content cannot be reliably assigned to TeX parts."""


class TeXDocumentProcessor:
    """Process LaTeX documents to extract glyph data from SVG output.

    The processor compiles LaTeX to DVI, converts the result to SVG, and extracts glyph metadata.
    """

    def __init__(self, texfile: TeXDocument, *, part_names: Sequence[str] | None = None):
        """Initialize the processor with LaTeX content.

        Args:
            texfile: The TeX document to compile and process.
            part_names: Names corresponding to the internal SVG markers in the document.
        """
        assert isinstance(texfile, TeXDocument), "Content must be a TeXFile instance."
        self._content = str(texfile)
        self._temp_dir: tempfile.TemporaryDirectory = None
        self._tex_path: Path = None  # Path to the temporary directory for LaTeX files
        self._tex_name = "doc"  # Base name for .tex, .dvi, .svg, etc.
        self._command_logs: list[tuple[str, str]] = []
        self._part_names = tuple(part_names) if part_names is not None else None
        self.part_indices: dict[str, tuple[int, ...]] | None = None

    def __enter__(self) -> tuple[GlyphPathsType, GlyphPositionsType]:
        """Compile the document and extract its glyph data.

        SVG generation uses the persistent cache when enabled and a valid entry is available.

        Returns:
            A pair containing a mapping of SVG path IDs to paths and an ordered list of
            ``(path_id, (x, y), character, display_label)`` glyph instances.
        """
        # Create a temporary directory to store the LaTeX, SVG, and other generated files
        self._temp_dir = tempfile.TemporaryDirectory()
        self._tex_path = Path(self._temp_dir.name)

        try:
            use_cache = tex_cache_enabled()
            cache_root = None
            cache_key = None
            cached_svgs = None
            if use_cache:
                cache_root = tex_cache_root()
                cache_key = tex_cache_key(self._content)
                cached_svgs = read_tex_cache(cache_root, cache_key)
            if cached_svgs is not None:
                logger.info("Using cached TeX SVG outputs.")
                self._write_svg_pair(cached_svgs)
                self._replay_command_logs(cached_svgs.logs)
            else:
                # Keep outline geometry and font/text metadata in separate SVG outputs.
                self._convert_tex_to_dvi()
                self._convert_dvi_to_svg()

            result = self._extract_glyph_data()
            if cache_root is not None and cache_key is not None and cached_svgs is None:
                try:
                    self._store_svg_pair(cache_root, cache_key)
                except OSError as error:
                    logger.warning("Could not write TeX cache entry; continuing without caching: {}", error)
            return result
        except BaseException:
            self._temp_dir.cleanup()
            raise

    def __exit__(self, exc_type, exc_value, traceback):
        """Clean up temporary files after processing.

        Args:
            exc_type: The exception type raised in the context, if any.
            exc_value: The exception raised in the context, if any.
            traceback: The traceback for the context exception, if any.
        """
        self._temp_dir.cleanup()

    def _convert_tex_to_dvi(self):
        """Compile the LaTeX file to DVI format and prepare for glyph extraction.

        Raises:
            RuntimeError: If the LaTeX compilation fails.
        """
        tex_path = self._tex_path
        tex_file = tex_path / f"{self._tex_name}.tex"

        # Write LaTeX content
        logger.trace(format_output("LaTeX document content", self._content))
        tex_file.write_text(self._content, encoding="utf-8")

        # Run lualatex to generate DVI
        logger.info("Compiling TeX to DVI...")
        run_proc = partial(
            subprocess.run,
            cwd=tex_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            #    capture_output=True,
            check=True,
            text=True,
        )
        cmd = "lualatex"
        try:
            res = run_proc([cmd, "-interaction=nonstopmode", "-output-format=dvi", str(tex_file)])
            self._command_logs.append((cmd, res.stdout or ""))
            print_logs(cmd, res)
        except subprocess.CalledProcessError as err:
            print_logs(cmd, err)
            if self._part_names is not None:
                names = ", ".join(repr(name) for name in self._part_names)
                if "ANIMA-SEMANTIC-PARTS-MULTIPAGE" in (err.output or ""):
                    raise TeXPartMappingError(
                        f"Cannot map TeX part(s) {names}: multiple pages are not supported."
                    ) from err
                raise TeXPartMappingError(
                    f"Cannot map TeX part(s) {names}: LaTeX compilation failed; check the fragments and boundaries."
                ) from err
            raise RuntimeError("LaTeX compilation failed.") from err

    def _convert_dvi_to_svg(self):
        """Convert the DVI to outline and font SVGs concurrently, waiting for both.

        Raises:
            RuntimeError: If the DVI to SVG conversion fails.
        """
        tex_path = self._tex_path

        logger.info("Compiling DVI to SVG...")
        run_proc = partial(
            subprocess.run,
            cwd=tex_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            #    capture_output=True,
            check=True,
            text=True,
        )
        cmd = "dvisvgm"
        dvi_file = tex_path / f"{self._tex_name}.dvi"
        # Outlining is required for Blender geometry; font output preserves character-to-font mappings.
        outputs = (
            (self._get_svg_path(), ["--no-fonts"]),
            (self._get_svg_path("_text"), []),
        )
        commands = [
            [cmd, *options, "--exact-bbox", "--precision=6", str(dvi_file), "-o", str(svg_file)]
            for svg_file, options in outputs
        ]
        failures = []
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(run_proc, command) for command in commands]
            for (svg_file, _), future in zip(outputs, futures):
                try:
                    result = future.result()
                    self._command_logs.append((cmd, result.stdout or ""))
                    print_logs(cmd, result)
                except subprocess.CalledProcessError as err:
                    print_logs(cmd, err)
                    failures.append((svg_file, err))
        if failures:
            names = ", ".join(path.name for path, _ in failures)
            raise RuntimeError(f"DVI to SVG conversion failed for: {names}.") from failures[0][1]

    def _get_svg_file(self) -> Path:
        """Get the SVG file generated from the LaTeX document.

        Returns:
            Path: The path to the SVG file.

        Raises:
            RuntimeError: If the SVG file is not found.
        """
        svg_file = self._get_svg_path()
        if not svg_file.exists():
            raise RuntimeError(
                f"SVG file '{svg_file}' not found. Ensure that the DVI to SVG conversion was successful."
            )
        # Print contents of the SVG file for debugging
        with open(svg_file, encoding="utf-8") as f:
            logger.trace(format_output("SVG file content", f.read()))
        return svg_file

    def _get_svg_path(self, suffix: str = "") -> Path:
        """Build the path for an SVG output from the document name.

        Args:
            suffix: Optional suffix to append to the base document name.

        Returns:
            Path: The path to the SVG file.
        """
        return self._tex_path / f"{self._tex_name}{suffix}.svg"

    def _write_svg_pair(self, svgs: CachedTexOutputs) -> None:
        """Write cached SVG outputs into the processor's temporary directory.

        Args:
            svgs: The cached outline and text SVG outputs.
        """
        self._get_svg_path().write_bytes(svgs.outline_svg)
        self._get_svg_path("_text").write_bytes(svgs.text_svg)

    def _replay_command_logs(self, logs: tuple[tuple[str, str], ...]) -> None:
        """Replay successful compiler and converter output on a cache hit.

        Args:
            logs: The commands and output captured during the successful cache-miss run.
        """
        if not TEX_DEBUG_MODE:
            return
        for command, output in logs:
            _print_captured_output(command, output)

    def _store_svg_pair(self, cache_root: Path, cache_key: str) -> None:
        """Store both generated SVG outputs after successful extraction.

        Args:
            cache_root: The root directory for the persistent TeX cache.
            cache_key: The cache key for the generated document and pipeline.
        """
        outline = self._get_svg_path().read_bytes()
        text = self._get_svg_path("_text").read_bytes()
        write_tex_cache(cache_root, cache_key, outline, text, tuple(self._command_logs))

    def _extract_glyph_data(self) -> tuple[GlyphPathsType, GlyphPositionsType]:
        """Extract reusable outlines and ordered glyph instances from the generated SVGs.

        Returns:
            A pair containing:
            - A mapping from SVG glyph IDs (and generated rule IDs) to outline paths.
            - Ordered instances as ``(path_id, (x, y), character, display_label)``.

            Positions use Blender's y-axis direction. Character and display label
            are None when no matching text metadata or special-shape label exists.

        Notes:
            Character metadata is paired with outline instances in SVG use-element
            order when their counts match. A mismatch is logged and leaves the
            character metadata unavailable. Standalone rectangles recognized in
            both SVGs are included as fraction-rule instances; unsupported
            anonymous paths are ignored.
        """
        logger.info("Extracting glyph data from SVG...")
        svg_file = self._get_svg_file()
        all_paths, all_attrs = svgtools.svg2paths(svg_file)

        # dvisvgm stores reusable glyph outlines as identified paths. Fraction bars
        # are emitted separately as rectangles, so assign them generated path IDs.
        glyph_paths = GlyphPathsType()
        rule_paths: dict[tuple[str, str, str, str], list[str]] = {}
        for path, attrs in zip(all_paths, all_attrs):
            gid = attrs.get("id")
            if gid is not None:
                glyph_paths[gid] = path
            elif {"x", "y", "width", "height"} <= attrs.keys():
                rule_id = f"rule-{len(glyph_paths)}"
                glyph_paths[rule_id] = path
                signature = tuple(attrs[key] for key in ("x", "y", "width", "height"))
                rule_paths.setdefault(signature, []).append(rule_id)
            else:
                logger.debug("Ignoring SVG path without an ID or recognized standalone shape attributes.")

        tree = ET.parse(svg_file)
        root = tree.getroot()

        definitions = {
            element.attrib["id"]: element
            for defs in root.findall(".//svg:defs", SVG_NAMESPACE)
            for element in defs.findall("svg:use", SVG_NAMESPACE)
            if "id" in element.attrib
        }
        rendered_elements = list(_iter_rendered_elements(root))
        uses = [element for element in rendered_elements if element.tag.rsplit("}", 1)[-1] == "use"]
        outline_parts = None
        if self._part_names is not None:
            outline_parts, outline_uses, outline_rules, outline_markers = _extract_part_elements(
                root, self._part_names, text=False
            )
            text_root = ET.parse(self._get_svg_path("_text")).getroot()
            _, text_characters, text_rules, text_markers = _extract_part_elements(
                text_root, self._part_names, text=True
            )
            if outline_markers != text_markers:
                raise TeXPartMappingError(
                    f"Cannot map TeX part(s) {', '.join(repr(name) for name in self._part_names)}: "
                    "outline and text SVG markers differ."
                )
            if outline_uses != text_characters:
                mismatch = next(
                    (i for i, (a, b) in enumerate(zip(outline_uses, text_characters)) if a != b),
                    min(len(outline_uses), len(text_characters)),
                )
                affected = {
                    name for name, _ in outline_uses[mismatch : mismatch + 1] + text_characters[mismatch : mismatch + 1]
                }
                raise TeXPartMappingError(
                    f"Cannot map TeX part(s) {', '.join(repr(name) for name in sorted(affected))}: "
                    "outline and text glyph ownership differs."
                )
            if outline_rules != text_rules:
                affected = set(name for name, _, _ in outline_rules + text_rules)
                raise TeXPartMappingError(
                    f"Cannot map TeX part(s) {', '.join(repr(name) for name in sorted(affected))}: "
                    "outline and text shapes differ."
                )
        text_glyphs = _extract_text_glyphs(self._get_svg_path("_text"))
        if len(text_glyphs) == len(uses):
            text_glyphs_by_use = text_glyphs
        else:
            # Only pair by position when both SVG conversions produced the same
            # number of glyph instances; otherwise labels could be misleading.
            logger.warning(
                "Could not match SVG text characters to glyphs: found {} characters for {} glyphs.",
                len(text_glyphs),
                len(uses),
            )
            text_glyphs_by_use = [(None, None)] * len(uses)

        # Walk the outline SVG, rather than grouping uses and rectangles, to keep
        # generated Blender object order consistent with the rendered expression.
        glyph_positions = GlyphPositionsType()
        part_indices: dict[str, list[int]] = {name: [] for name in self._part_names or ()}
        use_index = 0
        for element in rendered_elements:
            tag = element.tag.rsplit("}", 1)[-1]
            if tag == "use":
                if outline_parts is not None and element not in outline_parts:
                    raise TeXPartMappingError("Cannot map TeX parts: an SVG use is outside rendered part markers.")
                try:
                    gid = _svg_use_reference(element)
                    _resolve_glyph_path(gid, glyph_paths, definitions, set())
                except RuntimeError as error:
                    if outline_parts is not None:
                        raise TeXPartMappingError(f"Cannot map TeX part {outline_parts[element]!r}: {error}") from error
                    raise

                x = float(element.attrib.get("x", 0))
                y = float(element.attrib.get("y", 0))
                character, display_label = text_glyphs_by_use[use_index]
                if outline_parts is not None:
                    part_indices[outline_parts[element]].append(len(glyph_positions))
                glyph_positions.append((gid, (x, -y), character, display_label))
                use_index += 1
            elif tag == "rect":
                signature = tuple(element.attrib.get(key, "") for key in ("x", "y", "width", "height"))
                matching_rules = rule_paths.get(signature)
                if matching_rules:
                    rule_id = matching_rules.pop(0)
                    if outline_parts is not None:
                        if element not in outline_parts:
                            raise TeXPartMappingError("Cannot map TeX parts: an SVG rule is outside part markers.")
                        part_indices[outline_parts[element]].append(len(glyph_positions))
                    glyph_positions.append((rule_id, (0, 0), None, "rule"))
                elif outline_parts is not None and element in outline_parts:
                    raise TeXPartMappingError(f"Cannot map TeX part {outline_parts[element]!r}: unsupported SVG rule.")

        if outline_parts is not None:
            self.part_indices = {name: tuple(indices) for name, indices in part_indices.items()}
        return glyph_paths, glyph_positions


def _iter_rendered_elements(element: ET.Element) -> Iterator[ET.Element]:
    """Walk SVG content in order, excluding reusable definitions."""
    if element.tag.rsplit("}", 1)[-1] == "defs":
        return
    yield element
    for child in element:
        yield from _iter_rendered_elements(child)


def _svg_use_reference(element: ET.Element) -> str:
    href = element.attrib.get("{http://www.w3.org/1999/xlink}href") or element.attrib.get("href", "")
    if not href.startswith("#") or len(href) == 1:
        raise RuntimeError(f"Invalid SVG glyph reference {href!r}.")
    return href[1:]


def _part_preamble(part_count: int) -> str:
    """Create shipout markers after shaping, without splitting kerning or ligatures."""
    return r"""
\newattribute\AnimaSemanticPartAttribute
\directlua{
local attribute = \the\allocationnumber;
local sequence = 0;
local count = PART_COUNT;
local boundaries = {};
local next_boundary = 0;
local pages = 0;
function anima_semantic_boundary(index)
    if tex.attribute[attribute] == index and index == next_boundary then
        boundaries[index] = true;
        next_boundary = next_boundary + 1
    else
        boundaries[index] = false
    end
end
local function special(data)
    local result = node.new('whatsit', 'special');
    result.data = 'dvisvgm:raw ' .. data;
    return result
end
local function empty_marker(id)
    return special('<g id="' .. id .. '"/>')
end
local function wrap(head)
    for current in node.traverse(head) do
        local kind = node.type(current.id);
        if kind == 'hlist' or kind == 'vlist' then
            current.list = wrap(current.list)
        end
        if kind == 'glyph' or kind == 'rule' then
            local owner = node.has_attribute(current, attribute);
            if owner and owner >= 0 and owner < count then
                if kind == 'glyph' then
                    local font_data = font.getfont(current.font);
                    if font_data.hb or (font_data.properties and
                            (font_data.properties.mode == 'plug' or font_data.properties.mode == 'harf')) then
                        head = node.insert_before(head, current,
                            empty_marker('anima-part-' .. owner .. '-unsupported-renderer'))
                    end
                    if current.components then
                        for component in node.traverse(current.components) do
                            if node.type(component.id) == 'glyph' then
                                local other = node.has_attribute(component, attribute);
                                if not (other == owner) then
                                    head = node.insert_before(head, current,
                                        empty_marker('anima-part-' .. owner .. '-ambiguous-' .. (other or -1)))
                                end
                            end
                        end
                    end
                end
                local marker = 'anima-part-' .. owner .. '-item-' .. sequence;
                sequence = sequence + 1;
                head = node.insert_before(head, current, special('<g id="' .. marker .. '">'));
                head = node.insert_after(head, current, special('</g>'))
            end
        end
    end
    return head
end
function anima_semantic_shipout(box)
    pages = pages + 1;
    if pages > 1 then
        tex.error('ANIMA-SEMANTIC-PARTS-MULTIPAGE')
    end
    box.list = wrap(box.list);
    for i = 0, count - 1 do
        if boundaries[i] then
            box.list = node.insert_before(box.list, box.list, empty_marker('anima-part-' .. i .. '-sentinel'))
        end
    end
end
}
\AddToHook{shipout/before}{\directlua{anima_semantic_shipout(tex.box[\number\ShipoutBox])}}
""".strip().replace("PART_COUNT", str(part_count))


def _resolve_glyph_path(
    gid: str, glyph_paths: GlyphPathsType, definitions: dict[str, ET.Element], visiting: set[str]
) -> svgtools.Path:
    """Resolve and cache a glyph outline, including transformed SVG use aliases."""
    if gid in glyph_paths:
        return glyph_paths[gid]
    if gid in visiting:
        raise RuntimeError(f"Cyclic SVG glyph definition involving {gid!r}.")
    element = definitions.get(gid)
    if element is None:
        raise RuntimeError(f"SVG glyph definition {gid!r} is missing.")
    visiting.add(gid)
    try:
        path = _resolve_glyph_path(_svg_use_reference(element), glyph_paths, definitions, visiting)
        try:
            x = float(element.attrib.get("x", 0))
            y = float(element.attrib.get("y", 0))
            matrix = parse_transform(element.attrib.get("transform"), strict=True)
            if not all(isfinite(value) for value in (x, y, *matrix.flat)):
                raise ValueError("non-finite SVG transform")
        except ValueError as error:
            raise RuntimeError(f"Invalid SVG transform in glyph definition {gid!r}: {error}") from error
        if x or y:
            path = path.translated(complex(x, y))
        glyph_paths[gid] = transform_svg_path(path, matrix)
        return glyph_paths[gid]
    finally:
        visiting.remove(gid)


def _extract_part_elements(
    root: ET.Element, part_names: tuple[str, ...], *, text: bool
) -> tuple[
    dict[ET.Element, str],
    list[tuple[str, str]],
    list[tuple[str, str, tuple[str, ...]]],
    set[str],
]:
    """Validate marker ownership and collect glyph and rule ownership in SVG order."""
    seen: set[str] = set()
    sentinels: set[int] = set()
    owners: dict[ET.Element, str] = {}
    glyph_owners: list[tuple[str, str]] = []
    rules: list[tuple[str, str, tuple[str, ...]]] = []
    item_markers: set[str] = set()
    affected = ", ".join(repr(name) for name in part_names)
    containers = {"svg", "g", "tspan"}

    def visit(element: ET.Element, owner: str | None = None, item: str | None = None, in_text: bool = False) -> None:
        tag = element.tag.rsplit("}", 1)[-1]
        if tag in {"defs", "style", "metadata", "title", "desc"}:
            return
        marker = element.attrib.get("id", "")
        if marker.startswith(_PART_MARKER_PREFIX):
            match = re.fullmatch(r"anima-part-(\d+)-(sentinel|item-\d+|ambiguous--?\d+|unsupported-renderer)", marker)
            if tag != "g" or match is None or marker in seen or owner is not None or in_text:
                raise TeXPartMappingError(
                    f"Cannot map TeX part(s) {affected}: invalid or duplicate SVG marker {marker!r}."
                )
            index = int(match.group(1))
            if index >= len(part_names):
                raise TeXPartMappingError(f"Cannot map TeX part(s) {affected}: unknown SVG marker {marker!r}.")
            name = part_names[index]
            marker_type = match.group(2)
            if marker_type.startswith("ambiguous-"):
                other = int(marker_type.removeprefix("ambiguous-"))
                names = [name]
                if 0 <= other < len(part_names) and other != index:
                    names.append(part_names[other])
                raise TeXPartMappingError(
                    f"Cannot map TeX part(s) {', '.join(repr(part) for part in names)}: "
                    "a shaped glyph spans part boundaries."
                )
            if marker_type == "unsupported-renderer":
                raise TeXPartMappingError(
                    f"Cannot map TeX part {name!r}: the font renderer does not preserve ligature ownership."
                )
            seen.add(marker)
            if marker_type == "sentinel":
                sentinels.add(index)
            else:
                item_markers.add(marker)
                item = marker
            owner = name
        if tag not in containers:
            if owner is None:
                raise TeXPartMappingError(
                    f"Cannot map TeX part(s) {affected}: unsupported SVG {tag} outside a part marker."
                )
            if item is None:
                raise TeXPartMappingError(f"Cannot map TeX part {owner!r}: SVG {tag} outside an item marker.")
            if tag == "use" and not text:
                owners[element] = owner
                glyph_owners.append((owner, item))
            elif tag == "text" and text and not in_text:
                glyph_owners.extend(
                    (owner, item) for chunk in element.itertext() for char in chunk if not char.isspace()
                )
            elif tag == "rect":
                owners[element] = owner
                rules.append((owner, item, tuple(element.attrib.get(key, "") for key in ("x", "y", "width", "height"))))
            else:
                raise TeXPartMappingError(f"Cannot map TeX part {owner!r}: unsupported SVG {tag}.")
        elif tag == "tspan" and not in_text:
            raise TeXPartMappingError(f"Cannot map TeX part(s) {affected}: SVG tspan outside text.")
        for child in element:
            visit(child, owner, item, in_text or tag == "text")

    visit(root)
    missing = [name for index, name in enumerate(part_names) if index not in sentinels]
    if missing:
        raise TeXPartMappingError(
            f"Cannot map TeX part(s) {', '.join(repr(name) for name in missing)}: SVG marker missing."
        )
    return owners, glyph_owners, rules, item_markers


def _extract_text_glyphs(svg_file: Path) -> list[tuple[str | None, str | None]]:
    """Read rendered characters and private-use glyph names from a dvisvgm SVG.

    Args:
        svg_file: Font-preserving SVG produced by dvisvgm.

    Returns:
        Non-whitespace text characters in SVG reading order, each paired with a
        font ``glyph-name`` when that character is in a Unicode private-use area
        and the SVG provides a matching font mapping. Other characters, or
        private-use characters without a font mapping, have a None glyph name.

    Notes:
        The character-to-font mapping is selected using each text element's CSS
        class and the corresponding ``font-family`` rule in the SVG stylesheet.
        Nested text elements are read as part of their containing text element.
    """
    root = ET.parse(svg_file).getroot()
    font_names: dict[str, dict[str, str]] = {}
    for font in root.iter():
        if font.tag.rsplit("}", 1)[-1] != "font":
            continue
        font_face = next(
            (child for child in font if child.tag.rsplit("}", 1)[-1] == "font-face"),
            None,
        )
        family = (
            font_face.attrib.get("font-family", font.attrib.get("id", ""))
            if font_face is not None
            else font.attrib.get("id", "")
        )
        # Glyph names are font-specific; a Unicode value alone is not unique
        # across the multiple math fonts dvisvgm may embed.
        glyph_names = font_names.setdefault(family, {})
        for glyph in font:
            if glyph.tag.rsplit("}", 1)[-1] == "glyph":
                character = glyph.attrib.get("unicode")
                glyph_name = glyph.attrib.get("glyph-name")
                if character and glyph_name:
                    glyph_names[character] = glyph_name

    text_families: dict[str, str] = {}
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] != "style" or element.text is None:
            continue
        # dvisvgm associates text classes with font families through CSS rules.
        for css_class, family in re.findall(r"text\.([^{\s]+)\s*\{[^}]*font-family:\s*([^;}\s]+)", element.text):
            text_families[css_class] = family.strip("'\"")

    text_glyphs: list[tuple[str, str | None]] = []
    for element in _iter_rendered_elements(root):
        if element.tag.rsplit("}", 1)[-1] == "text":
            css_class = element.attrib.get("class", "")
            family = text_families.get(css_class, "")
            glyph_names = font_names.get(family, {})
            # Text may be split across nested tspans; flatten it while excluding
            # whitespace, which has no corresponding outline glyph.
            text_glyphs.extend(
                (character, glyph_names.get(character) if _is_private_use_character(character) else None)
                for character in "".join(element.itertext())
                if not character.isspace()
            )
    return text_glyphs


def _is_private_use_character(character: str) -> bool:
    """Return whether a character belongs to a Unicode private-use area.

    Args:
        character: The character to check.

    Returns:
        True if the character is in a private-use area, False otherwise.
    """
    codepoint = ord(character)
    return 0xE000 <= codepoint <= 0xF8FF or 0xF0000 <= codepoint <= 0xFFFFD or 0x100000 <= codepoint <= 0x10FFFD


def print_logs(command: str, result: subprocess.CompletedProcess | subprocess.CalledProcessError) -> None:
    """Print the stdout and stderr result of a subprocess.

    Args:
        command: The command that was run.
        result: The result of the subprocess run, which can be a CompletedProcess or CalledProcessError.
    """
    if isinstance(result, subprocess.CompletedProcess) and not TEX_DEBUG_MODE:
        return

    output = getattr(result, "stdout", "")
    _print_captured_output(command, output)


def _print_captured_output(command: str, output: str) -> None:
    """Log captured subprocess output when it is non-empty."""
    if output.rstrip():
        logger.trace(format_output(f"{command.capitalize()} output", output))
