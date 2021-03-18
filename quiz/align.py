import string
import logging


def get_alignment(sentence, aligner):
    if len(sentence) != 4:
        return None

    # The source and target sentences tokenized to words, with punctuation removed
    punctuation = string.punctuation + '„' + '”' + '®'
    word = sentence[0]
    trg_sentence = list(filter(None, sentence[1].translate(str.maketrans('', '', punctuation)).split(" ")))
    src_sentence = list(filter(None, sentence[2].translate(str.maketrans('', '', punctuation)).split(" ")))
    src_lemma = list(filter(None, sentence[3].translate(str.maketrans('', '', punctuation)).split(" ")))

    # The output is a dictionary with different matching methods.
    # Each method has a list of pairs indicating the indexes of aligned words (The alignments are zero-indexed).
    alignments = aligner.get_word_aligns(src_sentence, trg_sentence)

    if word in src_lemma:
        src_index = src_lemma.index(word)
        answer = src_sentence[src_index]
    elif word in src_sentence:
        src_index = src_sentence.index(word)
        answer = word
    else:
        return None
    # Simalign methods: mwmf, inter, itermax
    trg_word_index = [b for (a, b) in alignments['mwmf'] if a == src_index]

    # answer = src_sentence[src_index] if word not in sentence[2] else word
    question_de = sentence[2].replace(answer, "__________", 1)
    question_en = sentence[1]
    for j in trg_word_index:
        question_en = question_en.replace(trg_sentence[j], '**' + trg_sentence[j].upper() + '**', 1)

    question = {
        "question_de": question_de,
        "question_en": question_en,
        "answer": answer
    }
    return question

