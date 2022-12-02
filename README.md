# j2konverter
A Python script to split volume-based CBZ archives into chapter-based CBZ archives, for Tachiyomi J2K.

## Usage

`$ python ./j2konverter.py <source> <pattern> <dest>`

`source` is the path to either a single archive or a directory containing multiple archives`

`pattern` is a stream of tokens that get matched to file names from inside the archives to generate metadata. The aim is to fill the following data structure:
```
scanner: str = ""
volume: int = 0
chapter: int = 0
page: int = 0
name: str = ""
```

So, if the file names inside the archive are, for example
`SomeTitle V01 - C21 / 16 [Chapter Name] [Company]`
then the pattern to fill the metadata will look like

`x|volume|x|chapter|x|page|[name]|[scanner]`

`x` is just used to discard words we don't need. The square brackets are automatically skipped and are used to describe multi-word tokens that we need. 

If there is a lot of garbage between two tokens that we need, we can discard it as

`loopToken` where `Token` should be replaced by the first token after the garbage that we want.

Finally, `dest` is the path to the directory where we want the outputs to be generated.
