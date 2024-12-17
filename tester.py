# import sys
# import tempfile
# import subprocess
# import json
# from pylint.lint import Run
# import os
# from pylint.reporters.text import TextReporter
# #
# #
# from pylint.lint import Run
# from pylint.reporters import BaseReporter
# from io import StringIO
#

import subprocess
import pickle
import yaml
import tempfile
import os

import random
from typing import Dict, Literal, Optional, Union
from dataclasses import dataclass


@dataclass
class MinMax:
    min: int
    max: int


class TextGenerator:
    def __init__(self):
        self.vowels = 'aeiou'
        self.consonants = 'bcdfghjklmnpqrstvwxyz'
        self.punctuation = '.!?'

    def generate_random_text(
            self,
            text_type: Literal['words', 'sentences', 'paragraphs', 'mixed'] = 'mixed',
            length: int = 100,
            min_word_length: int = 3,
            max_word_length: int = 12,
            words_per_sentence: Optional[Dict[str, int]] = None,
            sentences_per_paragraph: Optional[Dict[str, int]] = None
    ) -> str:
        """
        Generate random text based on specified parameters.

        Args:
            text_type: Type of text to generate ('words', 'sentences', 'paragraphs', 'mixed')
            length: Target length in characters
            min_word_length: Minimum length of generated words
            max_word_length: Maximum length of generated words
            words_per_sentence: Dict with 'min' and 'max' keys for sentence length
            sentences_per_paragraph: Dict with 'min' and 'max' keys for paragraph length

        Returns:
            str: Generated text
        """
        # Set default values for optional parameters
        if words_per_sentence is None:
            words_per_sentence = {'min': 5, 'max': 15}
        if sentences_per_paragraph is None:
            sentences_per_paragraph = {'min': 3, 'max': 7}

        result = ''
        current_length = 0

        while current_length < length:
            if text_type == 'mixed':
                current_type = random.choice(['words', 'sentences', 'paragraphs'])
            else:
                current_type = text_type

            new_text = self._generate_by_type(
                current_type,
                min_word_length,
                max_word_length,
                words_per_sentence,
                sentences_per_paragraph
            )
            result += new_text
            current_length = len(result)

        # Trim to exact length and ensure it ends properly
        result = result[:length].rstrip()
        if result and result[-1] in self.punctuation:
            result = result[:-1] + '.'

        return result

    def _generate_word(self, min_length: int, max_length: int) -> str:
        """Generate a random word with alternating consonants and vowels."""
        word_length = random.randint(min_length, max_length)
        word = ''
        use_consonant = random.random() > 0.5

        while len(word) < word_length:
            chars = self.consonants if use_consonant else self.vowels
            word += random.choice(chars)
            use_consonant = not use_consonant

        return word

    def _generate_sentence(
            self,
            min_word_length: int,
            max_word_length: int,
            words_per_sentence: Dict[str, int]
    ) -> str:
        """Generate a random sentence."""
        num_words = random.randint(words_per_sentence['min'], words_per_sentence['max'])
        words = [self._generate_word(min_word_length, max_word_length)
                 for _ in range(num_words)]

        # Capitalize first word
        words[0] = words[0].capitalize()

        return ' '.join(words) + random.choice(self.punctuation) + ' '

    def _generate_paragraph(
            self,
            min_word_length: int,
            max_word_length: int,
            words_per_sentence: Dict[str, int],
            sentences_per_paragraph: Dict[str, int]
    ) -> str:
        """Generate a random paragraph."""
        num_sentences = random.randint(
            sentences_per_paragraph['min'],
            sentences_per_paragraph['max']
        )

        sentences = [
            self._generate_sentence(min_word_length, max_word_length, words_per_sentence)
            for _ in range(num_sentences)
        ]

        return ''.join(sentences) + '\n\n'

    def _generate_by_type(
            self,
            text_type: str,
            min_word_length: int,
            max_word_length: int,
            words_per_sentence: Dict[str, int],
            sentences_per_paragraph: Dict[str, int]
    ) -> str:
        """Generate text based on specified type."""
        if text_type == 'words':
            return self._generate_word(min_word_length, max_word_length) + ' '
        elif text_type == 'sentences':
            return self._generate_sentence(
                min_word_length,
                max_word_length,
                words_per_sentence
            )
        else:  # paragraphs
            return self._generate_paragraph(
                min_word_length,
                max_word_length,
                words_per_sentence,
                sentences_per_paragraph
            )


# Example usage:
if __name__ == "__main__":
    generator = TextGenerator()

    # Generate mixed text
    print("Mixed text (200 characters):")
    print(generator.generate_random_text(
        text_type='mixed',
        length=200,
        min_word_length=3,
        max_word_length=10,
        words_per_sentence={'min': 4, 'max': 12},
        sentences_per_paragraph={'min': 2, 'max': 5}
    ))

    # Generate just words
    print("\nRandom words (100 characters):")
    print(generator.generate_random_text(
        text_type='words',
        length=100
    ))

    # Generate paragraphs
    print("\nParagraphs (300 characters):")
    print(generator.generate_random_text(
        text_type='paragraphs',
        length=50,
        words_per_sentence={'min': 3, 'max': 8},
        sentences_per_paragraph={'min': 2, 'max': 4}
    ))
# Usage (DO NOT USE IN PRODUCTION):
# process_user_data("malicious_input", "untrusted.pkl")
# class CaptureReporter(BaseReporter):
#     def __init__(self):
#         super().__init__()
#         self.output = StringIO()
#
#     def handle_message(self, msg):
#         self.output.write(str(msg) + '\n')
#
#     def _display(self, layout):
#         pass
#
#
# def badcode(x):
#     global z
#
#
#     if x > 10:
#         if x > 20:
#             if x > 30:
#                 if x > 40:
#                     print("Nested conditions!")
#
#
# code = """
#
#
# global z
#
#
# if x > 10:
#     if x > 20:
#         if x > 30:
#             if x > 40:
#                 print("Nested conditions!")
#
# """
#
#
# def run_pylint(code):
#     with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8', dir=os.getcwd()) as temp_file:
#         temp_file.write(code)
#
#         temp_file.close()  # Explicitly close the file
#
#         temp_file_path = temp_file.name
#
#         reporter = CaptureReporter()
#         Run([temp_file_path], reporter=reporter,exit=False)
#         results = reporter.output.getvalue()
#
#         print(results)
#         #
#         # try:
#         #    Run([temp_file_path], exit=False, reporter=TextReporter(temp_file_path))
#         #    print(temp_file_path)
#         # finally:
#         #     # Clean up the temporary file
#         #     os.unlink(temp_file_path)
#
# run_pylint(code)
#
