# from anima.latex.tex_parser import TeXParser


# class TestTeXParser:
#     """Test suite for TeX Parser functionality."""

#     def setup_method(self):
#         """Set up test fixtures before each test method."""
#         self.parser = TeXParser()

#     def test_parse_simple_characters(self):
#         """Test parsing of simple characters."""
#         # Rendered characters
#         for char in ['.', ',', ';', ':', '`', '"', '(', '[', '{', '1', 'a', '?', '!']:
#             objects = self.parser.parse(char)
#             assert len(objects) == 1
#             assert objects[0].text == char
#             assert objects[0].rendered == True

#         # Non-rendered characters (whitespace)
#         for char in [' ', '\t', '\n']:
#             objects = self.parser.parse(char)
#             assert len(objects) == 1
#             assert objects[0].text == char
#             # In our parser, regular chars render
#             assert objects[0].rendered == True

#     def test_parse_tex_strings(self):
#         """Test parsing complete TeX strings."""
#         test_strings = [
#             r"The final velocity at time $t$ is computed as $v = u + at$.",
#             r"Einstein showed that $e = mc^2$.",
#             r"Euler's identity can be expressed as $e^{i\pi} = 0$.",
#             r"Useful binomial identity: $$(a - b)^2 = (a + b)(a - b)$$.",
#             r"An nth-order polynomial: $$ P_n(x) = \sum_{i = 0}^n c_ix^i. $$"
#         ]

#         for tex_str in test_strings:
#             objects = self.parser.parse(tex_str)
#             # Reconstruct text from objects
#             reconstructed = ''.join(obj.text for obj in objects)
#             assert len(reconstructed) <= len(
#                 tex_str)  # Should capture most content
#             assert len(objects) > 0

#     def test_parse_math_mode(self):
#         """Test parsing in math mode."""
#         # Single dollar math
#         objects = self.parser.parse(r"$x^2$")
#         assert len(objects) > 0

#         # Double dollar math
#         objects = self.parser.parse(r"$$e = mc^2$$")
#         assert len(objects) > 0

#     def test_parse_commands(self):
#         """Test parsing TeX commands."""
#         # Rendered commands
#         test_commands = [r"\alpha", r"\beta", r"\gamma", r"\pi", r"\tau"]

#         for cmd in test_commands:
#             objects = self.parser.parse(cmd, math_mode=True)
#             assert len(objects) == 1
#             assert objects[0].text == cmd
#             assert objects[0].rendered == True

#         # Spacing commands (non-rendered)
#         spacing_commands = [r"\quad", r"\qquad", r"\!"]

#         for cmd in spacing_commands:
#             objects = self.parser.parse(cmd)
#             assert len(objects) == 1
#             assert objects[0].text == cmd
#             assert objects[0].rendered == False

#     def test_parse_commands_with_arguments(self):
#         """Test parsing commands with braced arguments."""
#         test_cases = [
#             r"\frac{1}{2}",
#             r"\sqrt{x}",
#             r"\text{hello}",
#         ]

#         for cmd in test_cases:
#             objects = self.parser.parse(cmd, math_mode=True)
#             assert len(objects) == 1
#             assert cmd in objects[0].text
#             assert objects[0].rendered == True
#             # Should have sub-objects for arguments
#             if '{' in cmd:
#                 assert len(objects[0].sub_objects) > 0

#     def test_parse_scripts(self):
#         """Test parsing superscripts and subscripts."""
#         test_cases = [
#             ("x^2", True),
#             ("y_i", True),
#             ("x^{2}", True),
#             ("y_{i}", True),
#             ("x^2_i", True),  # Both super and subscript
#             ("x_{i}^{2}", True),
#         ]

#         for script_text, should_have_scripts in test_cases:
#             objects = self.parser.parse(script_text, math_mode=True)
#             assert len(objects) >= 1

#             if should_have_scripts:
#                 # Find object with scripts
#                 script_obj = next(
#                     (obj for obj in objects if obj.sub_objects), None)
#                 assert script_obj is not None, f"No script object found for {script_text}"
#                 assert len(script_obj.sub_objects) > 0

#     def test_parse_complex_expressions(self):
#         """Test parsing complex mathematical expressions."""
#         complex_exprs = [
#             r"x^2 + y^2 = z^2",
#             r"\sum_{i=0}^{n} x_i",
#             r"\int_0^1 f(x) dx",
#             r"\frac{x^2 - 1}{x + 1}",
#         ]

#         for expr in complex_exprs:
#             objects = self.parser.parse(expr, math_mode=True)
#             assert len(objects) > 0
#             # Should capture the main structure
#             reconstructed = ''.join(
#                 obj.text for obj in objects if obj.rendered)
#             assert len(reconstructed) > 0

#     def test_nested_braces(self):
#         """Test parsing nested braced expressions."""
#         nested_expr = r"\frac{\sqrt{x + 1}}{y^2}"
#         objects = self.parser.parse(nested_expr, math_mode=True)

#         assert len(objects) == 1
#         assert objects[0].rendered == True
#         assert len(objects[0].sub_objects) > 0

#     def test_mixed_math_and_text(self):
#         """Test parsing mixed math and text content."""
#         mixed_text = r"The formula $E = mc^2$ is famous."
#         objects = self.parser.parse(mixed_text)

#         assert len(objects) > 0
#         # Should have both text and math components
#         has_text = any('formula' in obj.text for obj in objects)
#         has_math = any('$' in obj.text for obj in objects)
#         assert has_text or has_math  # At least one should be found

#     def test_spacing_commands(self):
#         """Test that spacing commands are marked as non-rendered."""
#         spacing_commands = ['!', ',', ':', '>', ';', ' ', 'quad', 'qquad']

#         for cmd_name in spacing_commands:
#             if len(cmd_name) == 1:
#                 cmd = f"\\{cmd_name}"
#             else:
#                 cmd = f"\\{cmd_name}"

#             objects = self.parser.parse(cmd)
#             assert len(objects) == 1
#             assert objects[0].rendered == False

#     def test_character_commands(self):
#         """Test single character TeX commands."""
#         char_commands = [r"\%", r"\&", r"\#", r"\$"]

#         for cmd in char_commands:
#             objects = self.parser.parse(cmd)
#             assert len(objects) == 1
#             assert objects[0].text == cmd
#             assert objects[0].rendered == True

#     def test_empty_input(self):
#         """Test parsing empty or None input."""
#         assert self.parser.parse("") == []
#         assert self.parser.parse(None) == []

#     def test_malformed_input(self):
#         """Test parsing malformed TeX input."""
#         # Unmatched braces - should handle gracefully
#         objects = self.parser.parse(r"\frac{1}{")
#         assert len(objects) >= 1  # Should parse what it can

#         # Unmatched dollar signs
#         objects = self.parser.parse(r"$x^2")
#         assert len(objects) >= 1

#     def test_convenience_functions(self):
#         """Test the convenience functions."""
#         tex_str = r"Simple $x^2$ test"

#         # Test parse_tex function
#         objects = parse_tex(tex_str)
#         assert len(objects) > 0

#         # Test tex_to_text function
#         rendered_text = tex_to_text(objects)
#         assert isinstance(rendered_text, str)
#         assert len(rendered_text) > 0
