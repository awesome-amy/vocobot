#!/bin/bash
#Download data

curl -s https://nlp.stanford.edu/projects/nmt/data/wmt14.en-de/newstest2013.en > newstest2013.en
curl -s https://nlp.stanford.edu/projects/nmt/data/wmt14.en-de/newstest2013.de > newstest2013.de
#Deal with special symbols
sed -i '' 's/ ##AT##-##AT## /-/g' newstest2013.de
sed -i '' 's/ ##AT##-##AT## /-/g' newstest2013.en
sed -i '' 's/&quot;/QUOTATION-MARK/g' newstest2013.de
sed -i '' 's/&quot;/QUOTATION-MARK/g' newstest2013.en
sed -i '' 's/&apos;/APOSTROPHE/g' newstest2013.de
sed -i '' 's/&apos;/APOSTROPHE/g' newstest2013.en
#Create lemmatized corpus
python3 prepare_lemmatized_corpus.py
#Create combined corpus
paste -d "|" newstest2013.de newstest2013.en > newstest2013.de-en
paste -d "|" newstest2013.de-en newstest2013_lemma.de > newstest2013_with_lemma.de-en

