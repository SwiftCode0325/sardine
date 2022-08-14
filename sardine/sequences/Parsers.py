import itertools
import random
import re
from rich import print

__all__ = ('PatternParser')

class PatternParser():
    """Mininotation for sequences"""

    SOUND_REGEX = re.compile(
        r"""
        (?P<sound>[\w|]+)
        (?: \?(?P<chance>\d*) )?
        (?:  !(?P<repeat>\d+) )?
        """,
        re.VERBOSE)

    NUMBER_REGEX = re.compile(
        r"""
        (?P<number>([-+]?[\d*\.\d+|]+))
        (?: \?(?P<chance>\d*) )?
        (?: !(?P<repeat>\d+) )?
        (?: :(?P<range>([-+]?[\d*\.\d+|]+) ))?
        """,
        re.VERBOSE)


    def __init__(self, pattern: str, type: str):

        if type == 'sound':
            self.pattern = self.parse_sound_string(pattern)
        elif type == 'number':
            self.pattern = self.parse_number_string(pattern)
        else:
            raise TypeError("Pattern must be of type 'sound' or 'number'")


    def parse_sound_string(self, pattern: str) -> list[str]:
        """Parse pattern string using the sound REGEX"""
        rule = self.SOUND_REGEX

        def _expand_sound(pattern: str) -> list[str]:
            # Split the incoming string
            words, tokens = pattern.split(), []
            # Tokenize and parse
            for w in words:
                # Try to match a symbol, return None if not in spec
                m = rule.fullmatch(w)
                if m is None:
                    raise ValueError(f'unknown sound definition: {w!r}')
                sound = [m['sound']]
                if '|' in m['sound']:
                    sound = [random.choice( m['sound'].split('|') )]
                else:
                    sound = [m['sound']]
                if m['chance'] is not None:
                    chance = int(m['chance'] or 50)
                    if random.randrange(100) >= chance:
                        continue
                if m['repeat'] is not None:
                    sound *= int(m['repeat'])
                tokens.extend(sound)
            return tokens

        parsed_expression = _expand_sound(pattern)
        return parsed_expression


    def parse_number_string(self, pattern: str) -> list[str]:
        """Parse number string using the number REGEX"""
        rule = self.NUMBER_REGEX

        def _expand_number(s: str) -> list[str]:
            # Split the incoming string
            words, tokens = s.split(), []
            # Tokenize and parse
            for w in words:
                # Try to match a symbol, return None if not in spec
                m = rule.fullmatch(w)
                if m is None:
                    raise ValueError(f'unknown number definition: {w!r}')
                number= [m['number']]
                if m['chance'] is not None:
                    chance = int(m['chance'] or 50)
                    if random.randrange(100) >= chance:
                        continue
                if m['repeat'] is not None:
                    number *= int(m['repeat'])
                if m['range'] is not None:
                    integer_test = str(number[0]).isdigit()
                    number = [random.uniform(float(number[0]), float(m['range']))]
                    if integer_test:
                        number = [int(number[0])]
                tokens.extend(number)
            return tokens

        parsed_expression = _expand_number(pattern)
        return parsed_expression

    def get_pattern(self) -> itertools.cycle:
        """Get pattern as iterator"""
        return itertools.cycle(self.pattern)


# if __name__ == "__main__":
#     random.seed(random.randint(1,100))
#     nb_tests = 5
# 
#     s = '909? cp?30 bd?!3 cp|hh|ll'
#     print(f"\nRegex for sounds\n")
#     for i in range(0, nb_tests):
#         pattern = PatternParser(pattern=s, type='sound')
#         print(f'run {i}:', pattern.pattern)
# 
#     print(f"\nRegex for simple number operations\n")
#     s = '0 -0 +0 5 5.0 -5.0 +5.0? 12!2'
#     for i in range(0, nb_tests):
#         pattern = PatternParser(pattern=s, type='number')
#         print(f'run {i}:', pattern.pattern)
# 
#     print(f"\nRegex for number ramp/list generation\n")
#     s = '0:20 -10:10 -20:20'
#     for i in range(0, nb_tests):
#         pattern = PatternParser(pattern=s, type='number')
#         print(f'run {i}:', pattern.pattern)
