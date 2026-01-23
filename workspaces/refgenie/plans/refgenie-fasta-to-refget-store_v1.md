So, recent advances:
- refget seqcol is hosting fasta files
- refget package provides access to RefgetStore, which can be populated via a local client to a remote API that provides fasta files.
- this provides a way to store raw sequences (in collections) locally in a fast approach
- the gtars.refget package provides fasta index information (fai).

Previously, refgenie had a 'fasta' asset that would accomplish all of this (put fasta files on disk).

Now:
- can refgenie be modified to use the RefgetStore as its source of genomes?

Pros:
- offload the raw sequence storage (genome storage) to refget. provides new useful capabailities like fast sequence extraction.
- no duplication of the data -- just one copy in refgetstore

Cons: 
- well there was something nice about using refgenie's asset, because it's literally just a fasta file on disk. some tools may actually need a fasta file (and not a RefgetStore).

or mabye we just allow refgenie fasta assets to be built from local or remote RefgetStores?

Here's an idea I like: refgenie can build its fasta asset from a RefgetStore.
- when you initate a genome, you actually just manage a refgetstore. 
- then, a fasta asset is built from that store (if you want it).

