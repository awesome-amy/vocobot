import os
import random
from simalign import SentenceAligner

# making an instance of SimAlign.
# specify the embedding model and all alignment settings in the constructor.
myaligner = SentenceAligner(model="bert", token_type="bpe", matching_methods="mai")


def get_quiz(text):
    try:
        vocabulary = get_vocabulary(text)
        quiz = []
        for v in vocabulary['vocabulary']:
            questions = get_questions(v) # list
            quiz = quiz + questions
        random.shuffle(quiz)
        return{
            "word_count": vocabulary['count'],
            "question_count": len(quiz),
            "quiz": quiz
        }
    except:
        return {"error": 'Something wrong when generating quiz. :( Send "Start" to try again.'}


def get_vocabulary(text):
    # csv to list of words
    text = text.split(":")[1]
    vocabulary = text.replace(" ", "").split(",")
    return {
        "vocabulary": vocabulary,
        "count": len(vocabulary)
    }


# If using wmt13 data
def get_sentences(word, n_random=2, corpus='data/wmt13/newstest2013_with_lemma.de-en'):
    process = os.popen('grep -w "' + word + '" ' + corpus)
    preprocessed = process.read()
    process.close()

    output = [i.split("|") for i in [lines for lines in preprocessed.split("\n")]]
    sentences = random.sample(output[:-1], min(len(output)-1, n_random))
    return sentences


def get_questions(word, n_random=2, corpus='data/wmt13/newstest2013_with_lemma.de-en'):
    sentences = get_sentences(word, n_random=n_random, corpus=corpus)
    questions = []
    try:
        for i in range(len(sentences)):
            # The source and target sentences tokenized to words.
            src_sentence = sentences[i][0].split(" ")
            trg_sentence = sentences[i][1].split(" ")
            src_lemma = sentences[i][2].split(" ")

            # The output is a dictionary with different matching methods.
            # Each method has a list of pairs indicating the indexes of aligned words (The alignments are zero-indexed).
            alignments = myaligner.get_word_aligns(src_sentence, trg_sentence)

            # Simalign methods: mwmf, inter, itermax
            src_lemma_index = src_lemma.index(word)
            src_word_index = src_lemma_index
            trg_word_index = [b for (a, b) in alignments['mwmf'] if a==src_word_index]

            answer = src_sentence[src_word_index]
            src_sentence[src_word_index] = "__________"
            for j in trg_word_index:
                trg_sentence[j] = '**' + trg_sentence[j].upper() + '**'

            question = {
                "question_de": " ".join(src_sentence).replace('QUOTATION-MARK', '"').replace('APOSTROPHE', "'"),
                "question_en": " ".join(trg_sentence).replace('QUOTATION-MARK', '"').replace('APOSTROPHE', "'"),
                "answer": answer
            }
            questions.append(question)
    except:
        return []

    return questions
