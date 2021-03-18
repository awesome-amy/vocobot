import os
from random import shuffle


# If using paracrawl data
def get_paracrawl_sentences(text, max_try=3):
    """
    USING GNU Parallel. Install it on MacOX first!
    :param text:
    :param n_random:
    :param max_try:
    :return:
    """
    text = text.split(":")[1]
    word_count = text.count(',')+1
    word_set = set(text.replace(" ", "").split(","))

    sentences = []
    i = 0
    while len(word_set) != 0 and i < max_try:
        input = " ".join(word_set)
        process = os.popen('parallel --link --tagstring {1} LC_ALL=C grep -m 2 -F -w {1} data/paracrawl/{2} ::: ' +
                           input +
                           ' ::: $(cat data/paracrawl/data_chunk | shuf -n 2)')
        preprocessed = process.read()
        process.close()

        output = [i.split("\t") for i in [lines for lines in preprocessed.split("\n")]]
        output.pop() # remove an empty line at the end of the command line output
        sentences = sentences + output
        word_set = word_set - set([i[0] for i in output])
        i = i+1

    question_count = len(sentences)
    shuffle(sentences)

    return word_count, question_count, sentences
