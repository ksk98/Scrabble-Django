print("--BUILDING DICTIONARY--")
file = open("scrabble/resources/dict.txt", "r", encoding="utf-8")
words = set()

for line in file.readlines():
    words.add(line.rstrip())

print("---DICTIONARY  BUILT---")
