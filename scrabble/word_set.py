print("--BUILDING DICTIONARY--")
file = open("scrabble/resources/dict.txt", "r")
words = set()

for line in file.readlines():
    words.add(line.rstrip())

print("---DICTIONARY  BUILT---")
