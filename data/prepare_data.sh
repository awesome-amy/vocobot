# Make directory for paracrawl data
mkdir paracrawl
cd paracrawl || exit

# Download paracrawl data
curl -s https://s3.amazonaws.com/web-language-models/paracrawl/release7.1/en-de.txt.gz > en-de.txt.gz

# Break data into chuncks and save a list in data_chunck
gunzip en-de.txt.gz | split -l 122246
ls >> data_chunk
rm en-de.txt.gz

#Create lemmatized corpus
while IFS='' read -r LINE || [ -n "${LINE}" ]; do
    echo "Processing chunk: ${LINE}"
    python3 prepare_data.py "${LINE}"
done < data_chunk

# Delete old data chunks
while IFS='' read -r LINE || [ -n "${LINE}" ]; do
#    echo "Deleting chunk: ${LINE}"
    rm "${LINE}"
done < data_chunk

# Save a list of lemmatized data chunks
rm data_chunk
ls | grep _lemma >> data_chunk
